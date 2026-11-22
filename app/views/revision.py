"""Pantalla 5 · Revisión y corrección: alertas de volumen inusual y ajuste del pronóstico."""
import pandas as pd
import streamlit as st

import common
from stockia import storage


def render() -> None:
    ds, analysis, run_id = common.require_analysis()
    st.title("🚩 Revisión y corrección")
    st.caption("Pedidos de volumen inusual detectados para que usted decida cómo tratarlos y corrija el pronóstico si corresponde.")
    if ds.alerts is None:
        st.info("Este archivo no trae líneas de factura (es un panel semanal), por lo que no se pueden detectar pedidos de volumen inusual.")
        return

    conn = common.conn()
    n_excl = len(storage.exclusions(conn))
    st.caption(f"Líneas excluidas del historial: {n_excl}. Nada se elimina automáticamente: las exclusiones se aplican solo cuando usted recalcula.")
    if st.button("Recalcular pronósticos con las exclusiones", disabled=n_excl == 0):
        with st.spinner("Recalculando…"):
            new_id = common.run_analysis(note=f"recalculado con {n_excl} exclusiones")
        st.success(f"Nueva ejecución #{new_id} registrada en el historial.")
        st.rerun()

    st.divider()

    decisions = storage.load_alert_decisions(common.conn())
    alerts = ds.alerts.copy()
    alerts["Date"] = alerts["Date"].astype(str)
    key = decisions.assign(date=decisions["date"].astype(str))[["sku", "date", "units", "decision"]]
    alerts = alerts.merge(key, left_on=["SKU", "Date", "Units"], right_on=["sku", "date", "units"], how="left")
    alerts["Estado"] = alerts["decision"].fillna("Pendiente")

    c1, c2, c3 = st.columns([2, 2, 3])
    state_filter = c1.multiselect("Estado", list(storage.ALERT_DECISIONS), default=["Pendiente"], placeholder="Todos")
    top = c2.slider("Mostrar las N mayores", 10, 200, 50, step=10)
    query = c3.text_input("Buscar por código o descripción")
    view = alerts
    if state_filter:
        view = view[view["Estado"].isin(state_filter)]
    if query:
        q = query.strip().lower()
        view = view[view["SKU"].str.lower().str.contains(q) | view["Description"].str.lower().str.contains(q)]
    view = view.sort_values("Times", ascending=False).head(top).reset_index(drop=True)
    if view.empty:
        st.success("No hay alertas con esos filtros.")
        return

    st.caption(f"{len(ds.alerts)} alertas en el período · regla: ≥ 100 veces la mediana de unidades por factura del artículo y "
               "≥ 500 unidades. No se muestran identificadores de clientes.")
    shown = view[["SKU", "Description", "Date", "Units", "MedianUnits", "Times", "Estado"]].rename(
        columns={"Description": "Producto", "Date": "Fecha", "Units": "Cantidad", "MedianUnits": "Mediana/factura", "Times": "Veces"})
    event = st.dataframe(shown, hide_index=True, width="stretch", height=300, on_select="rerun", selection_mode="single-row",
                         column_config={"Veces": st.column_config.NumberColumn(format="%.0f×"),
                                        "Cantidad": st.column_config.NumberColumn(format="%d")})
    picked = event.selection.rows[0] if event.selection.rows else 0
    row = view.iloc[picked]

    st.subheader(f"Detalle · {row.Description or row.SKU} ({row.SKU})")
    st.write(f"Una factura del **{row.Date}** registra **{common.num(row.Units)} uds**, "
             f"**{common.num(row.Times)}×** la mediana habitual del artículo ({common.num(row.MedianUnits)} uds por factura).")
    hit = analysis.table[analysis.table["sku"] == row.SKU]
    if not hit.empty:
        p = hit.iloc[0]
        a, b = st.columns(2)
        a.metric("Media 4 sem. (con el pico)", f"{common.num(p.referencia_media4)} uds")
        b.metric("Pronóstico TSB", f"{common.num(p.pronostico_tsb)} uds")
        if p.referencia_media4 > 1.5 * max(p.pronostico_tsb, 1):
            st.warning("El pedido extraordinario eleva el promedio móvil a más de una vez y media el pronóstico TSB. "
                       "Si fue un evento puntual, conviene no extrapolarlo.")

    st.markdown("**¿Qué fue este pedido?**")
    d1, d2, d3 = st.columns(3)
    note = st.text_input("Motivo o nota (opcional)", key=f"note_{row.SKU}_{row.Date}_{row.Units}")
    if d1.button("Pedido extraordinario (conservar)", width="stretch"):
        storage.save_alert_decision(conn, row.SKU, row.Date, row.Units, "Conservado", note)
        st.rerun()
    if d2.button("Error de registro (excluir)", width="stretch"):
        storage.save_alert_decision(conn, row.SKU, row.Date, row.Units, "Excluido", note)
        st.rerun()
    if d3.button("Revisar después", width="stretch"):
        storage.save_alert_decision(conn, row.SKU, row.Date, row.Units, "Pendiente", note)
        st.rerun()

    if not hit.empty:
        st.markdown("**Corregir pronóstico**")
        p = hit.iloc[0]
        e1, e2 = st.columns([1, 3])
        value = e1.number_input("Valor ajustado (uds)", min_value=0, value=int(round(p.pronostico_tsb)), key=f"adj_{row.SKU}")
        reason = e2.text_input("Motivo del ajuste", placeholder="p. ej. pedido puntual, sin recurrencia", key=f"adjn_{row.SKU}")
        if st.button("Guardar ajuste"):
            storage.update_review(conn, run_id, row.SKU, "Ajustado", float(value), reason)
            st.toast("Ajuste guardado en el historial.")
    common.ia_box("líneas de factura por artículo y su distribución histórica de unidades por factura.",
                  "alerta con su motivo (cantidad muy superior a la habitual). No predice ventas futuras ni identifica si el "
                  "comprador es mayorista; la decisión es de la persona usuaria.")
