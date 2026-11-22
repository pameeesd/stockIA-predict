"""Pronóstico de la semana siguiente con TSB, referencia de 4 semanas, segmento y fiabilidad."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .forecasting import (ALPHAS, adi_cv2, classify, forecast_moving_average, forecast_tsb, wape)

MIN_ACTIVE_WEEKS = 20
INNER_WINDOW = 8
RELIABILITY_BY_SEGMENT = {"smooth": "Alta", "erratic": "Media", "intermittent": "Media", "lumpy": "Baja"}


def reliability(segment: str, active_weeks: int, min_active: int = MIN_ACTIVE_WEEKS) -> str:
    """Baja si el patrón es lumpy o hay menos de `min_active` semanas con ventas; si no, según el segmento."""
    if segment == "lumpy" or active_weeks < min_active:
        return "Baja"
    return RELIABILITY_BY_SEGMENT[segment]


def select_alpha(Y: np.ndarray, grid=ALPHAS, window: int = INNER_WINDOW) -> tuple[float, dict]:
    """α = β con menor WAPE en las últimas `window` semanas (validación interna; no usa la semana a pronosticar)."""
    T = Y.shape[1]
    forecasts = {a: forecast_tsb(Y, a, a) for a in grid}
    scores = {a: wape(Y[:, T - window:T], forecasts[a][:, T - window:T]) for a in grid}
    best = min(scores, key=scores.get)
    return best, forecasts


def apply_exclusions(Y: np.ndarray, weeks: pd.DatetimeIndex, skus: list[str], exclusions: pd.DataFrame) -> np.ndarray:
    """Resta del historial las líneas que el usuario marcó como «excluir» (error de registro). No modifica Y."""
    out = Y.copy()
    if exclusions is None or exclusions.empty:
        return out
    index = {s: i for i, s in enumerate(skus)}
    week_pos = {w: j for j, w in enumerate(weeks)}
    for row in exclusions.itertuples():
        i = index.get(str(row.sku))
        monday = pd.Timestamp(row.date).to_period("W-SUN").start_time
        j = week_pos.get(monday)
        if i is not None and j is not None:
            out[i, j] = max(0.0, out[i, j] - float(row.units))
    return out


def forecast_next_week(Y: np.ndarray, skus: list[str], descriptions: dict | None = None,
                       min_active: int = MIN_ACTIVE_WEEKS, history_weeks: int = 12) -> tuple[pd.DataFrame, dict]:
    """Pronóstico de la semana siguiente para cada artículo con ventas en el historial.

    Devuelve (tabla, meta). `meta` incluye el α elegido y el número de semanas.
    """
    T = Y.shape[1]
    alpha, forecasts = select_alpha(Y)
    ma4 = forecast_moving_average(Y, 4)
    adi, cv2 = adi_cv2(Y, T)
    seg = classify(adi, cv2)
    active = (Y > 0).sum(axis=1)
    keep = active > 0
    table = pd.DataFrame({
        "sku": np.array(skus)[keep],
        "descripcion": [(descriptions or {}).get(s, "") for s in np.array(skus)[keep]],
        "segmento": seg[keep],
        "adi": np.round(adi[keep], 2),
        "cv2": np.round(cv2[keep], 2),
        "semanas_con_venta": active[keep],
        "pronostico_tsb": forecasts[alpha][keep, T],
        "referencia_media4": ma4[keep, T],
        "historial": [list(map(float, row[-history_weeks:])) for row in Y[keep]],
    })
    table["fiabilidad"] = [reliability(s, int(a), min_active) for s, a in zip(table["segmento"], table["semanas_con_venta"])]
    table = table.sort_values("pronostico_tsb", ascending=False).reset_index(drop=True)
    return table, {"alpha": alpha, "weeks": T, "items": int(len(table))}
