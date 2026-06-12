import os
import requests
import streamlit as st

# URL del backend FastAPI (en Railway sera otra)
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Ixtli - Analizador de CVs", page_icon="📄", layout="wide")

st.sidebar.title("📄 Ixtli")
vista = st.sidebar.radio("Menú", ["Analizar CV", "Agregar puesto", "Buscar análisis", "Reporte por puesto"])


if vista == "Analizar CV":
    st.title("Analizar CV")

    clientes = requests.get(f"{API_URL}/clientes/", timeout=10).json()
    nombres = [c["nombre"] for c in clientes]
    if not nombres:
        st.warning("No hay clientes todavía. Crea un puesto primero en 'Agregar puesto'.")
        st.stop()

    nombre_del_cliente = st.selectbox("Cliente", nombres)

    trabajos = requests.get(f"{API_URL}/obtener_trabajos_por_cliente/{nombre_del_cliente}", timeout=10).json()
    if not isinstance(trabajos, list) or not trabajos:
        st.warning("Este cliente no tiene puestos registrados.")
        st.stop()

    titulo_de_trabajo = st.selectbox("Puesto", [t["titulo"] for t in trabajos])
    nombre_del_candidato = st.text_input("Nombre del candidato (opcional)")
    archivo = st.file_uploader("CV del candidato", type=["pdf", "docx"])

    if st.button("Analizar", type="primary", disabled=archivo is None):
        with st.spinner("Analizando CV... el LLM puede tardar un rato"):
            r = requests.post(
                f"{API_URL}/analizar/",
                data={
                    "titulo_de_trabajo": titulo_de_trabajo,
                    "nombre_del_cliente": nombre_del_cliente,
                    "nombre_del_candidato": nombre_del_candidato,
                },
                files={"archivo": (archivo.name, archivo.getvalue())},
                timeout=600,
            )
        st.session_state["resultado"] = r.json()

    # el resultado se muestra fuera del if del boton: el clic en download_button
    # re-ejecuta el script y sin session_state desapareceria de la pantalla
    if "resultado" in st.session_state:
        resultado = st.session_state["resultado"]

        # la API devuelve errores de negocio con HTTP 200 y {"error": ...}
        if "error" in resultado:
            st.error(resultado["error"])
        else:
            if resultado.get("alerta_inyeccion"):
                st.warning("⚠️ Este CV contiene texto que intenta manipular el análisis "
                           "(posible texto invisible en el PDF). El puntaje del LLM fue "
                           "descartado y se usó solo el match semántico. Revisar manualmente.")
            col1, col2, col3 = st.columns(3)
            col1.metric("Match score", f"{resultado['match_score']}/10")
            col2.metric("Decisión", resultado["decision"])
            col3.metric("Idioma del CV", resultado["idioma"].upper())
            st.markdown("### Feedback del agente")
            st.markdown(resultado["feedback"])

            pdf = requests.get(f"{API_URL}/analisis/{resultado['id']}/pdf", timeout=30)
            st.download_button(
                "📄 Descargar informe PDF",
                data=pdf.content,
                file_name=f"ixtli_analisis_{resultado['id']}.pdf",
                mime="application/pdf",
            )


elif vista == "Agregar puesto":
    st.title("Agregar puesto")

    with st.form("form_puesto"):
        nombre_del_cliente = st.text_input("Nombre del cliente")
        titulo_de_trabajo = st.text_input("Título del puesto")
        perfil_del_trabajador = st.text_input("Perfil del trabajador")
        funciones_del_trabajo = st.text_area("Funciones del puesto (separadas por coma)")
        habilidades = st.text_area("Habilidades (separadas por coma)")
        enviar = st.form_submit_button("Guardar puesto")

    if enviar:
        if not all([nombre_del_cliente, titulo_de_trabajo, perfil_del_trabajador, funciones_del_trabajo, habilidades]):
            st.error("Todos los campos son obligatorios.")
        else:
            r = requests.post(f"{API_URL}/agregar_trabajo/", data={
                "nombre_del_cliente": nombre_del_cliente,
                "titulo_de_trabajo": titulo_de_trabajo,
                "perfil_del_trabajador": perfil_del_trabajador,
                "funciones_del_trabajo": funciones_del_trabajo,
                "habilidades": habilidades,
            }, timeout=10)
            st.success(r.json()["message"])


