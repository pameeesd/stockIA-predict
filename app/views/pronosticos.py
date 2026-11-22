"""Pantalla 3 · Resultado de la IA: pronóstico por producto, fiabilidad y cobertura de stock."""
import altair as alt
import pandas as pd
import streamlit as st

import common
from stockia import alerts, storage


def _chart(ds, row) -> alt.Chart:
    weeks = list(ds.weeks[-len(row.historial):])
    hist = pd.DataFrame({"Semana": weeks, "Unidades": row.historial, "Serie": "Ventas observadas"})
    nxt = pd.Timestamp(ds.weeks[-1]) + pd.Timedelta(days=7)
    fc = pd.DataFrame({"Semana": [weeks[-1], nxt], "Unidades": [row.historial[-1], row.pronostico_tsb], "Serie": "Pronóstico TSB"})
    ref = pd.DataFrame({"Semana": [nxt], "Unidades": [row.referencia_media4], "Serie": "Referencia (media 4 sem.)"})
    color = alt.Color("Serie:N", scale=alt.Scale(domain=["Ventas observadas", "Pronóstico TSB", "Referencia (media 4 sem.)"],
                                                 range=["#0e9f8e", "#3b6fd4", "#8a97ac"]), legend=alt.Legend(orient="bottom"))
    base = alt.Chart(hist).mark_line(point=True).encode(x=alt.X("Semana:T", title=None), y=alt.Y("Unidades:Q"), color=color)
    pred = alt.Chart(fc).mark_line(point=True, strokeDash=[6, 4]).encode(x="Semana:T", y="Unidades:Q", color=color)
    refp = alt.Chart(ref).mark_point(size=110, filled=False).encode(x="Semana:T", y="Unidades:Q", color=color)
    return (base + pred + refp).properties(height=300)


def render() -> None:
    ds, analysis, run_id = common.require_analysis()
    table = analysis.table
    st.title("📈 Resultado de la IA · Pronóstico por producto")
    st.caption(f"Unidades vendidas esperadas para la semana del {analysis.meta['next_week']} (ejecución #{run_id}, "
               f"datos hasta {analysis.meta['cutoff']}).")

    f1, f2, f3 = st.columns([2, 2, 3])
    segs = f1.multiselect("Patrón de demanda", ["smooth", "erratic", "intermittent", "lumpy"], placeholder="Todos")
    rel = f2.multiselect("Fiabilidad", ["Alta", "Media", "Baja"], placeholder="Todas")
    query = f3.text_input("Buscar por código o descripción")
    view = table
    if segs:
        view = view[view["segmento"].isin(segs)]
    if rel:
        view = view[view["fiabilidad"].isin(rel)]
    if query:
        q = query.strip().lower()
        view = view[view["sku"].str.lower().str.contains(q) | view["descripcion"].str.lower().str.contains(q)]
    if view.empty:
        st.warning("Ningún producto coincide con los filtros.")
        return

    options = view.head(500)
    labels = {r.sku: f"{r.sku} · {r.descripcion or 'sin descripción'} · {r.segmento} · fiabilidad {r.fiabilidad}"
              for r in options.itertuples()}
    default = "85123A" if "85123A" in labels else next(iter(labels))
    sku = st.selectbox("Producto", list(labels), index=list(labels).index(default), format_func=labels.get)
    row = table[table["sku"] == sku].iloc[0]

    st.subheader(row.descripcion or row.sku)
    a, b, c, d = st.columns(4)
    a.metric("Pronóstico TSB", f"{common.num(row.pronostico_tsb)} uds", f"α = {common.num(analysis.meta['alpha'], 2)}", delta_color="off", delta_arrow="off")
    b.metric("Referencia · media 4 sem.", f"{common.num(row.referencia_media4)} uds", "método sin IA", delta_color="off", delta_arrow="off")
    c.metric("Patrón de demanda", row.segmento.capitalize(), f"ADI {common.num(row.adi, 2)} · CV² {common.num(row.cv2, 2)}", delta_color="off", delta_arrow="off")
    d.metric("Semanas con venta", common.num(row.semanas_con_venta), f"de {analysis.meta['weeks']}", delta_color="off", delta_arrow="off")

    seg_wape = None
    if analysis.backtest is not None and not analysis.backtest["segments"].empty:
        s = analysis.backtest["segments"]
        hit = s[s["segmento"] == row.segmento]
        seg_wape = float(hit["WAPE_tsb"].iloc[0]) if len(hit) else None

    left, right = st.columns([3, 2])
    with left:
        st.altair_chart(_chart(ds, row), width="stretch")
    with right:
        st.markdown(common.badge(row.fiabilidad), unsafe_allow_html=True)
        if seg_wape is not None:
            st.write(f"En el backtesting, el error de TSB en productos **{row.segmento}** fue **{common.pct(seg_wape, 1)}** (WAPE). "
                     "Úselo como referencia, no como certeza.")
        if row.fiabilidad == "Baja":
            motivo = "patrón lumpy" if row.segmento == "lumpy" else f"menos de 20 semanas con ventas ({row.semanas_con_venta})"
            st.warning(f"**Revisión manual recomendada** ({motivo}). Compare con la referencia antes de usar el pronóstico.")
        with st.expander("¿Cómo se calculó?"):
            st.write("TSB combina la **probabilidad** de que haya venta esa semana con el **tamaño esperado** de una venta, "
                     "y ambos se actualizan cada semana con el historial. El parámetro α se eligió con las 8 semanas más "
                     "recientes, sin usar la semana pronosticada. No se calcula un intervalo de confianza.")

    st.markdown("#### Cobertura de stock (opcional, informativa)")
    st.caption("Datos que ingresa usted; no provienen del archivo. Supone demanda constante igual al pronóstico y no está validada.")
    k1, k2, k3, k4 = st.columns([1, 1, 1, 2])
    stock = k1.number_input("Stock actual (uds)", min_value=0, value=1200, step=50, key=f"stock_{sku}")
    lead = k2.number_input("Plazo de entrega (sem.)", min_value=0.0, value=2.0, step=0.5, key=f"lead_{sku}")
    safety = k3.number_input("Semanas de seguridad", min_value=0.0, value=1.0, step=0.5, key=f"safe_{sku}")
    cov = alerts.stock_coverage(row.pronostico_tsb, stock, lead, safety)
    with k4:
        weeks_txt = "∞" if cov["coverage_weeks"] == float("inf") else common.num(cov["coverage_weeks"], 1)
        st.metric("Cobertura con el stock actual", f"{weeks_txt} sem.",
                  "menor que el plazo de entrega" if cov["below_lead_time"] else "cubre el plazo de entrega",
                  delta_color="inverse" if cov["below_lead_time"] else "off", delta_arrow="off")
        st.metric("Cantidad referencial a pedir", f"{common.num(cov['reference_order'])} uds", cov["formula"], delta_color="off", delta_arrow="off")

    st.divider()
    cols = st.columns([1, 4])
    if cols[0].button("Aceptar este pronóstico"):
        storage.update_review(common.conn(), run_id, sku, "Aceptado")
        st.toast("Pronóstico aceptado y registrado en el historial.")
    common.ia_box("historial semanal del producto, su patrón ADI/CV² y el α elegido en validación interna.",
                  "pronóstico puntual para 1 semana, referencia, patrón y fiabilidad histórica. La cobertura de stock es "
                  "aritmética con datos de la persona usuaria (no es IA).")
