"""Pruebas de la interfaz Streamlit con streamlit.testing (AppTest). Cada pantalla se monta con el arnés tests/app_harness.py."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from stockia import storage  # noqa: E402

HARNESS = str(Path(__file__).with_name("app_harness.py"))
TIMEOUT = 180


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Cada prueba usa su propia base SQLite."""
    monkeypatch.setattr(storage, "DEFAULT_DB", tmp_path / "app.db")


def open_page(monkeypatch, page, demo=True):
    monkeypatch.setenv("STOCKIA_TEST_PAGE", page)
    monkeypatch.setenv("STOCKIA_TEST_DEMO", "1" if demo else "0")
    return AppTest.from_file(HARNESS, default_timeout=TIMEOUT).run()


def metric_values(at):
    return [m.value for m in at.metric]


def by_label(widgets, text):
    return [w for w in widgets if text.lower() in w.label.lower()][0]


@pytest.mark.parametrize("page", ["inicio", "datos", "pronosticos", "historial", "revision", "metricas"])
def test_every_page_renders_without_errors(monkeypatch, page):
    at = open_page(monkeypatch, page)
    assert not at.exception, [e.value for e in at.exception]


def test_inicio_demo_button_runs_analysis(monkeypatch):
    at = open_page(monkeypatch, "inicio", demo=False)
    assert not at.exception and "analysis" not in at.session_state
    by_label(at.button, "demostración").click().run()
    assert not at.exception
    assert at.session_state["analysis"].meta["items"] == 4769 and at.session_state["run_id"] == 1


def test_inicio_requires_a_name(monkeypatch):
    at = open_page(monkeypatch, "inicio", demo=False)
    by_label(at.button, "Entrar").click().run()
    assert any("nombre" in w.value.lower() for w in at.warning) and "user" not in at.session_state


def test_pages_without_analysis_ask_for_data(monkeypatch):
    for page in ("pronosticos", "metricas", "revision"):
        at = open_page(monkeypatch, page, demo=False)
        assert not at.exception
        assert any("cargue datos" in i.value.lower() for i in at.info)


def test_pronosticos_shows_expected_numbers(monkeypatch):
    at = open_page(monkeypatch, "pronosticos")
    values = metric_values(at)
    assert "724 uds" in values and "727 uds" in values        # TSB y referencia del producto 85123A
    assert "1,7 sem." in values and "971 uds" in values       # cobertura de stock del ejemplo
    assert any("Cobertura de stock" in m.value for m in at.markdown)


def test_pronosticos_stock_inputs_change_the_coverage(monkeypatch):
    at = open_page(monkeypatch, "pronosticos")
    by_label(at.number_input, "Stock actual").set_value(5000).run()
    values = metric_values(at)
    assert "0 uds" in values and not any(v == "971 uds" for v in values)


def test_pronosticos_low_reliability_warning(monkeypatch):
    at = open_page(monkeypatch, "pronosticos")
    at.selectbox[0].set_value("16014").run()   # AppTest recibe el valor (código), no la etiqueta formateada
    assert any("Revisión manual recomendada" in w.value for w in at.warning)


def test_accept_forecast_is_saved_in_history(monkeypatch):
    at = open_page(monkeypatch, "pronosticos")
    by_label(at.button, "Aceptar este pronóstico").click().run()
    conn = storage.connect(storage.DEFAULT_DB)
    fc = storage.load_forecasts(conn, 1).set_index("sku")
    assert fc.loc["85123A", "review_status"] == "Aceptado"


def test_metricas_shows_official_figures(monkeypatch):
    at = open_page(monkeypatch, "metricas")
    values = metric_values(at)
    assert "77,00 %" in values and "78,65 %" in values and "-6,13 %" in values and "59,2 %" in values


def test_historial_lists_the_run(monkeypatch):
    at = open_page(monkeypatch, "historial")
    assert len(at.dataframe) >= 2 and not at.exception


def test_revision_exclude_and_recalculate_flow(monkeypatch):
    """Excluir el pedido de 12.540 uds del artículo 84826 y recalcular debe bajar su pronóstico."""
    at = open_page(monkeypatch, "revision")
    search = by_label(at.text_input, "Buscar")
    search.set_value("84826").run()
    assert not at.exception
    by_label(at.button, "Error de registro").click().run()
    conn = storage.connect(storage.DEFAULT_DB)
    ex = storage.exclusions(conn)
    assert list(ex["sku"]) == ["84826"] and ex["units"].iloc[0] == 12540

    # la línea excluida deja de listarse (el filtro por defecto es «Pendiente»), pero «Recalcular» sigue disponible
    recalc = by_label(at.button, "Recalcular")
    assert not recalc.disabled
    recalc.click().run()
    assert at.session_state["run_id"] == 2
    new = at.session_state["analysis"]
    assert new.meta["excluded_lines"] == 1
    assert new.table.set_index("sku").loc["84826", "pronostico_tsb"] < 10
    assert len(storage.list_runs(conn)) == 2
