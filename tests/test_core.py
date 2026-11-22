"""Pruebas del paquete stockia (ingesta, motor, backtest, alertas, cobertura, almacenamiento, pipeline)."""
import threading

import numpy as np
import pandas as pd
import pytest

from stockia import alerts, backtest, engine, ingest, pipeline, storage


# ----------------------------------------------------------------------------- datos sintéticos
@pytest.fixture(scope="module")
def raw_transactions():
    """~40 semanas de transacciones con suciedad típica: duplicados, cancelaciones, negativos, otro país, código no comercial."""
    rng = np.random.default_rng(3)
    days = pd.date_range("2020-01-02", periods=290, freq="D")  # empieza en jueves: la 1.ª semana queda parcial
    rows = []
    n = 1000
    for d in days:
        for sku, desc in (("A1", "ALPHA"), ("b2", "BETA"), ("C3", "GAMMA")):
            if rng.random() < 0.55:
                n += 1
                rows.append([f"{n}", sku, desc, int(rng.integers(1, 12)), d + pd.Timedelta(hours=10), 2.5, 12345.0, "United Kingdom"])
    df = pd.DataFrame(rows, columns=["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"])
    extra = pd.DataFrame([
        ["C9001", "A1", "ALPHA", -3, pd.Timestamp("2020-03-10 09:00"), 2.5, 12345.0, "United Kingdom"],   # cancelación
        ["9002", "A1", "ALPHA", -2, pd.Timestamp("2020-03-11 09:00"), 2.5, 12345.0, "United Kingdom"],    # cantidad negativa
        ["9003", "A1", "ALPHA", 5, pd.Timestamp("2020-03-12 09:00"), 2.5, None, "France"],                # otro país
        ["9004", "POST", "POSTAGE", 1, pd.Timestamp("2020-03-12 09:00"), 9.0, 1.0, "United Kingdom"],     # no comercial
        ["9005", "A1", "ALPHA", 5000, pd.Timestamp("2020-05-14 09:00"), 2.5, 12345.0, "United Kingdom"],  # pedido enorme
    ], columns=df.columns)
    out = pd.concat([df, extra], ignore_index=True)
    return pd.concat([out, out.iloc[:7]], ignore_index=True)  # 7 duplicados exactos


# ----------------------------------------------------------------------------- ingesta
def test_map_columns_accepts_aliases():
    df = pd.DataFrame(columns=["Invoice", "SKU", "Cantidad", "Fecha", "Customer ID", "Price"])
    mapped, mapping = ingest.map_columns(df)
    assert {"InvoiceNo", "StockCode", "Quantity", "InvoiceDate", "CustomerID", "UnitPrice"} <= set(mapped.columns)
    assert mapping["SKU"] == "StockCode"


def test_detect_format(raw_transactions):
    assert ingest.detect_format(raw_transactions) == "transactions"
    weekly = pd.DataFrame({"StockCode_str": ["A"], "WeekStart": ["2020-01-06"], "UnitsSold": [3]})
    assert ingest.detect_format(weekly) == "weekly"
    with pytest.raises(ingest.DataError, match="No se reconocen"):
        ingest.detect_format(pd.DataFrame({"foo": [1], "bar": [2]}))


def test_read_table_rejects_unknown_extension():
    with pytest.raises(ingest.DataError):
        ingest.read_table("x.txt", "x.txt")


def test_quality_report_counts_dirty_rows(raw_transactions):
    q = ingest.quality_report(raw_transactions)
    assert q["exact_duplicates"] == 7
    assert q["cancellations"] == 1
    assert q["negative_quantity"] == 2          # la cancelación y la devolución
    assert "France" in q["countries"] and q["has_customer_id"]
    assert q["missing_customer_id_pct"] > 0


def test_clean_lines_applies_all_rules(raw_transactions):
    lines = ingest.clean_lines(raw_transactions, country="United Kingdom")
    assert (lines["Quantity"] > 0).all()
    assert not lines["InvoiceNo_str"].str.startswith("C").any()
    assert set(lines["Country"]) == {"United Kingdom"}
    assert not lines.duplicated(["InvoiceNo_str", "StockCode_str"]).any()
    assert set(lines["StockCode_str"]) >= {"A1", "B2", "C3"}   # los códigos se normalizan a mayúsculas


def test_weekly_panel_drops_partial_edge_weeks_and_excludes_non_merchandise(raw_transactions):
    lines = ingest.clean_lines(raw_transactions, country="United Kingdom")
    weekly = ingest.weekly_from_lines(lines)
    assert (weekly["WeekStart"].dt.day_of_week == 0).all()
    # los datos empiezan un jueves (2020-01-02): su semana (lunes 2019-12-30) es parcial y se descarta
    assert weekly["WeekStart"].min() == pd.Timestamp("2020-01-06")
    Y, weeks, skus = ingest.panel_matrix(weekly)
    assert "POST" not in skus and Y.shape[0] == 3 and Y.shape[1] == len(weeks)


