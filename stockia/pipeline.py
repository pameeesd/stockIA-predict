"""Flujo completo sin interfaz: cargar datos → validar → panel semanal → pronóstico y backtesting → alertas."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import alerts as alerts_mod
from . import backtest, engine, ingest, storage
from .forecasting import wape

ROOT = Path(__file__).resolve().parents[1]
DEMO_PANEL = ROOT / "data" / "processed" / "uk_product_week_sales.csv"
DEMO_DIR = ROOT / "data" / "demo"


@dataclass
class Dataset:
    source: str
    kind: str                       # 'demo' | 'upload'
    weeks: pd.DatetimeIndex
    skus: list
    Y: np.ndarray
    descriptions: dict
    quality: dict
    alerts: pd.DataFrame | None     # None si el archivo no trae líneas de factura
    zero_weeks: list = field(default_factory=list)
    column_mapping: dict = field(default_factory=dict)
    country: str | None = None

    @property
    def cutoff(self) -> str:
        return str((self.weeks[-1] + pd.Timedelta(days=6)).date())

    @property
    def next_week(self) -> str:
        return str((self.weeks[-1] + pd.Timedelta(days=7)).date())


@dataclass
class Analysis:
    table: pd.DataFrame
    meta: dict
    backtest: dict | None
    backtest_error: str | None = None


def _alerts_in_window(alerts_df: pd.DataFrame | None, weeks: pd.DatetimeIndex) -> pd.DataFrame | None:
    if alerts_df is None:
        return None
    out = alerts_df.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    mask = (out["Date"] >= weeks[0]) & (out["Date"] < weeks[-1] + pd.Timedelta(days=7))
    out = out[mask].copy()
    out["Date"] = out["Date"].dt.date
    return out.reset_index(drop=True)


def load_demo() -> Dataset:
    """Panel semanal derivado de UCI Online Retail II (Reino Unido) y activos de demostración precalculados."""
    weekly = ingest.weekly_from_panel(pd.read_csv(DEMO_PANEL, dtype={"StockCode_str": str}))
    Y, weeks, skus = ingest.panel_matrix(weekly)
    desc_path = DEMO_DIR / "product_descriptions.csv"
    descriptions = {}
    if desc_path.exists():
        d = pd.read_csv(desc_path, dtype=str).dropna()
        descriptions = dict(zip(d["SKU"], d["Description"]))
    quality = json.loads((DEMO_DIR / "quality_report_uci.json").read_text(encoding="utf-8")) \
        if (DEMO_DIR / "quality_report_uci.json").exists() else {}
    alerts_df = None
    alert_path = DEMO_DIR / "volume_alerts_uci.csv"
    if alert_path.exists():
        alerts_df = _alerts_in_window(pd.read_csv(alert_path, dtype={"SKU": str}), weeks)
    return Dataset(source="UCI Online Retail II (demostración)", kind="demo", weeks=weeks, skus=skus, Y=Y,
                   descriptions=descriptions, quality=quality, alerts=alerts_df,
                   zero_weeks=ingest.weekly_zero_weeks(weekly), country="United Kingdom")


def inspect_upload(df: pd.DataFrame) -> dict:
    """Primer vistazo al archivo: formato, mapeo de columnas, calidad y países disponibles."""
    kind = ingest.detect_format(df)
    info = {"format": kind, "rows": len(df), "columns": list(df.columns)}
    if kind == "transactions":
        _, mapping = ingest.map_columns(df)
        info["mapping"] = mapping
        info["quality"] = ingest.quality_report(df)
        info["countries"] = info["quality"]["countries"]
    return info


def load_upload(df: pd.DataFrame, filename: str, country: str | None = None) -> Dataset:
    kind = ingest.detect_format(df)
    if kind == "weekly":
        weekly = ingest.weekly_from_panel(df)
        Y, weeks, skus = ingest.panel_matrix(weekly)
        quality = {"rows": len(df), "format": "panel semanal"}
        return Dataset(source=filename, kind="upload", weeks=weeks, skus=skus, Y=Y, descriptions={}, quality=quality,
                       alerts=None, zero_weeks=ingest.weekly_zero_weeks(weekly))
    quality = ingest.quality_report(df)
    _, mapping = ingest.map_columns(df)
    lines = ingest.clean_lines(df, country=country)
    weekly = ingest.weekly_from_lines(lines)
    Y, weeks, skus = ingest.panel_matrix(weekly)
    descriptions = {}
    if "Description" in lines.columns:
        d = lines.dropna(subset=["Description"]).groupby("StockCode_str")["Description"].agg(lambda s: s.mode().iat[0])
        descriptions = {k: str(v).strip() for k, v in d.items()}
    found = alerts_mod.detect_volume_alerts(lines)
    return Dataset(source=filename, kind="upload", weeks=weeks, skus=skus, Y=Y, descriptions=descriptions, quality=quality,
                   alerts=_alerts_in_window(found, weeks), zero_weeks=ingest.weekly_zero_weeks(weekly),
                   column_mapping=mapping, country=country)


def analyze(ds: Dataset, exclusions: pd.DataFrame | None = None) -> Analysis:
    """Pronóstico de la semana siguiente y backtesting sobre el historial (con las exclusiones del usuario aplicadas)."""
    Y = engine.apply_exclusions(ds.Y, ds.weeks, ds.skus, exclusions) if exclusions is not None else ds.Y
    table, meta = engine.forecast_next_week(Y, ds.skus, ds.descriptions)
    meta.update({"excluded_lines": 0 if exclusions is None else int(len(exclusions)),
                 "next_week": ds.next_week, "cutoff": ds.cutoff})
    try:
        result, error = backtest.rolling_backtest(Y, ds.weeks), None
    except ValueError as exc:
        result, error = None, str(exc)
    return Analysis(table=table, meta=meta, backtest=result, backtest_error=error)


def evaluate_runs(conn, ds: Dataset) -> pd.DataFrame:
    """Compara los pronósticos guardados con la venta real, para las ejecuciones cuya semana objetivo ya está en `ds`.

    La semana objetivo de una ejecución es la que sigue a su corte de datos. Una ejecución solo es evaluable si el
    archivo cargado ahora incluye esa semana completa.
    """
    rows = []
    index = {s: i for i, s in enumerate(ds.skus)}
    week_pos = {w: j for j, w in enumerate(ds.weeks)}
    for run in storage.list_runs(conn).itertuples():
        target = pd.Timestamp(run.data_cutoff) + pd.Timedelta(days=1)
        j = week_pos.get(target)
        if j is None:
            continue
        fc = storage.load_forecasts(conn, run.id)
        fc = fc[fc["sku"].isin(index)]
        if fc.empty:
            continue
        actual = np.array([ds.Y[index[s], j] for s in fc["sku"]])
        if actual.sum() == 0:
            continue
        tsb, ref = fc["tsb"].to_numpy(), fc["reference"].to_numpy()
        rows.append({"ejecucion": int(run.id), "semana_objetivo": target.date(), "articulos": int(len(fc)),
                     "unidades_reales": float(actual.sum()), "WAPE_tsb": wape(actual, tsb), "WAPE_referencia": wape(actual, ref),
                     "sesgo_tsb": float(100 * (tsb.sum() - actual.sum()) / actual.sum())})
    return pd.DataFrame(rows)
