# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

"Ixtli": API backend en FastAPI para analizar currículums (CV) contra puestos de trabajo definidos por clientes. Combina similitud semántica (sentence-transformers, local) con feedback generado por un LLM (`gpt-4o-mini`). Se despliega en Railway (API + PostgreSQL); el frontend vive en otro repo (`frontend-resume-analyzer` en Vercel).

## Documentación principal

La guía detallada de este repo vive en `.claude/` — léela antes de trabajar:

- **`.claude/AGENT.md`** — rol de trabajo, filosofía (soluciones simples, ángulo de negocio, privacidad de los CVs), convenciones del repo (todo en español: código, endpoints, campos de formulario, commits) y deudas técnicas conocidas.
- **`.claude/skills/resume-analyzer/SKILL.md`** — pipeline completo de `POST /analyze/`, cómo correr/probar (incluido sin Postgres con SQLite), cómo cambiar el LLM (OpenAI ↔ modelo local), el modelo de datos y las trampas conocidas.

## Esencial de un vistazo

- **Arquitectura**: todo el backend son dos archivos. `main.py` (app FastAPI: endpoints, extracción de texto, scoring semántico con `all-MiniLM-L6-v2`, prompt al LLM) y `database.py` (modelos SQLAlchemy con tablas en español: `clientes` → `tipos_de_trabajo` → `habilidades`/`funciones_del_trabajo`/`perfil_del_trabajador`).
- **Comandos**: `pip install -r requirements.txt`, `python main.py` (o `uvicorn main:app --reload` en dev), `alembic upgrade head` para migraciones. No hay tests ni linter.
- **Variables de entorno** (`.env`): `OPENAI_API_KEY` y `DATABASE_URL` son obligatorias — ambos imports fallan al arrancar si faltan. Alembic en modo online usa `sqlalchemy.url` hardcodeada en `alembic.ini` (línea 66), no `DATABASE_URL`.
