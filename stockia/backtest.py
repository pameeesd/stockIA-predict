"""Backtesting rodante TSB vs promedio móvil de 4 semanas (mismo protocolo que scripts/05_backtesting_model_selection.py).

Seis bloques externos de 8 semanas; en cada uno el α se elige solo con las 8 semanas internas previas.
La cohorte son los artículos con >= `min_active` semanas con ventas antes del primer bloque.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .forecasting import ALPHAS, SEGMENTS, forecast_moving_average, forecast_tsb, score, segment_at, wape


def rolling_backtest(Y: np.ndarray, weeks: pd.DatetimeIndex, n_blocks: int = 6, block: int = 8,
                     min_active: int = 20) -> dict:
    T = Y.shape[1]
    first_origin = T - n_blocks * block
    if first_origin < min_active + block:
        raise ValueError(f"Historial insuficiente para el backtesting: se necesitan al menos "
                         f"{n_blocks * block + min_active + block} semanas y hay {T}.")
    cohort = (Y[:, :first_origin] > 0).sum(axis=1) >= min_active
    if cohort.sum() < 10:
        raise ValueError("Muy pocos artículos con historial suficiente para evaluar.")
    Yc = Y[cohort]
    tsb = {a: forecast_tsb(Yc, a, a) for a in ALPHAS}
    ma4 = forecast_moving_average(Yc, 4)
    origins = [first_origin + k * block for k in range(n_blocks)]

    pred_tsb = np.zeros((len(Yc), n_blocks * block))
    pred_ma4 = np.zeros_like(pred_tsb)
    actual = np.zeros_like(pred_tsb)
    seg = np.empty(pred_tsb.shape, dtype=object)
    folds = []
    for f, o in enumerate(origins):
        cols = slice(f * block, (f + 1) * block)
        alpha = min(ALPHAS, key=lambda a: wape(Yc[:, o - block:o], tsb[a][:, o - block:o]))
        pred_tsb[:, cols] = tsb[alpha][:, o:o + block]
        pred_ma4[:, cols] = ma4[:, o:o + block]
        actual[:, cols] = Yc[:, o:o + block]
        seg[:, cols] = segment_at(Yc, o)[:, None]
        folds.append({"bloque": f + 1, "inicio": weeks[o].date(), "fin": weeks[o + block - 1].date(), "alpha": alpha,
                      "WAPE_tsb": wape(actual[:, cols], pred_tsb[:, cols]),
                      "WAPE_referencia": wape(actual[:, cols], pred_ma4[:, cols])})

    s_tsb, s_ref = score(actual, pred_tsb), score(actual, pred_ma4)
    has_sales = actual.sum(axis=1) > 0
    err_tsb = np.abs(actual - pred_tsb).sum(axis=1)
    err_ref = np.abs(actual - pred_ma4).sum(axis=1)
    segments = []
    for name in SEGMENTS:
        m = seg == name
        if m.any() and actual[m].sum() > 0:
            segments.append({"segmento": name, "unidades": float(actual[m].sum()),
                             "WAPE_tsb": wape(actual[m], pred_tsb[m]), "WAPE_referencia": wape(actual[m], pred_ma4[m])})
    return {
        "summary": {"WAPE_tsb": s_tsb["WAPE_pct"], "WAPE_referencia": s_ref["WAPE_pct"],
                    "sesgo_tsb": s_tsb["bias_pct"], "sesgo_referencia": s_ref["bias_pct"],
                    "mejora_relativa_pct": 100 * (s_ref["WAPE_pct"] - s_tsb["WAPE_pct"]) / s_ref["WAPE_pct"],
                    "productos_mejores_pct": float(100 * (err_tsb[has_sales] < err_ref[has_sales]).mean()),
                    "productos_evaluados": int(has_sales.sum()), "cohorte": int(cohort.sum()),
                    "observaciones": int(actual.size), "unidades": float(actual.sum())},
        "folds": pd.DataFrame(folds),
        "segments": pd.DataFrame(segments),
    }
