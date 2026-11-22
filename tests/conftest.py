"""Fixtures compartidas. Los scripts se llaman 05_*.py (no importables por nombre), así que se cargan por ruta."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "processed" / "uk_product_week_sales.csv"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def bt():
    """Módulo scripts/05_backtesting_model_selection.py."""
    return _load("stockia_backtesting", "05_backtesting_model_selection.py")


@pytest.fixture(scope="session")
def root():
    return ROOT


@pytest.fixture(scope="session")
def panel_path():
    return PANEL


@pytest.fixture
def rng():
    return np.random.default_rng(7)
