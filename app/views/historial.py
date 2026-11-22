"""Pantalla 4 · Historial de ejecuciones."""
import json

import streamlit as st

import common
from stockia import storage


def render() -> None:
    st.title("🗂️ Historial de ejecuciones")
    st.caption("Cada análisis queda registrado con su archivo, corte de datos, método y parámetros para poder reproducirlo.")
    runs = storage.list_runs(common.conn())
    if runs.empty:
        st.info("Todavía no hay ejecuciones. Ejecute un análisis en **Datos** o use los datos de demostración en **Inicio**.")
        return

    show = runs.rename(columns={"id": "N.º", "created_at": "Fecha de ejecución", "source": "Fuente", "data_cutoff": "Corte de datos",
                                "n_items": "Artículos", "alpha": "α (TSB)", "weeks": "Semanas"})
    st.dataframe(show.drop(columns=["params"]), hide_index=True, width="stretch")

    run_id = st.selectbox("Ver los pronósticos de la ejecución", runs["id"].tolist(),
                          format_func=lambda i: f"#{i} · {runs.loc[runs['id'] == i, 'created_at'].iloc[0]}")
    params = json.loads(runs.loc[runs["id"] == run_id, "params"].iloc[0])
    st.caption(f"Parámetros: {params}")
    fc = storage.load_forecasts(common.conn(), run_id)
    c1, c2 = st.columns(2)
    segs = c1.multiselect("Filtrar por patrón", sorted(fc["segment"].dropna().unique()), placeholder="Todos")
    status = c2.multiselect("Estado de revisión", list(storage.REVIEW_STATES), placeholder="Todos")
    if segs:
        fc = fc[fc["segment"].isin(segs)]
    if status:
        fc = fc[fc["review_status"].isin(status)]
    out = fc.rename(columns={"sku": "Código", "description": "Producto", "segment": "Patrón", "reliability": "Fiabilidad",
                             "tsb": "Pronóstico TSB", "reference": "Media 4 sem.", "review_status": "Revisión",
                             "adjusted": "Valor ajustado", "note": "Nota"}).drop(columns=["run_id"])
    out["Pronóstico TSB"] = out["Pronóstico TSB"].round(0)
    out["Media 4 sem."] = out["Media 4 sem."].round(0)
    st.dataframe(out, hide_index=True, width="stretch", height=420)
    st.download_button("Exportar CSV", out.to_csv(index=False).encode("utf-8"), file_name=f"stockia_ejecucion_{run_id}.csv",
                       mime="text/csv")
    st.caption("La exportación no incluye identificadores de clientes ni números de factura.")
    common.ia_box("pronóstico, referencia, patrón, fiabilidad, α, corte de datos y la decisión de la persona usuaria.",
                  "consulta por ejecución, producto o patrón, y exportación a CSV.")
