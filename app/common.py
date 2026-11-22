"""Utilidades compartidas por las pantallas de la app (estado de sesión, formato, estilos)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stockia import pipeline, storage  # noqa: E402

DISCLAIMER = ("StockIA pronostica **ventas observadas**: no conoce el stock, las ventas perdidas ni los plazos de "
              "proveedores, y no genera órdenes de compra. La decisión es siempre de la persona usuaria.")

CSS = """
<style>
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.78rem;font-weight:700}
.b-alta{background:#e5f4ec;color:#2f8f5b}.b-media{background:#fff3dc;color:#b87708}.b-baja{background:#fde9e7;color:#c8453b}
.ia-box{border:2px dashed #0e9f8e;background:rgba(14,159,142,.07);border-radius:12px;padding:.8rem 1rem;font-size:.9rem}
.ia-box b.t{color:#0e9f8e;letter-spacing:.05em;font-size:.75rem}
</style>
"""


def setup() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def num(x, decimals: int = 0) -> str:
    """Formato es-CL: punto para miles y coma para decimales."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x, decimals: int = 2) -> str:
    return f"{num(x, decimals)} %"


def badge(level: str) -> str:
    cls = {"Alta": "b-alta", "Media": "b-media", "Baja": "b-baja"}.get(level, "b-media")
    return f'<span class="badge {cls}">Fiabilidad {level}</span>'


def ia_box(entra: str, sale: str) -> None:
    st.markdown(f'<div class="ia-box"><b class="t">IA · DATOS DE ENTRADA Y SALIDA</b><br>'
                f'<b>Entra:</b> {entra}<br><b>Sale:</b> {sale}</div>', unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def demo_dataset() -> pipeline.Dataset:
    return pipeline.load_demo()


def conn():
    """Conexión SQLite de la sesión (ruta configurable con STOCKIA_DB)."""
    if "conn" not in st.session_state:
        st.session_state["conn"] = storage.connect()
    return st.session_state["conn"]


def set_dataset(ds: pipeline.Dataset) -> None:
    st.session_state["ds"] = ds
    st.session_state.pop("analysis", None)
    st.session_state.pop("run_id", None)


def run_analysis(note: str = "") -> int:
    """Ejecuta el análisis con las exclusiones guardadas, lo registra en el historial y deja el resultado en la sesión."""
    ds: pipeline.Dataset = st.session_state["ds"]
    excl = storage.exclusions(conn())
    analysis = pipeline.analyze(ds, excl)
    run_id = storage.save_run(conn(), ds.source, ds.cutoff, analysis.meta, analysis.table,
                              params={"kind": ds.kind, "country": ds.country, "excluded_lines": analysis.meta["excluded_lines"],
                                      "note": note})
    st.session_state["analysis"] = analysis
    st.session_state["run_id"] = run_id
    return run_id


def require_analysis():
    """Detiene la pantalla con un aviso si todavía no hay un análisis ejecutado."""
    if "analysis" not in st.session_state:
        st.info("Primero cargue datos y ejecute el análisis en **Datos** (o use los datos de demostración en **Inicio**).")
        st.stop()
    return st.session_state["ds"], st.session_state["analysis"], st.session_state["run_id"]
