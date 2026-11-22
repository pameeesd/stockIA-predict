"""Arnés para probar cada pantalla de la app con streamlit.testing (las páginas son funciones, no scripts).

Variables de entorno: STOCKIA_TEST_PAGE (inicio|datos|pronosticos|historial|revision|metricas) y
STOCKIA_TEST_DEMO=1 para dejar cargados los datos de demostración y un análisis ejecutado.
"""
import importlib
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT))

import common  # noqa: E402

common.setup()
if os.environ.get("STOCKIA_TEST_DEMO") == "1" and "analysis" not in st.session_state:
    st.session_state["user"] = "Prueba"
    common.set_dataset(common.demo_dataset())
    common.run_analysis(note="prueba")

importlib.import_module(f"views.{os.environ['STOCKIA_TEST_PAGE']}").render()
