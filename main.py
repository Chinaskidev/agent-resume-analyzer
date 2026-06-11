import os
import uvicorn
import PyPDF2
import docx2txt
import re
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Analisis, Funcion, Perfil, SessionLocal, Cliente, Trabajo, Habilidad
from langdetect import detect, DetectorFactory, LangDetectException

DetectorFactory.seed = 0  # langdetect es no-determinista sin seed fija

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

# Modelo NLP para similitud semántica.
modelo_semantico = SentenceTransformer("all-MiniLM-L6-v2")


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



# Función para extraer texto de un archivo PDF o DOCX
def extraer_texto(archivo: UploadFile) -> str:
    texto = ""
    if archivo.filename.endswith(".pdf"):
        lector_pdf = PyPDF2.PdfReader(archivo.file)
        texto = " ".join(pagina.extract_text() for pagina in lector_pdf.pages if pagina.extract_text())
    elif archivo.filename.endswith(".docx"):
        texto = docx2txt.process(archivo.file)
    return texto.lower()  # Convertir todo a minúsculas para evitar errores de coincidencia




# Función para extraer experiencia en años usando expresiones regulares
def extraer_experiencia(texto: str) -> list:
    experiencia = re.findall(r"(\d+)\s*(?:años|years)", texto)
    return experiencia if experiencia else []

# Detecta el idioma del CV para responder en el mismo idioma
def detectar_idioma(texto: str) -> str:
    texto_limpio = texto.replace("\n", " ").strip()
    if not texto_limpio:
        return "es"
    try:
        return detect(texto_limpio)
    except LangDetectException:
        return "es"

# Función para calcular la similitud semántica entre el CV y la descripción del trabajo
def similitud_semantica(texto_cv: str, funciones_del_trabajo: str) -> float:
    embeddings = modelo_semantico.encode([texto_cv, funciones_del_trabajo], convert_to_tensor=True)
    score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    return round(score, 2)

# Generar un feedback detallado usando el LLM (Ministral via Ollama)
def generar_feedback(texto_cv: str, nombre_del_cliente: str, funciones_del_trabajo: str, perfil_del_trabajador: str) -> str:

    idioma_cv = detectar_idioma(texto_cv)
    idioma_respuesta = "English" if idioma_cv == "en" else "Spanish"

    prompt = f"""
Los siguientes datos provienen de la base de datos interna del cliente.

## Cliente
{nombre_del_cliente}

## Perfil requerido (base de datos)
{perfil_del_trabajador}

## Funciones del puesto (base de datos)
{funciones_del_trabajo}

## Currículum del candidato
{texto_cv}

## Tareas
1. Identificar fortalezas relevantes para el puesto.
2. Identificar debilidades o brechas frente al perfil requerido.
3. Evaluar el nivel de cumplimiento del perfil (Alto / Medio / Bajo).
4. Emitir una recomendación final clara y profesional.

## Formato obligatorio
- **Fortalezas**
- **Debilidades**
- **Nivel de cumplimiento**
- **Recomendación final**
"""

    prompt_de_sistema = f"""Eres un motor profesional de análisis de currículums usado en procesos de selección.
MANDATORY: Responde solo en {idioma_respuesta}. No uses otro idioma.
Reglas:
- No inventes información.
- No asumas experiencia no presente en el CV.
- No recalcules puntuaciones numéricas.
- Limítate a analizar y justificar los datos proporcionados."""

    respuesta = cliente_llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": prompt_de_sistema},
                  {"role": "user", "content": prompt}]
    )
    return respuesta.choices[0].message.content


# Calibra el coseno (0-1) a una escala 0-10.
# En la practica MiniLM da cosenos entre ~0.20 (sin relacion) y ~0.75 (match muy fuerte):
# ese rango real se mapea linealmente a 0-10, sin saltos.
def puntuacion(match_score: float):
    PISO, TECHO = 0.20, 0.75
    normalizado = (match_score - PISO) / (TECHO - PISO)
    score = max(0.0, min(1.0, normalizado)) * 10

    if score >= 8.0:
        decision = "Alto"
    elif score >= 7.0:
        decision = "Promedio Alto"
    elif score >= 6.0:
        decision = "Promedio Bajo"
    elif score >= 4.0:
        decision = "Bajo"
    else:
        decision = "Deficiente"

    return round(score, 2), decision


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

    # Obtener funciones del trabajo (via relacion, evita errores si no hay datos)
    funciones_del_trabajo = ", ".join([f.titulo for f in trabajo.funciones]) if trabajo.funciones else "No especificado"

    # Obtener perfil del trabajador
    perfil_del_trabajador = ", ".join([p.nombre for p in trabajo.perfil]) if trabajo.perfil else "No especificado"

    # Extraer texto del CV
    texto_cv = extraer_texto(archivo)

    feedback = generar_feedback(texto_cv, cliente.nombre, funciones_del_trabajo, perfil_del_trabajador)

    match_score = similitud_semantica(texto_cv, funciones_del_trabajo)

    puntuacion_calibrada, decision = puntuacion(match_score)

    # Guardar el analisis en el historial
    nuevo_analisis = Analisis(
        nombre_del_candidato=nombre_del_candidato,
        archivo=archivo.filename,
        titulo_trabajo=trabajo.titulo,
        match_score=puntuacion_calibrada,
        raw_score=match_score,
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
        "match_score": puntuacion_calibrada,
        "decision": decision,
        "feedback": nuevo_analisis.feedback,
        "creado_en": nuevo_analisis.creado_en
        }


# Endpoint para listar el historial de analisis
@app.get("/analisis/")
async def listar_analisis(db: Session = Depends(obtener_db)):
    analisis = db.query(Analisis).order_by(Analisis.creado_en.desc()).all()
    return [{
        "id": a.id,
        "nombre_del_candidato": a.nombre_del_candidato,
        "archivo": a.archivo,
        "titulo_trabajo": a.titulo_trabajo,
        "match_score": a.match_score,
        "decision": a.decision,
        "creado_en": a.creado_en
    } for a in analisis]


# Verificación de que FastAPI está funcionando en producción
@app.get("/")
def raiz():
    return {"message": "🚀 FastAPI funcionando correctamente en Railway!"}

# Configuración para producción
if __name__ == "__main__":
    puerto = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=puerto)
