"""Lectura, validación de calidad y preparación del panel semanal (misma lógica que scripts/01_audit_dataset.py)."""
from __future__ import annotations

import pandas as pd

NON_MERCHANDISE = {"DOT", "M", "C2", "POST", "BANK CHARGES", "GIFT_0001_30"}
REQUIRED = ["InvoiceNo", "StockCode", "Quantity", "InvoiceDate"]
OPTIONAL = ["Description", "UnitPrice", "CustomerID", "Country"]
ALIASES = {
    "invoice": "InvoiceNo", "invoiceno": "InvoiceNo", "invoice no": "InvoiceNo", "factura": "InvoiceNo",
    "stockcode": "StockCode", "stock code": "StockCode", "sku": "StockCode", "codigo": "StockCode", "código": "StockCode",
    "description": "Description", "descripcion": "Description", "descripción": "Description",
    "quantity": "Quantity", "cantidad": "Quantity",
    "invoicedate": "InvoiceDate", "invoice date": "InvoiceDate", "fecha": "InvoiceDate",
    "price": "UnitPrice", "unitprice": "UnitPrice", "unit price": "UnitPrice", "precio": "UnitPrice",
    "customerid": "CustomerID", "customer id": "CustomerID",
    "country": "Country", "pais": "Country", "país": "Country",
}
WEEKLY_ALIASES = {"stockcodestr": "StockCode", "stockcode": "StockCode", "sku": "StockCode",
                  "weekstart": "WeekStart", "unitssold": "UnitsSold"}


class DataError(ValueError):
    """Error de formato o de contenido del archivo cargado (se muestra al usuario)."""


def read_table(source, filename: str) -> pd.DataFrame:
    """Lee un CSV o XLSX (todas las hojas se concatenan). `source` es una ruta o un objeto con bytes."""
    name = filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(source, low_memory=False)
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        sheets = pd.read_excel(source, sheet_name=None, engine="openpyxl")
        return pd.concat(sheets.values(), ignore_index=True)
    raise DataError("Formato no admitido: use un archivo .csv o .xlsx.")


def _canon(column: str) -> str:
    return " ".join(str(column).strip().lower().replace("_", " ").split())


