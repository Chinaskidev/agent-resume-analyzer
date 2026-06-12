---
name: resume-analyzer
description: Guía del motor de análisis de CVs de Ixtli. Usar cuando se trabaje en el endpoint /analizar/, el match score semántico, el feedback con LLM (Ministral/Ollama u OpenAI), la extracción de texto de PDF/DOCX, o al correr/desplegar este backend FastAPI. Use when working on resume analysis, semantic matching, LLM feedback, or running this FastAPI backend.
---

# Motor de análisis de CVs (Ixtli)

## Flujo del análisis

`POST /analizar/` (multipart form: `archivo`, `titulo_de_trabajo`, `nombre_del_cliente`, `nombre_del_candidato` opcional) ejecuta este pipeline en `main.py`:

1. **Lookup en DB**: busca `Cliente` por nombre y `Trabajo` por título + cliente. Si no existen devuelve `{"error": ...}` con HTTP 200 (ojo: no usa códigos de error HTTP).
2. **Contexto del puesto**: concatena `trabajo.funciones`, `trabajo.habilidades` y `trabajo.perfil` en strings separados por coma ("No especificado" si están vacíos).
3. **`extraer_texto(archivo)`**: PyPDF2 para `.pdf`, docx2txt para `.docx`. Devuelve el texto en minúsculas. Cualquier otra extensión devuelve string vacío sin error. Luego `detectar_idioma` (langdetect) clasifica el CV como `en` o `es`, y `detectar_inyeccion` busca patrones de manipulación (texto invisible tipo "ignora las instrucciones", "PUNTUACION: 10/10") — si dispara, el puntaje del LLM se descarta (cae al semántico) y el análisis queda con `alerta_inyeccion=True`.
4. **`generar_feedback(...)`**: llama al LLM con la plantilla del idioma detectado. Las plantillas viven en **`prompts.py`** (la "guía de trabajo" del agente): una completa por idioma, porque un modelo 8B sigue el idioma dominante del prompt — una sola línea de "responde en inglés" no funciona.
5. **`calcular_match_score(...)`**: el CV se divide en fragmentos con solape (`fragmentar`, el modelo trunca a ~128 tokens y si no solo "leería" el inicio del CV); por cada componente del puesto se toma el fragmento que mejor matchea (max de cosenos) y se promedia ponderado: funciones 50%, habilidades 30%, perfil 20%. Componentes vacíos se excluyen y los pesos se renormalizan. Embeddings con `paraphrase-multilingual-MiniLM-L12-v2` (multilingüe es/en — el `all-MiniLM-L6-v2` original era solo inglés y daba cosenos bajísimos con CVs en español; carga global al iniciar, ~470MB de descarga la primera vez).
6. **Puntaje híbrido**: `calibrar_puntuacion` mapea el coseno del rango real [0.25, 0.65] a 0–10 (mide si el CV es del *rubro* correcto), `extraer_puntuacion_llm` parsea la línea `PUNTUACION: X/10` / `SCORE: X/10` del feedback (mide la *calificación* real), y `combinar_puntuaciones` pondera ambos con `PESO_SEMANTICO`. Si el LLM no devuelve puntuación parseable, queda solo el semántico. `decidir`: ≥8 "Alto", ≥7 "Promedio Alto", ≥6 "Promedio Bajo", ≥4 "Bajo", si no "Deficiente".
7. **Persistencia**: guarda el análisis en la tabla `analisis`, incluidos `raw_score` (coseno original) y `puntaje_llm`, para recalibrar pesos y umbrales con datos reales.

Respuesta: `{id, archivo, titulo_trabajo, nombre_del_candidato, idioma, match_score (0-10 híbrido), puntaje_semantico, puntaje_llm, decision, feedback, creado_en}`.

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
- **Los embeddings no miden calificación, solo afinidad temática**: un data scientist senior y uno flojo dan cosenos casi iguales (~0.45 vs ~0.43); E5 multilingüe se probó y es peor (comprime todo a 0.82–0.86, hasta un chef contra un puesto técnico). Por eso el puntaje es híbrido con el LLM — no intentar "arreglar" la separación cambiando solo el modelo de embeddings.
- Los pesos del match (funciones 0.5 / habilidades 0.3 / perfil 0.2), `PESO_SEMANTICO` y PISO=0.25/TECHO=0.65 se calibraron con pocos CVs reales — recalibrar con `raw_score`/`puntaje_llm` acumulados. Los `raw_score` previos al cambio de modelo (junio 2026) no son comparables.
- La calidad de los datos del puesto importa: funciones cargadas como párrafos de filosofía o habilidades abstractas ("Fundamentos Matemáticos") degradan el match semántico — cargar tareas y herramientas concretas que aparezcan en un CV.
- Para cambiar cómo analiza el agente (reglas, formato, idiomas) se edita `prompts.py`, no el código de `main.py`. Si se agrega un idioma hay que añadir su clave en `PROMPT_SISTEMA` y `PLANTILLA_ANALISIS` y mapearlo en el endpoint.
- CORS permite solo `localhost:3000` y `frontend-resume-analyzer.vercel.app`; si el frontend cambia de dominio hay que tocar `main.py`. El frontend viejo espera la API en inglés (`/analyze/`, `match_score` 0–1) — quedó incompatible desde el issue-6; se va a crear una interfaz nueva.
- Los CVs son datos personales: no loguear `texto_cv` ni guardarlo sin necesidad (el feedback guardado en `analisis` ya contiene extractos del CV — no exponerlo en listados públicos).
- **Inyección de prompt vía CV**: el texto del CV entra al prompt del LLM. Defensas: delimitadores `<<<INICIO_CV>>>/<<<FIN_CV>>>` + regla en el prompt de sistema (`prompts.py`), y `detectar_inyeccion` (`PATRONES_INYECCION` en `main.py`, con tests). Los patrones son deliberadamente específicos para no penalizar CVs inocentes ("redacté instrucciones de trabajo" no dispara). Si agregas patrones, agrega también casos legítimos a los tests de no-disparo.
- Nunca imprimir API keys al arrancar (el repo original lo hacía).
