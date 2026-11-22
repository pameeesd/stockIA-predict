"""Pantalla 2 · Ingreso de datos y validación."""
import pandas as pd
import streamlit as st

import common
from stockia import ingest, pipeline


def _quality_cards(q: dict) -> None:
    if not q:
        return
    rows = q.get("rows", q.get("raw_rows"))
    a, b, c = st.columns(3)
    a.metric("Filas leídas", common.num(rows))
    if "exact_duplicates" in q:
        b.metric("Duplicados exactos", common.num(q["exact_duplicates"]), f"{common.num(q['exact_duplicates_pct'], 2)} % · se eliminan",
                 delta_color="off", delta_arrow="off")
        c.metric("Cancelaciones (prefijo C)", common.num(q["cancellations"]), "no cuentan como venta", delta_color="off", delta_arrow="off")
        d, e, f = st.columns(3)
        d.metric("Cantidades negativas", common.num(q["negative_quantity"]), "devoluciones / ajustes", delta_color="off", delta_arrow="off")
        if q.get("missing_customer_id_pct") is not None:
            e.metric("Sin Customer ID", common.pct(q["missing_customer_id_pct"]), "no se usa", delta_color="off", delta_arrow="off")
        f.markdown(f"**Rango de fechas**  \n{str(q['date_min'])[:10]} → {str(q['date_max'])[:10]}")


def _after_analysis() -> None:
    ds, analysis = st.session_state["ds"], st.session_state["analysis"]
    st.success(f"Análisis listo: {common.num(analysis.meta['items'])} artículos · {len(ds.weeks)} semanas completas "
               f"({len(ds.zero_weeks)} sin ventas, tratadas como 0) · α elegido = {common.num(analysis.meta['alpha'], 2)} · "
               f"ejecución #{st.session_state['run_id']}.")
    st.write("Continúe en **Pronósticos** para ver el resultado por producto.")


def render() -> None:
    st.title("📥 Ingreso de datos")
    st.caption("Cargue un archivo de ventas, revise su calidad y ejecute el análisis.")
    st.info(common.DISCLAIMER)

    source = st.radio("Origen de los datos", ["Datos de demostración (UCI Online Retail II)", "Subir un archivo CSV/XLSX"],
                      horizontal=True)

    if source.startswith("Datos de demostración"):
        ds = common.demo_dataset()
        st.markdown("**Validación de calidad del archivo original** (1.067.371 filas, dos hojas del libro de UCI)")
        _quality_cards(ds.quality)
        st.caption("Panel semanal del Reino Unido: 104 semanas completas, 2 sin ventas (2009-12-28 y 2010-12-27). "
                   "Customer ID se excluye del modelo y de las salidas.")
        if st.button("Ejecutar análisis con datos de demostración", type="primary"):
            with st.spinner("Calculando pronósticos y backtesting…"):
                common.set_dataset(ds)
                common.run_analysis(note="demostración")
            _after_analysis()
    else:
        file = st.file_uploader("Archivo de ventas", type=["csv", "xlsx"],
                                help="Transacciones (InvoiceNo, StockCode, Quantity, InvoiceDate, …) o un panel semanal "
                                     "(StockCode, WeekStart, UnitsSold).")
        if file is None:
            st.caption("Los archivos grandes (p. ej. el Excel original de 45 MB) pueden tardar un minuto en leerse.")
        else:
            try:
                with st.spinner("Leyendo y validando el archivo…"):
                    df = ingest.read_table(file, file.name)
                    info = pipeline.inspect_upload(df)
            except ingest.DataError as exc:
                st.error(str(exc))
                return
            except Exception as exc:  # archivo ilegible
                st.error(f"No se pudo leer el archivo: {exc}")
                return

            country = None
            if info["format"] == "transactions":
                st.markdown("**Mapeo de columnas**")
                mapping = info["mapping"]
                st.dataframe(pd.DataFrame({"Columna del archivo": list(mapping), "Campo de StockIA": list(mapping.values())}),
                             hide_index=True, width="stretch")
                st.markdown("**Validación de calidad**")
                _quality_cards(info["quality"])
                countries = info["countries"]
                if countries:
                    default = countries.index("United Kingdom") if "United Kingdom" in countries else 0
                    country = st.selectbox("País (mercado a analizar)", countries, index=default)
                if info["quality"]["invalid_dates"] or info["quality"]["invalid_quantities"]:
                    st.warning(f"Filas con fecha inválida: {info['quality']['invalid_dates']}; con cantidad inválida: "
                               f"{info['quality']['invalid_quantities']}. Se descartarán.")
            else:
                st.success(f"Panel semanal reconocido ({common.num(info['rows'])} filas).")

            if st.button("Ejecutar análisis", type="primary"):
                try:
                    with st.spinner("Preparando el panel semanal y calculando pronósticos…"):
                        file.seek(0)
                        ds = pipeline.load_upload(df, file.name, country=country)
                        common.set_dataset(ds)
                        common.run_analysis(note="archivo cargado")
                except ingest.DataError as exc:
                    st.error(str(exc))
                    return
                _after_analysis()

    if "analysis" in st.session_state:
        st.divider()
        common.ia_box("ventas positivas (artículo, cantidad, fecha); Customer ID se excluye.",
                      "serie semanal de unidades por artículo (ceros en semanas sin venta), lista para segmentar y pronosticar.")
