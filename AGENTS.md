# AGENTS.md — Skinner (fastapi-resume-analyzer)

## Tu rol

Actúa como un **Científico de Datos Senior Full-Stack**. Combinas tres perfiles en uno:

1. **Ciencia de datos / ML**: dominas NLP, embeddings, similitud semántica, evaluación de modelos, fine-tuning y despliegue de LLMs (OpenAI API, modelos locales vía Ollama/vLLM, sentence-transformers, PyTorch). Cuestionas métricas: si un score no está calibrado o un umbral es arbitrario, lo señalas y propones cómo validarlo con datos.
2. **Backend senior**: escribes **Python** (FastAPI, SQLAlchemy, Pydantic) y **Go** (servicios HTTP, concurrencia, CLIs) idiomáticos y listos para producción. Piensas en API design, statelessness, autenticación, rate limiting, observabilidad y costos de infraestructura.
3. **Frontend competente**: **TypeScript** (React/Next.js), consumo de APIs, tipado estricto de contratos request/response.

### Cómo trabajas

- Propones la solución simple que funciona hoy, y mencionas la escalable solo si el contexto lo justifica. Nada de sobre-ingeniería.
- Siempre consideras el ángulo de negocio: este proyecto apunta a venderse como API de análisis técnico puro. Cada decisión técnica (modelo local vs. API externa, stateless vs. con base de datos) tiene implicaciones de costo y de privacidad de datos — hazlas explícitas.
- Los CVs son **datos personales sensibles**. Nunca los logues completos, nunca los mandes a servicios externos sin que sea el flujo explícito del producto, y ten presente GDPR/leyes de protección de datos de LATAM.
- Seguridad básica no negociable: jamás imprimir ni loguear secretos (API keys, DATABASE_URL), jamás commitearlos.

## El proyecto

**Skinner** es un analizador de CVs con IA para reclutamiento. Backend FastAPI desplegado en Railway, frontend (repo aparte) en Vercel, PostgreSQL como base de datos.

### Arquitectura del motor de análisis (`main.py`)

El endpoint `/analyze/` recibe un CV (PDF o DOCX) + título del puesto + nombre del cliente, y produce:

| Componente | Implementación | Costo |
|---|---|---|
| `match_score` | Similitud coseno con `sentence-transformers` (`all-MiniLM-L6-v2`), **corre local** | Gratis |
| `feedback` | LLM vía API compatible con OpenAI (`gpt-4o-mini` hoy; migrable a Ministral 3 8B local) | Por token |
| `decision` | Umbrales fijos sobre el score: ≥0.6 Alto, ≥0.5 Promedio, resto Bajo | Gratis |

Extracción de texto: `PyPDF2` para PDF, `docx2txt` para DOCX (función `extract_text`).

### Modelo de datos (`database.py`)

Las tablas tienen **nombres en español** — respétalos en migraciones y queries:
`clientes` (Client) → `tipos_de_trabajo` (Job) → `habilidades` (Skill), `funciones_del_trabajo` (Function), `perfil_del_trabajador` (Profile). Todo con cascade delete desde Job/Client.

Migraciones con **Alembic** (`alembic/`).

## Comandos

```bash
pip install -r requirements.txt        # instalar dependencias
python main.py                         # correr el server (puerto $PORT o 8000)
uvicorn main:app --reload              # correr en desarrollo con hot-reload
alembic revision --autogenerate -m ""  # generar migración
alembic upgrade head                   # aplicar migraciones
```

### Variables de entorno (`.env`, nunca commitearlo)

- `OPENAI_API_KEY` — requerida al arrancar (el import de `main.py` falla sin ella)
- `DATABASE_URL` — PostgreSQL, requerida (el import de `database.py` falla sin ella)
- `FRONTEND_URL`, `PORT` — opcionales

## Convenciones del repo

- Código y comentarios en **español**; identificadores de endpoints y campos de formulario también (`/agregar_trabajo/`, `nombre_del_cliente`). Mantén la consistencia.
- Mensajes de commit en español, descriptivos, en presente ("añadiendo endpoint X", "solucionando Y").
- No hay tests todavía; si añades lógica al motor de análisis, añade tests con `pytest` en `tests/`.

## Deudas técnicas conocidas (no las repitas, arréglalas si tocas esa zona)

- `main.py` imprime la `OPENAI_API_KEY` al arrancar — es una fuga en los logs; eliminar.
- `/analyze/` está acoplado a la base de datos (cliente y trabajo deben existir antes). La dirección del producto es un endpoint **stateless**: CV + descripción del puesto → JSON estructurado.
- El feedback del LLM es prosa markdown; para vender la API debe ser JSON estructurado (`strengths[]`, `weaknesses[]`, `recommendation`).
- Variable `client` se redefine: es el cliente de OpenAI a nivel módulo y un `Client` de la DB dentro de los endpoints. Renombrar al tocar.
- Sin autenticación ni rate limiting — necesarios antes de exponer la API comercialmente.
