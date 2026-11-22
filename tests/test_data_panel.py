"""Integridad del panel semanal derivado (data/processed/uk_product_week_sales.csv)."""
import json

import pandas as pd
import pytest


@pytest.fixture(scope="module")
def panel(panel_path):
    return pd.read_csv(panel_path, dtype={"StockCode_str": str}, parse_dates=["WeekStart"])


def test_panel_has_expected_columns(panel):
    assert {"StockCode_str", "WeekStart", "UnitsSold"} <= set(panel.columns)


def test_no_duplicate_item_week_rows(panel):
    assert not panel.duplicated(["StockCode_str", "WeekStart"]).any()


def test_units_are_positive(panel):
    assert (panel["UnitsSold"] > 0).all()


def test_codes_have_no_float_suffix(panel):
    """Regresión: una versión anterior guardaba los códigos numéricos como '10002.0'."""
    assert not panel["StockCode_str"].str.endswith(".0").any()


def test_weeks_are_mondays_within_expected_span(panel):
    assert (panel["WeekStart"].dt.day_of_week == 0).all()
    assert panel["WeekStart"].min() == pd.Timestamp("2009-12-07")
    assert panel["WeekStart"].max() == pd.Timestamp("2011-11-28")


def test_total_units_match_audit_profile(panel, root):
    """Regresión: el panel contaba dos veces el solapamiento de hojas del 1-9 dic 2010 (+162.920 unidades)."""
    profile = json.loads((root / "reports" / "eda" / "dataset_profile.json").read_text(encoding="utf-8"))
    assert int(panel["UnitsSold"].sum()) == profile["uk_full_week_units"] == 9_076_096


def test_overlap_weeks_are_not_double_counted(panel):
    weekly = panel.groupby("WeekStart")["UnitsSold"].sum()
    neighbours = weekly[(weekly.index >= "2010-11-08") & (weekly.index <= "2010-11-22")].mean()
    for week in ("2010-11-29", "2010-12-06"):
        assert weekly[pd.Timestamp(week)] < 3 * neighbours


def test_loader_builds_104_week_cohort(bt, panel_path):
    Y, weeks, skus, profile = bt.load_bench_module().load_panel(panel_path, train_end=56, min_active=20)
    assert Y.shape == (2201, 104)
    assert len(weeks) == 104 and len(skus) == 2201
    assert profile["weeks_with_no_recorded_UK_sales"] == ["2009-12-28", "2010-12-27"]
    assert Y[:, 56:].sum() == 2_788_116
