"""Métodos de pronóstico, métricas y segmentación de demanda de StockIA.

Compartido por el backtesting (scripts/05_backtesting_model_selection.py) y la aplicación web.
Convención: para una matriz Y (artículos x semanas), F[:, t] es el pronóstico de la semana t
usando solo las semanas anteriores a t; F tiene T+1 columnas (la última es la semana siguiente).
"""
import numpy as np

ALPHAS = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50]
ADI_CUT, CV2_CUT = 1.32, 0.49
SEGMENTS = ["smooth", "erratic", "intermittent", "lumpy"]


def wape(actual, pred):
    denom = float(np.abs(actual).sum())
    return float(100 * np.abs(actual - pred).sum() / denom) if denom else float("nan")


def score(actual, pred):
    actual = np.asarray(actual, dtype=float)
    pred = np.maximum(0.0, np.asarray(pred, dtype=float))
    err = pred - actual
    return {
        "WAPE_pct": wape(actual, pred),
        "MAE": float(np.abs(err).mean()),
        "RMSE": float(np.sqrt((err ** 2).mean())),
        "bias_pct": float(100 * err.sum() / actual.sum()) if actual.sum() else float("nan"),
        "actual_units": float(actual.sum()),
        "predicted_units": float(pred.sum()),
    }


# ---------------------------------------------------------------------------
# Métodos estadísticos. Cada función devuelve F de forma (n, T+1) donde F[:, t]
# es el pronóstico de la semana t usando solo semanas < t.
# ---------------------------------------------------------------------------

def forecast_last_week(Y):
    return np.concatenate([np.zeros((Y.shape[0], 1)), Y], axis=1)


def forecast_moving_average(Y, k):
    n, T = Y.shape
    F = np.zeros((n, T + 1))
    for t in range(1, T + 1):
        F[:, t] = Y[:, max(0, t - k):t].mean(axis=1)
    return F


def forecast_tsb(Y, alpha, beta):
    """Teunter-Syntetos-Babai. Se inicializa en la primera venta positiva (p=1, z=y)."""
    n, T = Y.shape
    F = np.zeros((n, T + 1))
    p = np.zeros(n)
    z = np.zeros(n)
    started = np.zeros(n, dtype=bool)
    for t in range(T):
        F[:, t] = np.where(started, p * z, 0.0)
        y = Y[:, t]
        positive = y > 0
        newly = ~started & positive
        p = np.where(newly, 1.0, p)
        z = np.where(newly, y, z)
        p = np.where(started, p + beta * (positive.astype(float) - p), p)
        z = np.where(started & positive, z + alpha * (y - z), z)
        started |= newly
    F[:, T] = np.where(started, p * z, 0.0)
    return F


def forecast_croston(Y, alpha, sba=False):
    """Croston (y SBA con factor 1 - alfa/2). Intervalo inicial = semanas hasta la primera venta."""
    n, T = Y.shape
    F = np.zeros((n, T + 1))
    factor = (1 - alpha / 2) if sba else 1.0
    z = np.zeros(n)
    p = np.ones(n)
    q = np.zeros(n)
    started = np.zeros(n, dtype=bool)
    for t in range(T):
        F[:, t] = np.where(started, z / p, 0.0) * factor
        y = Y[:, t]
        q = q + 1
        positive = y > 0
        newly = ~started & positive
        update = started & positive
        z = np.where(newly, y, np.where(update, z + alpha * (y - z), z))
        p = np.where(newly, q, np.where(update, p + alpha * (q - p), p))
        q = np.where(positive, 0, q)
        started |= newly
    F[:, T] = np.where(started, z / p, 0.0) * factor
    return F


def statistical_candidates(Y):
    C = {
        "last_week": forecast_last_week(Y),
        "mean_4": forecast_moving_average(Y, 4),
        "mean_13": forecast_moving_average(Y, 13),
    }
    for a in ALPHAS:
        C[f"croston_{a:.2f}"] = forecast_croston(Y, a)
        C[f"sba_{a:.2f}"] = forecast_croston(Y, a, sba=True)
        C[f"tsb_{a:.2f}"] = forecast_tsb(Y, a, a)
    return C


# ---------------------------------------------------------------------------
# Segmentación ADI/CV² con historial disponible hasta el origen.
# ---------------------------------------------------------------------------

def adi_cv2(Y, origin):
    """ADI (intervalo medio entre ventas) y CV² (variabilidad de las cantidades positivas) con el historial anterior a `origin`."""
    hist = Y[:, :origin]
    adi = np.full(len(hist), np.inf)
    cv2 = np.zeros(len(hist))
    for i, h in enumerate(hist):
        pos = h[h > 0]
        npos = len(pos)
        if npos:
            adi[i] = origin / npos
        mean_pos = pos.mean() if npos else 0.0
        if npos > 1 and mean_pos > 0:
            cv2[i] = float(np.var(pos, ddof=1) / mean_pos ** 2)
    return adi, cv2


def classify(adi, cv2):
    """Clasificación de Syntetos, Boylan y Croston (2005) con umbrales ADI = 1,32 y CV² = 0,49."""
    labels = []
    for a, c in zip(adi, cv2):
        if a < ADI_CUT:
            labels.append("smooth" if c < CV2_CUT else "erratic")
        else:
            labels.append("intermittent" if c < CV2_CUT else "lumpy")
    return np.array(labels)


def segment_at(Y, origin):
    """Patrón de demanda de cada artículo usando solo las semanas anteriores a `origin`."""
    return classify(*adi_cv2(Y, origin))
