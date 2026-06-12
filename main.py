from datetime import date
import os
from sqlalchemy import func
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Analisis, Funcion, Perfil, SessionLocal, Cliente, Trabajo, Habilidad
from prompts import PROMPT_SISTEMA, PLANTILLA_ANALISIS
from reporte import generar_pdf_analisis
from motor import (
    calcular_match_score,
    calibrar_puntuacion,
    combinar_puntuaciones,
    decidir,
    detectar_idioma,
    detectar_inyeccion,
    extraer_puntuacion_llm,
    extraer_texto,
    quitar_linea_puntuacion,
)

# Cargar variables de entorno
load_dotenv(override=True)

# Configuracion del LLM-va ser compatible igual con OPENAI
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1") #ollama
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama") #ollama lo ignora pero el SDK exige un valor
LLM_MODEL = os.getenv("LLM_MODEL", "ministral-3:8b") #MODELO Ministral

cliente_llm = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


app = FastAPI()

# Conexion con la base de datos.
def obtener_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


FRONTEND_URL = os.getenv("FRONTEND_URL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://frontend-resume-analyzer.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Generar un feedback detallado usando el LLM (Ministral via Ollama).
# Las plantillas viven en prompts.py: una completa por idioma, porque un modelo 8B
# sigue el idioma dominante del prompt aunque se le pida responder en otro.
def generar_feedback(texto_cv: str, nombre_del_cliente: str, funciones_del_trabajo: str, habilidades: str, perfil_del_trabajador: str, idioma: str) -> str:

    prompt = PLANTILLA_ANALISIS[idioma].format(
        nombre_del_cliente=nombre_del_cliente,
        perfil_del_trabajador=perfil_del_trabajador,
        habilidades=habilidades,
        funciones_del_trabajo=funciones_del_trabajo,
        texto_cv=texto_cv,
    )

    respuesta = cliente_llm.chat.completions.create(
        model=LLM_MODEL,
        temperature=0.2,  # baja para que la PUNTUACION del LLM sea estable entre corridas
        messages=[{"role": "system", "content": PROMPT_SISTEMA[idioma]},
                  {"role": "user", "content": prompt}]
    )
    return respuesta.choices[0].message.content


#Endpoint para **añadir trabajos y habilidades**
@app.post("/agregar_trabajo/")
async def agregar_trabajo(
    nombre_del_cliente: str = Form(...),
    titulo_de_trabajo: str = Form(...),
    perfil_del_trabajador: str = Form(...),
    funciones_del_trabajo: str = Form(...),
    habilidades: str = Form(...),
    db: Session = Depends(obtener_db)
):

    print("📩 Recibiendo solicitud con los siguientes datos:")
    print(f"Cliente: {nombre_del_cliente}")
    print(f"Trabajo: {titulo_de_trabajo}")
    print(f"Perfil: {perfil_del_trabajador}")
    print(f"Funciones: {funciones_del_trabajo}")
    print(f"Habilidades: {habilidades}")

    #Buscar si el cliente ya existe
    cliente = db.query(Cliente).filter(Cliente.nombre == nombre_del_cliente).first()
    if not cliente:
        cliente = Cliente(nombre=nombre_del_cliente)
        db.add(cliente)
        db.flush()
        db.commit()
        db.refresh(cliente)

    #Crear un nuevo trabajo
    trabajo = Trabajo(titulo=titulo_de_trabajo, cliente_id=cliente.id)
    db.add(trabajo)
    db.flush()
    db.commit()
    db.refresh(trabajo)

    # Guardar habilidades en la base de datos
    for habilidad in habilidades.split(","):
        db.add(Habilidad(nombre=habilidad.strip(), trabajo_id=trabajo.id))

    # Guardar perfil en la base de datos
    db.add(Perfil(nombre=perfil_del_trabajador.strip(), trabajo_id=trabajo.id))

    # Guardar funciones del trabajo en la base de datos
    for funcion in funciones_del_trabajo.split(","):
        db.add(Funcion(titulo=funcion.strip(), trabajo_id=trabajo.id))

    db.flush()
    db.commit()
    return {"message": "Trabajo, habilidades, perfil y funciones registradas exitosamente"}

# Endpoint para obtener clientes
@app.get("/clientes/")
async def obtener_clientes(db: Session = Depends(obtener_db)):
    # anterior mente se me duplicaban los clientes en el frontend
    #ahora uso distint() para que no se dupliquen
    nombres_de_clientes = db.query(Cliente.nombre).distinct().all()
    return [{"nombre": c[0]} for c in nombres_de_clientes]


# Endpoint para **obtener trabajos por cliente**
@app.get("/obtener_trabajos_por_cliente/{nombre_del_cliente}")
async def obtener_trabajos_por_cliente(nombre_del_cliente: str, db: Session = Depends(obtener_db)):
    cliente = db.query(Cliente).filter(Cliente.nombre == nombre_del_cliente).first()
    if not cliente:
        return {"error": "Cliente no encontrado"}

    trabajos = db.query(Trabajo).filter(Trabajo.cliente_id == cliente.id).all()
    return [{"id": trabajo.id, "titulo": trabajo.titulo} for trabajo in trabajos]


#Analizar un CV y obtener políticas del cliente
@app.post("/analizar/")
async def analizar_cv(
    archivo: UploadFile = File(...),
    titulo_de_trabajo: str = Form(...),
    nombre_del_cliente: str = Form(...),
    nombre_del_candidato: str = Form(None),
    db: Session = Depends(obtener_db)
):
    # Obtener el cliente
    cliente = db.query(Cliente).filter(Cliente.nombre == nombre_del_cliente).first()
    if not cliente:
        return {"error": "Cliente no encontrado"}

    # Obtener el trabajo desde la base de datos
    trabajo = db.query(Trabajo).filter(Trabajo.titulo == titulo_de_trabajo, Trabajo.cliente_id == cliente.id).first()
    if not trabajo:
        return {"error": "Trabajo no encontrado"}

    # Obtener funciones, habilidades y perfil del trabajo (via relaciones)
    funciones_del_trabajo = ", ".join([f.titulo for f in trabajo.funciones]) if trabajo.funciones else "No especificado"
    habilidades = ", ".join([h.nombre for h in trabajo.habilidades]) if trabajo.habilidades else "No especificado"
    perfil_del_trabajador = ", ".join([p.nombre for p in trabajo.perfil]) if trabajo.perfil else "No especificado"

    # Extraer texto del CV, detectar su idioma (es/en) e intentos de inyeccion
    texto_cv = extraer_texto(archivo)
    idioma = "en" if detectar_idioma(texto_cv) == "en" else "es"
    alerta_inyeccion = detectar_inyeccion(texto_cv)

    feedback = generar_feedback(texto_cv, cliente.nombre, funciones_del_trabajo, habilidades, perfil_del_trabajador, idioma)

    match_score = calcular_match_score(texto_cv, funciones_del_trabajo, habilidades, perfil_del_trabajador)

    # Puntaje hibrido: semantico (rubro correcto) + LLM (calificacion real).
    # Con alerta de inyeccion el numero del LLM no es confiable: cae al semantico.
    puntaje_semantico = calibrar_puntuacion(match_score)
    puntaje_llm = None if alerta_inyeccion else extraer_puntuacion_llm(feedback)
    # Recien despues de parsear la nota se limpia la linea "SCORE: X/10":
    # es un dato interno y confunde en el informe que lee el cliente
    feedback = quitar_linea_puntuacion(feedback)
    puntuacion_final = combinar_puntuaciones(puntaje_semantico, puntaje_llm)
    decision = decidir(puntuacion_final)

    # Guardar el analisis en el historial
    nuevo_analisis = Analisis(
        nombre_del_candidato=nombre_del_candidato,
        archivo=archivo.filename,
        titulo_trabajo=trabajo.titulo,
        match_score=puntuacion_final,
        raw_score=match_score,
        puntaje_llm=puntaje_llm,
        alerta_inyeccion=alerta_inyeccion,
        decision=decision,
        feedback=feedback if feedback is not None else "No se pudo generar feedback",
        trabajo_id=trabajo.id
    )
    db.add(nuevo_analisis)
    db.commit()
    db.refresh(nuevo_analisis)

    return {
        "id": nuevo_analisis.id,
        "archivo": archivo.filename,
        "titulo_trabajo": trabajo.titulo,
        "nombre_del_candidato": nombre_del_candidato,
        "idioma": idioma,
        "match_score": puntuacion_final,
        "puntaje_semantico": puntaje_semantico,
        "puntaje_llm": puntaje_llm,
        "alerta_inyeccion": alerta_inyeccion,
        "decision": decision,
        "feedback": nuevo_analisis.feedback,
        "creado_en": nuevo_analisis.creado_en
        }


# Endpoint para listar el historial de analisis con filtros opcionales
@app.get("/analisis/")
async def listar_analisis(
    cliente: str | None = None,
    candidato: str | None = None,
    puesto: str | None = None,
    decision: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(obtener_db)
):
    consulta = db.query(Analisis).join(Trabajo).join(Cliente)
    if cliente:
        consulta = consulta.filter(Cliente.nombre == cliente)
    if candidato:
        consulta = consulta.filter(Analisis.nombre_del_candidato.ilike(f"%{candidato}%"))
    if puesto:
        consulta = consulta.filter(Analisis.titulo_trabajo.ilike(f"%{puesto}%"))
    if decision:
        consulta = consulta.filter(Analisis.decision == decision)
    if desde:
        consulta = consulta.filter(func.date(Analisis.creado_en) >= desde)
    if hasta:
        consulta = consulta.filter(func.date(Analisis.creado_en) <= hasta)
    analisis = consulta.order_by(Analisis.creado_en.desc()).all()
    return[{
        "id": a.id,
        "cliente": a.trabajo.cliente.nombre,
        "nombre_del_candidato": a.nombre_del_candidato,
        "archivo": a.archivo,
        "titulo_trabajo": a.titulo_trabajo,
        "match_score": a.match_score,
        "decision": a.decision,
        "alerta_inyeccion": a.alerta_inyeccion,
        "creado_en": a.creado_en
    } for a in analisis]

# Endpoint para descargar el informe PDF de un analisis
@app.get("/analisis/{analisis_id}/pdf")
async def descargar_pdf_analisis(analisis_id: int, db: Session = Depends(obtener_db)):
    analisis = db.query(Analisis).filter(Analisis.id == analisis_id).first()
    if not analisis:
        return {"error": "Análisis no encontrado"}

    nombre_cliente = analisis.trabajo.cliente.nombre if analisis.trabajo and analisis.trabajo.cliente else ""
    pdf_bytes = generar_pdf_analisis(analisis, nombre_cliente)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ixtli_analisis_{analisis.id}.pdf"'},
    )


# Verificación de que FastAPI está funcionando en producción
@app.get("/")
def raiz():
    return {"message": "🚀 FastAPI funcionando correctamente en Railway!"}

# Configuración para producción
if __name__ == "__main__":
    puerto = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=puerto)