elif vista == "Buscar análisis":
    st.title("Buscar análisis")

    clientes = requests.get(f"{API_URL}/clientes/", timeout=10).json()
    col1, col2, col3 = st.columns(3)
    cliente = col1.selectbox("Cliente", ["Todos"] + [c["nombre"] for c in clientes])
    candidato = col2.text_input("Candidato")
    puesto = col3.text_input("Puesto")

    col4, col5 = st.columns(2)
    decision = col4.selectbox(
        "Decisión", ["Todas", "Alto", "Promedio Alto", "Promedio Bajo", "Bajo", "Deficiente"]
    )
    fechas = col5.date_input("Rango de fechas", value=())

    params = {}
    if cliente != "Todos":
        params["cliente"] = cliente
    if candidato:
        params["candidato"] = candidato
    if puesto:
        params["puesto"] = puesto
    if decision != "Todas":
        params["decision"] = decision
    # mientras el usuario elige el rango, date_input devuelve una sola fecha
    if len(fechas) == 2:
        params["desde"] = fechas[0].isoformat()
        params["hasta"] = fechas[1].isoformat()

    analisis = requests.get(f"{API_URL}/analisis/", params=params, timeout=10).json()
    if not analisis:
        st.info("No hay análisis que coincidan con los filtros.")
    else:
        st.dataframe(analisis, use_container_width=True)

        opciones = {
            f"#{a['id']} - {a['nombre_del_candidato'] or a['archivo']} ({a['cliente']} / {a['titulo_trabajo']})": a["id"]
            for a in analisis
        }
        seleccion = st.selectbox("Descargar informe de:", list(opciones.keys()))
        pdf = requests.get(f"{API_URL}/analisis/{opciones[seleccion]}/pdf", timeout=30)
        st.download_button(
            "📄 Descargar PDF",
            data=pdf.content,
            file_name=f"ixtli_analisis_{opciones[seleccion]}.pdf",
            mime="application/pdf",
        )


elif vista == "Reporte por puesto":
    st.title("Reporte comparativo de candidatos")

    clientes = requests.get(f"{API_URL}/clientes/", timeout=10).json()
    nombres = [c["nombre"] for c in clientes]
    if not nombres:
        st.warning("No hay clientes todavía. Crea un puesto primero en 'Agregar puesto'.")
        st.stop()

    nombre_del_cliente = st.selectbox("Cliente", nombres)

    trabajos = requests.get(f"{API_URL}/obtener_trabajos_por_cliente/{nombre_del_cliente}", timeout=10).json()
    if not isinstance(trabajos, list) or not trabajos:
        st.warning("Este cliente no tiene puestos registrados.")
        st.stop()

    puestos = {t["titulo"]: t["id"] for t in trabajos}
    titulo = st.selectbox("Puesto", list(puestos.keys()))

    # idioma del cliente que recibe el reporte (no el de los CVs)
    idiomas = {"Español": "es", "English": "en"}
    idioma = idiomas[st.selectbox("Idioma del reporte", list(idiomas.keys()))]

    if st.button("Generar reporte", type="primary"):
        with st.spinner("Redactando el reporte... el LLM puede tardar un rato"):
            r = requests.get(
                f"{API_URL}/reporte_comparativo/{puestos[titulo]}",
                params={"idioma": idioma},
                timeout=600,
            )
        st.session_state["reporte"] = r.json()
        st.session_state["reporte_trabajo_id"] = puestos[titulo]

    # mismo truco que en Analizar CV: sin session_state el clic en el
    # download_button re-ejecuta el script y el reporte desapareceria
    if "reporte" in st.session_state:
        reporte = st.session_state["reporte"]
        if "error" in reporte:
            st.error(reporte["error"])
        else:
            st.subheader(f"{reporte['puesto']} — {reporte['cliente']}")
            st.dataframe(reporte["candidatos"], use_container_width=True)
            st.markdown("### Informe del agente")
            st.markdown(reporte["informe"])

            pdf = requests.post(
                f"{API_URL}/reporte_comparativo/pdf",
                data={
                    "trabajo_id": st.session_state["reporte_trabajo_id"],
                    "informe": reporte["informe"],
                    "idioma": reporte.get("idioma", "es"),
                },
                timeout=30,
            )
            st.download_button(
                "📄 Descargar reporte PDF",
                data=pdf.content,
                file_name=f"ixtli_reporte_{st.session_state['reporte_trabajo_id']}.pdf",
                mime="application/pdf",
            )
