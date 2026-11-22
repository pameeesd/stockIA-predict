"""Pantalla 6 · Métricas de éxito."""
import altair as alt
import pandas as pd
import streamlit as st

import common
from stockia import pipeline


def render() -> None:
    ds, analysis, run_id = common.require_analysis()
    st.title("🎯 Métricas de éxito")
    st.caption("Compara el error del pronóstico de StockIA (TSB) con el método de referencia (media móvil de 4 semanas) "
               "en 6 bloques sucesivos de 8 semanas.")
    if analysis.backtest is None:
        st.warning(f"No se pudo calcular el backtesting con estos datos: {analysis.backtest_error}")
        return
    s = analysis.backtest["summary"]
    folds = analysis.backtest["folds"]

    a, b, c, d = st.columns(4)
    a.metric("WAPE · TSB", common.pct(s["WAPE_tsb"]), f"▼ {common.num(s['mejora_relativa_pct'], 1)} % vs referencia", delta_color="normal", delta_arrow="off")
    b.metric("WAPE · media 4 sem. (línea base)", common.pct(s["WAPE_referencia"]), "método sin IA", delta_color="off", delta_arrow="off")
    c.metric("Sesgo agregado (TSB)", common.pct(s["sesgo_tsb"]), "dentro de ±10 %" if abs(s["sesgo_tsb"]) <= 10 else "fuera de ±10 %",
             delta_color="off" if abs(s["sesgo_tsb"]) <= 10 else "inverse", delta_arrow="off")
    d.metric("Productos mejores que la referencia", common.pct(s["productos_mejores_pct"], 1), "meta ≥ 55 %", delta_color="off", delta_arrow="off")

    st.caption("**Cómo leer el WAPE:** son las unidades de error divididas por las unidades vendidas; no es el porcentaje de "
               "predicciones erradas ni una probabilidad de acierto. Menor es mejor. El sesgo mide el error del total acumulado.")

    left, right = st.columns([1, 1])
    with left:
        st.markdown("**WAPE por bloque de 8 semanas**")
        long = pd.melt(folds, id_vars=["bloque"], value_vars=["WAPE_referencia", "WAPE_tsb"], var_name="Método", value_name="WAPE")
        long["Método"] = long["Método"].map({"WAPE_referencia": "Media 4 sem.", "WAPE_tsb": "TSB"})
        chart = alt.Chart(long).mark_bar().encode(
            x=alt.X("bloque:O", title="Bloque"), y=alt.Y("WAPE:Q", title="WAPE (%)"), xOffset="Método:N",
            color=alt.Color("Método:N", scale=alt.Scale(domain=["Media 4 sem.", "TSB"], range=["#9aa8c0", "#0e9f8e"]),
                            legend=alt.Legend(orient="bottom")), tooltip=["Método", "bloque", alt.Tooltip("WAPE:Q", format=".2f")])
        st.altair_chart(chart.properties(height=300), width="stretch")
        wins = int((folds["WAPE_tsb"] < folds["WAPE_referencia"]).sum())
        st.caption(f"TSB supera a la referencia en {wins} de {len(folds)} bloques. Cohorte: {common.num(s['cohorte'])} artículos con "
                   f"≥ 20 semanas de venta antes del primer bloque; {common.num(s['productos_evaluados'])} con ventas en el período evaluado.")
    with right:
        st.markdown("**Metas de la solución**")
        goals = pd.DataFrame([
            ["WAPE menor que la referencia", "Sí", "Cumplida" if s["WAPE_tsb"] < s["WAPE_referencia"] else "No cumplida"],
            ["Sesgo entre −10 % y +10 %", "Sí", "Cumplida" if abs(s["sesgo_tsb"]) <= 10 else "No cumplida"],
            ["Productos mejores que la referencia", "≥ 55 %", f"{common.pct(s['productos_mejores_pct'], 1)} · " +
             ("cumplida" if s["productos_mejores_pct"] >= 55 else "no cumplida")],
            ["Mejora del WAPE en piloto con datos reales", "≥ 5 %", "Por validar"],
        ], columns=["Indicador", "Meta", "Estado"])
        st.dataframe(goals, hide_index=True, width="stretch")
        st.info(f"**Lectura honesta:** la mejora es modesta (≈{common.num(s['mejora_relativa_pct'], 1)} %) y el error absoluto "
                "sigue alto. La meta de 5 % se evaluará con datos reales de un cliente.")

    st.markdown("**Pronósticos guardados frente a la venta real**")
    evaluated = pipeline.evaluate_runs(common.conn(), ds)
    if evaluated.empty:
        st.caption("Aún no hay ejecuciones evaluables. Cuando cargue datos que incluyan la semana ya cerrada que pronosticó una "
                   "ejecución anterior, aquí aparecerá su error real frente a la referencia.")
    else:
        st.dataframe(evaluated.rename(columns={"ejecucion": "Ejecución", "semana_objetivo": "Semana objetivo", "articulos": "Artículos",
                                               "unidades_reales": "Unidades reales", "WAPE_tsb": "WAPE TSB (%)",
                                               "WAPE_referencia": "WAPE media 4 sem. (%)", "sesgo_tsb": "Sesgo TSB (%)"}).round(2),
                     hide_index=True, width="stretch")

    st.markdown("**Por patrón de demanda** (recalculado en cada origen)")
    seg = analysis.backtest["segments"].rename(columns={"segmento": "Patrón", "unidades": "Unidades reales",
                                                       "WAPE_tsb": "WAPE TSB (%)", "WAPE_referencia": "WAPE media 4 sem. (%)"})
    st.dataframe(seg, hide_index=True, width="stretch",
                 column_config={"Unidades reales": st.column_config.NumberColumn(format="%d"),
                                "WAPE TSB (%)": st.column_config.NumberColumn(format="%.2f"),
                                "WAPE media 4 sem. (%)": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Backtesting sobre el historial cargado: pronóstico de un paso adelante en modo rodante; α elegido solo con las "
               "8 semanas previas a cada bloque.")
    common.ia_box("pronósticos y ventas reales de semanas ya cerradas (backtesting del historial y, cuando existen, ejecuciones guardadas).",
                  "WAPE, sesgo y % de productos mejores que la referencia, por bloque y por patrón.")