def map_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Renombra columnas equivalentes a los nombres estándar. Devuelve (df, {original: estándar})."""
    mapping = {}
    for col in df.columns:
        key = _canon(col)
        key_compact = key.replace(" ", "")
        target = ALIASES.get(key) or ALIASES.get(key_compact)
        if target and target not in mapping.values():
            mapping[col] = target
    return df.rename(columns=mapping), mapping


def detect_format(df: pd.DataFrame) -> str:
    """'transactions' (líneas de factura) o 'weekly' (panel semanal ya agregado)."""
    renamed, _ = map_columns(df)
    if all(c in renamed.columns for c in REQUIRED):
        return "transactions"
    weekly = {WEEKLY_ALIASES.get(_canon(c).replace(" ", ""), c) for c in df.columns}
    if {"StockCode", "WeekStart", "UnitsSold"} <= weekly:
        return "weekly"
    missing = [c for c in REQUIRED if c not in renamed.columns]
    raise DataError(
        "No se reconocen las columnas del archivo. Para transacciones se necesitan: "
        + ", ".join(REQUIRED) + f" (faltan: {', '.join(missing)}). "
        "También se acepta un panel semanal con StockCode, WeekStart y UnitsSold."
    )


def _prepare_transactions(df: pd.DataFrame) -> pd.DataFrame:
    data, _ = map_columns(df)
    data = data.copy()
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["InvoiceNo_str"] = data["InvoiceNo"].astype(str).str.strip()
    data["StockCode_str"] = data["StockCode"].astype(str).str.strip().str.upper()
    return data


def quality_report(df: pd.DataFrame) -> dict:
    """Resumen de calidad previo al modelado (nulos, duplicados, cancelaciones, cantidades negativas)."""
    data = _prepare_transactions(df)
    cols = [c for c in REQUIRED + OPTIONAL if c in data.columns]
    n = len(data)
    dup = int(data.duplicated(subset=cols).sum())
    clean = data.drop_duplicates(subset=cols)
    cancel = clean["InvoiceNo_str"].str.upper().str.startswith("C")
    bad_dates = int(data["InvoiceDate"].isna().sum())
    bad_qty = int(data["Quantity"].isna().sum())
    report = {
        "rows": n,
        "exact_duplicates": dup,
        "exact_duplicates_pct": round(100 * dup / n, 2) if n else 0.0,
        "cancellations": int(cancel.sum()),
        "negative_quantity": int((clean["Quantity"] < 0).sum()),
        "invalid_dates": bad_dates,
        "invalid_quantities": bad_qty,
        "missing_customer_id_pct": round(100 * clean["CustomerID"].isna().mean(), 2) if "CustomerID" in clean else None,
        "date_min": clean["InvoiceDate"].min(),
        "date_max": clean["InvoiceDate"].max(),
        "countries": sorted(clean["Country"].dropna().astype(str).unique().tolist()) if "Country" in clean else [],
        "has_customer_id": "CustomerID" in clean.columns,
    }
    return report


def clean_lines(df: pd.DataFrame, country: str | None = None) -> pd.DataFrame:
    """Líneas de venta válidas: sin duplicados exactos, cancelaciones ni cantidades no positivas."""
    data = _prepare_transactions(df)
    cols = [c for c in REQUIRED + OPTIONAL if c in data.columns]
    data = data.dropna(subset=["InvoiceDate", "Quantity"]).drop_duplicates(subset=cols)
    keep = ~data["InvoiceNo_str"].str.upper().str.startswith("C") & (data["Quantity"] > 0)
    data = data[keep]
    if country and "Country" in data.columns:
        data = data[data["Country"].astype(str).eq(country)]
    return data


def weekly_from_lines(lines: pd.DataFrame) -> pd.DataFrame:
    """Unidades por artículo y semana (lunes). Se excluyen la primera y la última semana calendario (parciales)."""
    if lines.empty:
        raise DataError("No quedan líneas de venta válidas después de la limpieza.")
    week = lines["InvoiceDate"].dt.to_period("W-SUN").apply(lambda p: p.start_time)
    first_full = week.min() + pd.Timedelta(days=7)
    last_full = week.max() - pd.Timedelta(days=7)
    if first_full > last_full:
        raise DataError("El archivo cubre menos de tres semanas calendario; se necesita más historial.")
    full = lines.assign(WeekStart=week)
    full = full[(full["WeekStart"] >= first_full) & (full["WeekStart"] <= last_full)]
    weekly = full.groupby(["StockCode_str", "WeekStart"], as_index=False).agg(UnitsSold=("Quantity", "sum"))
    return weekly.rename(columns={"StockCode_str": "StockCode"})


def weekly_from_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza un panel semanal ya agregado (StockCode, WeekStart, UnitsSold)."""
    data = df.rename(columns={c: WEEKLY_ALIASES.get(_canon(c).replace(" ", ""), c) for c in df.columns}).copy()
    data["StockCode"] = data["StockCode"].astype(str).str.strip().str.upper()
    data["WeekStart"] = pd.to_datetime(data["WeekStart"], errors="coerce")
    data["UnitsSold"] = pd.to_numeric(data["UnitsSold"], errors="coerce")
    data = data.dropna(subset=["WeekStart", "UnitsSold"])
    data = data[data["UnitsSold"] > 0]
    return data.groupby(["StockCode", "WeekStart"], as_index=False)["UnitsSold"].sum()


def panel_matrix(weekly: pd.DataFrame, exclude=NON_MERCHANDISE):
    """Matriz artículos x semanas (ceros en las semanas sin ventas). Devuelve (Y, weeks, skus)."""
    weeks = pd.date_range(weekly["WeekStart"].min(), weekly["WeekStart"].max(), freq="7D")
    wide = (weekly.pivot(index="StockCode", columns="WeekStart", values="UnitsSold")
            .reindex(columns=weeks).fillna(0.0).sort_index())
    wide = wide.loc[~wide.index.isin(exclude)]
    if len(weeks) < 30:
        raise DataError(f"El historial tiene {len(weeks)} semanas; se necesitan al menos 30 para pronosticar con fiabilidad.")
    return wide.to_numpy(dtype=float), weeks, wide.index.tolist()


def weekly_zero_weeks(weekly: pd.DataFrame) -> list[str]:
    weeks = pd.date_range(weekly["WeekStart"].min(), weekly["WeekStart"].max(), freq="7D")
    have = set(weekly["WeekStart"].unique())
    return [str(w.date()) for w in weeks if w not in have]