def test_panel_matrix_requires_enough_history():
    weekly = pd.DataFrame({"StockCode": ["A"] * 3, "WeekStart": pd.date_range("2020-01-06", periods=3, freq="7D"), "UnitsSold": [1, 2, 3]})
    with pytest.raises(ingest.DataError, match="al menos 30"):
        ingest.panel_matrix(weekly)


# ----------------------------------------------------------------------------- resultados oficiales con el panel demo
@pytest.fixture(scope="module")
def demo():
    return pipeline.load_demo()


def test_backtest_reproduces_official_numbers(demo):
    r = backtest.rolling_backtest(demo.Y, demo.weeks)
    s = r["summary"]
    assert s["WAPE_tsb"] == pytest.approx(77.00, abs=0.005)
    assert s["WAPE_referencia"] == pytest.approx(78.65, abs=0.005)
    assert s["sesgo_tsb"] == pytest.approx(-6.13, abs=0.005)
    assert s["productos_mejores_pct"] == pytest.approx(59.17, abs=0.005)
    assert (s["cohorte"], s["productos_evaluados"], s["observaciones"]) == (2201, 1957, 105648)
    assert list(r["folds"]["alpha"]) == [0.5, 0.5, 0.3, 0.2, 0.3, 0.2]
    seg = r["segments"].set_index("segmento")
    assert seg.loc["erratic", "WAPE_tsb"] == pytest.approx(76.00, abs=0.005)
    assert seg["unidades"].sum() == 2_788_116


def test_backtest_needs_history():
    Y = np.ones((50, 40))
    with pytest.raises(ValueError, match="Historial insuficiente"):
        backtest.rolling_backtest(Y, pd.date_range("2020-01-06", periods=40, freq="7D"))


def test_next_week_forecast_matches_mockups(demo):
    table, meta = engine.forecast_next_week(demo.Y, demo.skus, demo.descriptions)
    assert meta["alpha"] == 0.3 and meta["items"] == 4769
    row = table.set_index("sku").loc["85123A"]
    assert round(row.pronostico_tsb) == 724 and round(row.referencia_media4) == 727
    assert row.segmento == "erratic" and row.fiabilidad == "Media"
    assert row.descripcion == "WHITE HANGING HEART T-LIGHT HOLDER"
    assert (table["pronostico_tsb"] >= 0).all()


@pytest.mark.parametrize("segment,active,expected", [
    ("smooth", 90, "Alta"), ("erratic", 90, "Media"), ("intermittent", 60, "Media"),
    ("lumpy", 90, "Baja"), ("smooth", 12, "Baja"),
])
def test_reliability_rules(segment, active, expected):
    assert engine.reliability(segment, active) == expected


def test_exclusions_remove_units_and_do_not_mutate(demo):
    ex = pd.DataFrame([{"sku": "84826", "date": "2011-11-25", "units": 12540}])
    Y2 = engine.apply_exclusions(demo.Y, demo.weeks, demo.skus, ex)
    i = demo.skus.index("84826")
    j = list(demo.weeks).index(pd.Timestamp("2011-11-21"))
    assert demo.Y[i, j] == 12540 and Y2[i, j] == 0     # el original no se modifica
    t1, _ = engine.forecast_next_week(demo.Y, demo.skus)
    t2, _ = engine.forecast_next_week(Y2, demo.skus)
    f = lambda t: t.set_index("sku").loc["84826", "pronostico_tsb"]  # noqa: E731
    assert f(t1) == pytest.approx(1506, abs=1) and f(t2) < 10


# ----------------------------------------------------------------------------- alertas y cobertura
def test_alert_detection_flags_only_the_huge_line(raw_transactions):
    lines = ingest.clean_lines(raw_transactions, country="United Kingdom")
    found = alerts.detect_volume_alerts(lines)
    assert list(found["SKU"]) == ["A1"] and int(found["Units"].iloc[0]) == 5000
    assert found["Times"].iloc[0] >= alerts.ALERT_FACTOR
    assert not {"InvoiceNo_str", "CustomerID"} & set(found.columns)   # sin identificadores


def test_stock_coverage_matches_mockup():
    c = alerts.stock_coverage(723.5973, 1200, 2, 1)
    assert c["coverage_weeks"] == pytest.approx(1.658, abs=0.001)
    assert round(c["reference_order"]) == 971 and c["below_lead_time"]
    assert c["formula"] == "724 × (2 + 1) − 1.200"


