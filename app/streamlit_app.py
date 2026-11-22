"""StockIA Predict · aplicación web (MVP).

    streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
from views import datos, historial, inicio, metricas, pronosticos, revision  # noqa: E402

st.set_page_config(page_title="StockIA Predict", page_icon="📈", layout="wide")
common.setup()

pages = [
    st.Page(inicio.render, title="Inicio", icon="🏠", url_path="inicio", default=True),
    st.Page(datos.render, title="Datos", icon="📥", url_path="datos"),
    st.Page(pronosticos.render, title="Pronósticos", icon="📈", url_path="pronosticos"),
    st.Page(historial.render, title="Historial", icon="🗂️", url_path="historial"),
    st.Page(revision.render, title="Revisión", icon="🚩", url_path="revision"),
    st.Page(metricas.render, title="Métricas", icon="🎯", url_path="metricas"),
]
nav = st.navigation(pages)

with st.sidebar:
    st.caption("StockIA Predict · prueba de concepto académica")
    user = st.session_state.get("user")
    ds = st.session_state.get("ds")
    st.markdown(f"**Usuario:** {user or '—'}")
    st.markdown(f"**Datos:** {ds.source if ds else '—'}")
    if "run_id" in st.session_state:
        st.markdown(f"**Ejecución:** #{st.session_state['run_id']}")

nav.run()
