# Ixtli

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)

![Ixtli](./ixtli-logo.png)

> **Ixtli** proviene del náhuatl y significa *"rostro"*, *"cara"* u *"ojo"*. Los antiguos nahuas lo asociaban con la mirada, la expresión facial y la identidad — la capacidad de **ver y reconocer** a la persona detrás de cada candidato.

---

## Descripción

**Ixtli** es un sistema de reclutamiento potenciado por inteligencia artificial que analiza currículums (CV) y los compara con los puestos de trabajo definidos por cada cliente. Su objetivo es ayudar a las empresas a encontrar al talento ideal de forma más eficiente y precisa, optimizando los tiempos y la calidad del proceso de contratación.

## Qué hace

Ixtli recibe el currículum de un candidato (en formato **PDF** o **DOCX**) junto con el cliente y el puesto al que aspira, y devuelve un análisis estructurado:

- **Extracción de texto** — lee automáticamente el contenido del CV, sin importar si llega en PDF o Word.
- **Match semántico** — mide qué tan bien encaja el perfil del candidato con las funciones del puesto usando procesamiento de lenguaje natural (similitud semántica), generando un puntaje objetivo de afinidad.
- **Decisión por puntaje** — clasifica el resultado en *Puntaje Alto*, *Puntaje Promedio* o *Puntaje Bajo* según qué tan cerca esté el candidato del perfil buscado.
- **Feedback con IA** — genera un análisis en lenguaje natural que resume los puntos fuertes y débiles del candidato, evalúa si cumple con el perfil requerido y entrega una recomendación final de contratación.

Además, permite a cada cliente **registrar sus propios puestos de trabajo**, con sus habilidades, funciones y el perfil esperado del trabajador, de modo que el análisis se adapte a las políticas y necesidades de cada empresa.

## Cómo funciona

El proceso combina dos motores complementarios:

1. Un modelo de **embeddings semánticos** que corre localmente y calcula la afinidad entre el CV y el puesto sin costo por consulta.
2. Un **modelo de lenguaje (LLM)** que redacta el feedback cualitativo y la recomendación final.

De esta forma, cada candidato obtiene tanto una métrica cuantitativa de ajuste como una valoración interpretable y accionable para el equipo de reclutamiento.
