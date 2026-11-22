"""Alertas de volumen inusual y cobertura de stock informativa."""
from __future__ import annotations

import math

import pandas as pd

ALERT_FACTOR = 100.0  # veces la mediana de unidades por factura del artículo
ALERT_MIN_UNITS = 500  # unidades mínimas de la línea para alertar
ALERT_MIN_LINES = 5    # historial mínimo (facturas) del artículo para calcular una mediana fiable


def detect_volume_alerts(lines: pd.DataFrame, factor: float = ALERT_FACTOR, min_units: int = ALERT_MIN_UNITS,
                         min_lines: int = ALERT_MIN_LINES) -> pd.DataFrame:
    """Facturas cuyo volumen por artículo supera `factor` veces la mediana habitual del artículo.

    `lines` son líneas de venta limpias (ver stockia.ingest.clean_lines). No se devuelven números de factura
    ni identificadores de clientes.
    """
    per_invoice = (lines.groupby(["StockCode_str", "InvoiceNo_str"], as_index=False)
                   .agg(Units=("Quantity", "sum"), Date=("InvoiceDate", "min")))
    desc = (lines.dropna(subset=["Description"]).groupby("StockCode_str")["Description"]
            .agg(lambda s: s.mode().iat[0]) if "Description" in lines.columns else pd.Series(dtype=str))
    stats = per_invoice.groupby("StockCode_str")["Units"].agg(MedianUnits="median", Invoices="size").reset_index()
    merged = per_invoice.merge(stats, on="StockCode_str")
    merged["Times"] = merged["Units"] / merged["MedianUnits"]
    alerts = merged[(merged["Times"] >= factor) & (merged["Units"] >= min_units) & (merged["Invoices"] >= min_lines)].copy()
    alerts["Date"] = alerts["Date"].dt.date
    alerts["Description"] = alerts["StockCode_str"].map(desc).fillna("")
    alerts = alerts.rename(columns={"StockCode_str": "SKU"})
    cols = ["SKU", "Description", "Date", "Units", "MedianUnits", "Times", "Invoices"]
    return alerts[cols].sort_values("Times", ascending=False).reset_index(drop=True)


def stock_coverage(weekly_forecast: float, stock: float, lead_weeks: float, safety_weeks: float) -> dict:
    """Cobertura de stock informativa (no validada): supone demanda constante igual al pronóstico semanal.

    cobertura (semanas) = stock / pronóstico; cantidad referencial = max(0, pronóstico × (plazo + seguridad) − stock).
    """
    forecast = max(0.0, float(weekly_forecast))
    coverage = math.inf if forecast == 0 else float(stock) / forecast
    order = max(0.0, forecast * (float(lead_weeks) + float(safety_weeks)) - float(stock))
    return {
        "coverage_weeks": coverage,
        "reference_order": order,
        "below_lead_time": coverage < float(lead_weeks),
        "formula": f"{forecast:,.0f} × ({lead_weeks:g} + {safety_weeks:g}) − {stock:,.0f}".replace(",", "."),
    }
