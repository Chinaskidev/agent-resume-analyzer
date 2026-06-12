# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

"Ixtli": analizador de currículums (CV) contra puestos de trabajo definidos por clientes. Backend FastAPI + interfaz de demo en Streamlit. El puntaje es **híbrido**: similitud semántica (sentence-transformers, local) combinada con la puntuación que da un LLM (Ministral 3 8B vía Ollama por defecto, configurable por env vars). Stack 100% local (privacidad de los CVs como argumento de venta); el despliegue en Railway (API + PostgreSQL) y el frontend viejo de Vercel quedaron obsoletos tras el renombrado a español.

## Documentación principal

La guía detallada de este repo vive en `.claude/` — léela antes de trabajar:

- **`.claude/AGENT.md`** — rol de trabajo, filosofía (soluciones simples, ángulo de negocio, privacidad de los CVs), convenciones del repo (todo en español: código, endpoints, campos de formulario, commits) y deudas técnicas conocidas.
- **`.claude/skills/resume-analyzer/SKILL.md`** — pipeline completo de `POST /analizar/` (puntaje híbrido incluido), cómo correr/probar, cómo cambiar el LLM (Ollama ↔ OpenAI), el modelo de datos y las trampas conocidas.

## Esencial de un vistazo

- **Arquitectura**: módulos planos por responsabilidad (sin carpetas — extraer módulos cuando duela, no antes). `main.py` (app FastAPI: endpoints en español — `/analizar/`, `/agregar_trabajo/`, `/clientes/`, `/analisis/` — y el cliente LLM), `motor.py` (el motor de análisis: extracción de texto, idioma, detección de inyecciones, match semántico por fragmentos con `paraphrase-multilingual-MiniLM-L12-v2` de carga perezosa, puntaje híbrido 0.4·semántico + 0.6·LLM — testeable sin DB ni LLM), `prompts.py` (la "guía de trabajo" del LLM: plantillas completas por idioma es/en — el feedback sale en el idioma del CV), `database.py` (modelos SQLAlchemy en español: `Cliente` → `Trabajo` → `Habilidad`/`Funcion`/`Perfil`/`Analisis`; la tabla `analisis` guarda el historial con `raw_score` y `puntaje_llm` para recalibrar), e `interfaz.py` (Streamlit, consume la API por HTTP).
- **Comandos**: `uvicorn main:app --reload` (API), `streamlit run interfaz.py` (interfaz, puerto 8501), `alembic upgrade head` (migraciones), `python -m pytest` (tests de la lógica de scoring en `tests/`, sin DB ni LLM). No hay linter.
- **Variables de entorno** (`.env`): `DATABASE_URL` es obligatoria (el import de `database.py` falla si falta). El LLM se configura con `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (default: Ollama local con `ministral-3:8b`). Alembic lee `DATABASE_URL` vía `alembic/env.py`, pero **no carga `.env` solo** — exportarla antes de migrar: `export $(grep -v '^#' .env | xargs)`.
- **Calibración**: los pesos del puntaje (`PESO_SEMANTICO`, pesos por componente, PISO/TECHO) se calibraron con pocos CVs reales; la tabla `analisis` acumula los datos para recalibrar. Al cargar puestos, usar funciones/habilidades **concretas** (como aparecerían en un CV), no descripciones abstractas — degradan el match semántico.
