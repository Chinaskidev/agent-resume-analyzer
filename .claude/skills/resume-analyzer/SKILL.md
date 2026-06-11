---
name: resume-analyzer
description: Guía del motor de análisis de CVs de Ixtli. Usar cuando se trabaje en el endpoint /analizar/, el match score semántico, el feedback con LLM (Ministral/Ollama u OpenAI), la extracción de texto de PDF/DOCX, o al correr/desplegar este backend FastAPI. Use when working on resume analysis, semantic matching, LLM feedback, or running this FastAPI backend.
---

# Motor de análisis de CVs (Ixtli)

## Flujo del análisis

`POST /analizar/` (multipart form: `archivo`, `titulo_de_trabajo`, `nombre_del_cliente`, `nombre_del_candidato` opcional) ejecuta este pipeline en `main.py`:

1. **Lookup en DB**: busca `Cliente` por nombre y `Trabajo` por título + cliente. Si no existen devuelve `{"error": ...}` con HTTP 200 (ojo: no usa códigos de error HTTP).
2. **Contexto del puesto**: concatena `trabajo.funciones` y `trabajo.perfil` en strings separados por coma ("No especificado" si están vacíos).
3. **`extraer_texto(archivo)`**: PyPDF2 para `.pdf`, docx2txt para `.docx`. Devuelve el texto en minúsculas. Cualquier otra extensión devuelve string vacío sin error.
4. **`generar_feedback(...)`**: detecta el idioma del CV con langdetect (`detectar_idioma`) y llama al LLM con un prompt que pide fortalezas/debilidades, nivel de cumplimiento y recomendación final. Responde en inglés solo si el CV está en inglés; español para todo lo demás.
5. **`similitud_semantica(...)`**: similitud coseno entre embeddings del CV y de las funciones del trabajo con `all-MiniLM-L6-v2` (carga global al iniciar, ~80MB de descarga la primera vez).
6. **`puntuacion(match_score)`**: calibra el coseno a escala 0–10 con mapeo lineal del rango real de MiniLM [0.20, 0.75]. Decisión: ≥8 "Alto", ≥7 "Promedio Alto", ≥6 "Promedio Bajo", ≥4 "Bajo", si no "Deficiente".
7. **Persistencia**: guarda el análisis en la tabla `analisis` (incluido `raw_score`, el coseno original, para recalibrar PISO/TECHO con datos reales).

Respuesta: `{id, archivo, titulo_trabajo, nombre_del_candidato, match_score (0-10), decision, feedback, creado_en}`.

`GET /analisis/` lista el historial (sin el campo `feedback`, que contiene datos del CV).

## Correr el proyecto

```bash
pip install -r requirements.txt
uvicorn main:app --reload   # desarrollo
python main.py              # como en producción (puerto $PORT o 8000)
```

Requiere `.env` con `DATABASE_URL` (PostgreSQL) — **el import de `database.py` falla al arrancar si falta**. Para probar sin Postgres real: `DATABASE_URL=sqlite:///./test.db` funciona con SQLAlchemy para desarrollo local. Migraciones: `alembic upgrade head` (Alembic lee `DATABASE_URL` vía `alembic/env.py`).

Probar el análisis sin frontend:

```bash
curl -X POST http://localhost:8000/analizar/ \
  -F "archivo=@cv.pdf" \
  -F "titulo_de_trabajo=Backend Developer" \
  -F "nombre_del_cliente=Acme" \
  -F "nombre_del_candidato=Juan Pérez"
```

El cliente y el trabajo deben existir antes (crearlos con `POST /agregar_trabajo/`).

## Cambiar el LLM (modelo local ↔ OpenAI)

El feedback usa el SDK de OpenAI contra un servidor compatible; se configura por variables de entorno (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` en `main.py`):

```bash
# Local con Ollama (Ministral 3 8B, licencia Apache 2.0) — default actual
LLM_BASE_URL=http://localhost:11434/v1  LLM_API_KEY=ollama  LLM_MODEL=ministral-3:8b

# OpenAI
LLM_BASE_URL=https://api.openai.com/v1  LLM_API_KEY=sk-...  LLM_MODEL=gpt-4o-mini
```

Criterio: OpenAI para arrancar barato (~$0.001/CV); modelo local cuando el argumento de venta es privacidad (los CVs no salen de la infraestructura) o el volumen justifica un GPU.

## Modelo de datos

Tablas y modelos en español, definidos en `database.py`, migraciones con Alembic:

- `clientes` (`Cliente.nombre` es unique) → `tipos_de_trabajo` (`Trabajo`)
- `Trabajo` → `habilidades` (`Habilidad`), `funciones_del_trabajo` (`Funcion`), `perfil_del_trabajador` (`Perfil`), `analisis` (`Analisis`), todo cascade delete.
- `analisis` guarda el historial: candidato, archivo, `match_score` calibrado (0–10), `raw_score` (coseno 0–1), decisión, feedback y `creado_en`.

`POST /agregar_trabajo/` recibe habilidades y funciones como strings separados por coma y los divide con `split(",")`.

## Trampas conocidas

- Los errores de negocio se devuelven como `{"error": ...}` con HTTP 200; el frontend depende de esto, no lo cambies sin coordinar.
- `match_score` compara contra las **funciones** del trabajo, no contra habilidades ni perfil. Los límites de calibración PISO=0.20/TECHO=0.75 en `puntuacion()` se eligieron a ojo — recalibrar con la distribución de `raw_score` cuando haya análisis reales acumulados.
- CORS permite solo `localhost:3000` y `frontend-resume-analyzer.vercel.app`; si el frontend cambia de dominio hay que tocar `main.py`. El frontend viejo espera la API en inglés (`/analyze/`, `match_score` 0–1) — quedó incompatible desde el issue-6; se va a crear una interfaz nueva.
- Los CVs son datos personales: no loguear `texto_cv` ni guardarlo sin necesidad (el feedback guardado en `analisis` ya contiene extractos del CV — no exponerlo en listados públicos).
- Nunca imprimir API keys al arrancar (el repo original lo hacía).
