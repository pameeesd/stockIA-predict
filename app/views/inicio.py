"""Pantalla 1 · Inicio / acceso."""
import streamlit as st

import common


def _enter_demo() -> None:
    st.session_state.setdefault("user", "Invitada/o")
    common.set_dataset(common.demo_dataset())
    common.run_analysis(note="demostración")


def render() -> None:
    st.title("📈 StockIA Predict")
    st.subheader("Pronóstico semanal de ventas por producto y alertas de volumen inusual")
    st.write("Cargue su historial de ventas y obtenga, para cada artículo, su patrón de demanda, un pronóstico para la "
             "semana siguiente y los pedidos que se salen de lo normal.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Qué hace**  \nPronostica ventas observadas, clasifica la demanda de cada producto y señala "
                    "pedidos extraordinarios para revisión humana. Ofrece una cobertura de stock informativa.")
    with c2:
        st.markdown("**Qué no hace**  \nNo conoce su inventario real, no genera órdenes de compra ni predice quiebres. "
                    "La decisión es suya.")

    st.divider()
    if "user" not in st.session_state:
        left, right = st.columns(2)
        with left:
            with st.form("acceso"):
                st.markdown("#### Ingresar")
                name = st.text_input("Nombre", placeholder="Su nombre")
                st.caption("Acceso simulado: esta prueba de concepto no tiene cuentas ni contraseñas y los datos "
                           "no salen de este equipo.")
                if st.form_submit_button("Entrar", type="primary"):
                    if name.strip():
                        st.session_state["user"] = name.strip()
                        st.rerun()
                    else:
                        st.warning("Escriba un nombre para continuar.")
        with right:
            st.markdown("#### O pruebe sin cargar nada")
            st.write("Datos reales de un comercio electrónico británico anonimizado (Reino Unido, 2009–2011).")
            if st.button("Probar con datos de demostración (UCI Online Retail II)", width="stretch"):
                with st.spinner("Preparando datos y calculando pronósticos…"):
                    _enter_demo()
                st.rerun()
    else:
        st.success(f"Sesión iniciada como **{st.session_state['user']}**.")
        if "analysis" not in st.session_state:
            st.write("Siguiente paso: cargue su archivo en **Datos** o use los datos de demostración.")
            if st.button("Usar datos de demostración (UCI Online Retail II)", type="primary"):
                with st.spinner("Preparando datos y calculando pronósticos…"):
                    _enter_demo()
                st.rerun()
        else:
            ds, analysis, run_id = st.session_state["ds"], st.session_state["analysis"], st.session_state["run_id"]
            m = analysis.meta
            a, b, c = st.columns(3)
            a.metric("Artículos pronosticados", common.num(m["items"]))
            b.metric("Semana pronosticada", m["next_week"])
            c.metric("Ejecución", f"#{run_id}")
            st.write("Continúe en **Pronósticos** para ver el resultado por producto, o en **Revisión** para los "
                     "pedidos de volumen inusual.")
        if st.button("Cerrar sesión"):
            for key in ("user", "ds", "analysis", "run_id"):
                st.session_state.pop(key, None)
            st.rerun()

    st.caption("Fuente de los datos de demostración: Chen, D. (2012), Online Retail II, UCI Machine Learning Repository, "
               "DOI 10.24432/C5CG6D, licencia CC BY 4.0. No se muestran identificadores de clientes.")
    st.caption(common.DISCLAIMER)
