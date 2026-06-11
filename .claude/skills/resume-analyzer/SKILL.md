---
name: resume-analyzer
description: Guía del motor de análisis de CVs de Ixtli. Usar cuando se trabaje en el endpoint /analyze/, el match score semántico, el feedback con LLM (OpenAI o modelo local Ministral/Ollama), la extracción de texto de PDF/DOCX, o al correr/desplegar este backend FastAPI. Use when working on resume analysis, semantic matching, LLM feedback, or running this FastAPI backend.
---

# Motor de análisis de CVs (Ixtli)

## Flujo del análisis

`POST /analyze/` (multipart form: `file`, `job_title`, `client_name`) ejecuta este pipeline en `main.py`:

1. **Lookup en DB**: busca `Client` por nombre y `Job` por título + cliente. Si no existen devuelve `{"error": ...}` con HTTP 200 (ojo: no usa códigos de error HTTP).
2. **Contexto del puesto**: concatena `job.functions` y los `Profile` del job en strings separados por coma.
3. **`extract_text(file)`**: PyPDF2 para `.pdf`, docx2txt para `.docx`. Devuelve el texto en minúsculas. Cualquier otra extensión devuelve string vacío sin error.
4. **`generate_gpt_feedback(...)`**: llama al LLM con un prompt en español que pide puntos fuertes/débiles, cumplimiento del perfil y recomendación final, en markdown.
5. **`match_resume_to_job(...)`**: similitud coseno entre embeddings del CV y de las funciones del trabajo con `all-MiniLM-L6-v2` (carga global al iniciar, ~80MB de descarga la primera vez).
6. **Decisión por umbral**: score ≥0.6 → "Puntaje Alto", ≥0.5 → "Puntaje Promedio", si no → "Puntaje Bajo".

Respuesta: `{file_name, job_title, match_score, decision, feedback}`.

## Correr el proyecto

```bash
pip install -r requirements.txt
uvicorn main:app --reload   # desarrollo
python main.py              # como en producción (puerto $PORT o 8000)
```

Requiere `.env` con `OPENAI_API_KEY` y `DATABASE_URL` (PostgreSQL) — **ambos imports fallan al arrancar si faltan**. Para probar sin Postgres real: `DATABASE_URL=sqlite:///./test.db` funciona con SQLAlchemy para desarrollo local.

Probar el análisis sin frontend:

```bash
curl -X POST http://localhost:8000/analyze/ \
  -F "file=@cv.pdf" \
  -F "job_title=Backend Developer" \
  -F "client_name=Acme"
```

El cliente y el trabajo deben existir antes (crearlos con `POST /agregar_trabajo/`).

## Cambiar el LLM (OpenAI ↔ modelo local)

El feedback usa el SDK de OpenAI, así que cualquier servidor compatible (Ollama, vLLM) funciona cambiando solo la construcción del cliente en `main.py`:

```python
# OpenAI (actual)
client = OpenAI(api_key=OPENAI_API_KEY)        # model="gpt-4o-mini"

# Local con Ollama (Ministral 3 8B, licencia Apache 2.0)
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
# y en generate_gpt_feedback: model="ministral-3:8b"
```

Criterio: OpenAI para arrancar barato (~$0.001/CV); modelo local cuando el argumento de venta es privacidad (los CVs no salen de la infraestructura) o el volumen justifica un GPU.

## Modelo de datos

Tablas en español, definidas en `database.py`, migraciones con Alembic:

- `clientes` (`Client.name` es unique) → `tipos_de_trabajo` (`Job`)
- `Job` → `habilidades` (`Skill`), `funciones_del_trabajo` (`Function`), `perfil_del_trabajador` (`Profile`), todo cascade delete.

`POST /agregar_trabajo/` recibe habilidades y funciones como strings separados por coma y los divide con `split(",")`.

## Trampas conocidas

- `main.py:24` imprime la API key al arrancar — eliminar ese `print`, nunca replicar el patrón.
- El nombre `client` está sobrecargado: cliente OpenAI a nivel módulo y `Client` de DB dentro de los endpoints. Al editar `generate_gpt_feedback` el `client` que usa es el de OpenAI.
- Los errores de negocio se devuelven como `{"error": ...}` con HTTP 200; el frontend depende de esto, no lo cambies sin coordinar.
- `match_score` compara contra las **funciones** del trabajo, no contra habilidades ni perfil; los umbrales 0.6/0.5 son arbitrarios y no están calibrados.
- CORS permite solo `localhost:3000` y `frontend-resume-analyzer.vercel.app`; si el frontend cambia de dominio hay que tocar `main.py`.
- Los CVs son datos personales: no loguear `resume_text` ni guardarlo sin necesidad.