def test_stock_coverage_edge_cases():
    assert alerts.stock_coverage(0, 100, 2, 1)["coverage_weeks"] == float("inf")
    assert alerts.stock_coverage(100, 10_000, 2, 1)["reference_order"] == 0


# ----------------------------------------------------------------------------- almacenamiento
@pytest.fixture
def conn(tmp_path):
    c = storage.connect(tmp_path / "t.db")
    yield c
    c.close()


def _table():
    return pd.DataFrame({"sku": ["A", "B"], "descripcion": ["a", "b"], "segmento": ["smooth", "lumpy"],
                         "fiabilidad": ["Alta", "Baja"], "pronostico_tsb": [10.0, 5.0], "referencia_media4": [9.0, 7.0]})


def test_runs_and_review_roundtrip(conn):
    rid = storage.save_run(conn, "demo", "2011-12-04", {"items": 2, "alpha": 0.3, "weeks": 104}, _table(), {"k": 1})
    assert rid == 1 and len(storage.list_runs(conn)) == 1
    storage.update_review(conn, rid, "A", "Ajustado", 12.0, "motivo")
    fc = storage.load_forecasts(conn, rid).set_index("sku")
    assert fc.loc["A", "review_status"] == "Ajustado" and fc.loc["A", "adjusted"] == 12.0
    assert fc.loc["B", "review_status"] == "Pendiente"
    with pytest.raises(ValueError):
        storage.update_review(conn, rid, "A", "Inventado")


def test_alert_decisions_and_exclusions(conn):
    storage.save_alert_decision(conn, "A", "2011-11-25", 12540, "Excluido", "error")
    storage.save_alert_decision(conn, "B", "2011-11-02", 3000, "Conservado")
    ex = storage.exclusions(conn)
    assert list(ex["sku"]) == ["A"] and ex["units"].iloc[0] == 12540
    storage.save_alert_decision(conn, "A", "2011-11-25", 12540, "Pendiente")   # se puede revertir
    assert storage.exclusions(conn).empty


def test_connection_can_be_used_from_another_thread(conn):
    """Regresión: Streamlit ejecuta cada recarga en un hilo distinto y SQLite lo rechazaba."""
    result = {}
    t = threading.Thread(target=lambda: result.update(runs=len(storage.list_runs(conn))))
    t.start(); t.join()
    assert result == {"runs": 0}


# ----------------------------------------------------------------------------- pipeline
def test_load_upload_end_to_end(raw_transactions):
    ds = pipeline.load_upload(raw_transactions, "sintetico.csv", country="United Kingdom")
    assert ds.kind == "upload" and ds.Y.shape[0] == 3 and len(ds.weeks) >= 30
    assert ds.descriptions["A1"] == "ALPHA"
    assert ds.alerts is not None and list(ds.alerts["SKU"]) == ["A1"]
    a = pipeline.analyze(ds)
    assert a.meta["items"] == 3 and (a.table["pronostico_tsb"] >= 0).all()
    assert a.backtest is None and "Historial insuficiente" in a.backtest_error   # 3 artículos: cohorte muy pequeña o historia corta


def test_demo_dataset_alerts_have_no_identifiers(demo):
    assert demo.alerts is not None and len(demo.alerts) > 100
    assert not {"InvoiceNo", "CustomerID", "Customer ID"} & set(demo.alerts.columns)
    assert {"84826", "16014", "84077"} <= set(demo.alerts["SKU"])


def test_evaluate_runs_compares_saved_forecasts_with_actual_sales(tmp_path):
    """Una ejecución hecha con datos hasta la semana N se evalúa cuando llegan los datos de la semana N+1."""
    full = pipeline.load_demo()
    cut = len(full.weeks) - 1                       # se "olvida" la última semana
    past = pipeline.Dataset(source="x", kind="demo", weeks=full.weeks[:cut], skus=full.skus, Y=full.Y[:, :cut], descriptions={},
                            quality={}, alerts=None)
    conn = storage.connect(tmp_path / "e.db")
    analysis = pipeline.analyze(past)
    storage.save_run(conn, "demo", past.cutoff, analysis.meta, analysis.table)
    assert pipeline.evaluate_runs(conn, past).empty           # con los datos viejos no hay semana real que comparar
    ev = pipeline.evaluate_runs(conn, full)
    assert len(ev) == 1 and str(ev["semana_objetivo"].iloc[0]) == str(full.weeks[-1].date())
    actual = full.Y[:, -1]
    manual = 100 * np.abs(actual[[full.skus.index(s) for s in analysis.table["sku"]]] - analysis.table["pronostico_tsb"].to_numpy()).sum()         / actual[[full.skus.index(s) for s in analysis.table["sku"]]].sum()
    assert ev["WAPE_tsb"].iloc[0] == pytest.approx(manual)
