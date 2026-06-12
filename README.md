# Ixtli

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM_local_·_Ministral-Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)

![Ixtli](./ixtli-logo.png)

> **Ixtli** proviene del náhuatl y significa *"rostro"*, *"cara"* u *"ojo"*. Los antiguos nahuas lo asociaban con la mirada, la expresión facial y la identidad — la capacidad de **ver y reconocer** a la persona detrás de cada candidato.

---

## Descripción

**Ixtli** es un sistema de reclutamiento potenciado por inteligencia artificial que analiza currículums (CV) y los compara con los puestos de trabajo definidos por cada cliente. Su objetivo es ayudar a las empresas a encontrar al talento ideal de forma más eficiente y precisa, optimizando los tiempos y la calidad del proceso de contratación.

## Qué hace

Ixtli recibe el currículum de un candidato (en formato **PDF** o **DOCX**) junto con el cliente y el puesto al que aspira, y devuelve un análisis estructurado:

- **Extracción de texto** — lee automáticamente el contenido del CV, sin importar si llega en PDF o Word.
- **Match semántico** — mide qué tan bien encaja el CV con las funciones, habilidades y perfil del puesto usando similitud semántica multilingüe (español e inglés), generando un puntaje objetivo de afinidad.
- **Puntaje híbrido (0–10)** — combina la afinidad semántica con la evaluación de un LLM que lee el CV completo, y clasifica el resultado en *Alto*, *Promedio Alto*, *Promedio Bajo*, *Bajo* o *Deficiente*.
- **Feedback con IA** — genera un análisis en lenguaje natural **en el idioma del CV** que resume fortalezas y debilidades del candidato, evalúa si cumple con el perfil requerido y entrega una recomendación final de contratación.
- **Historial** — cada análisis queda guardado y consultable, listo para entregar resultados ordenados a cada cliente.

Además, permite a cada cliente **registrar sus propios puestos de trabajo**, con sus habilidades, funciones y el perfil esperado del trabajador, de modo que el análisis se adapte a las políticas y necesidades de cada empresa.

## Cómo funciona

El proceso combina dos motores complementarios, **ambos corriendo localmente** — los CVs nunca salen de la infraestructura:

1. Un modelo de **embeddings semánticos** que calcula la afinidad temática entre el CV y el puesto, sin costo por consulta.
2. Un **modelo de lenguaje local** (Ministral 3 8B vía Ollama) que evalúa la calificación real del candidato, redacta el feedback cualitativo y la recomendación final.

Las dos señales se combinan en un único puntaje calibrado de 0 a 10: la semántica garantiza que el candidato sea del rubro correcto, y el LLM distingue al candidato fuerte del flojo dentro del mismo rubro. Cada candidato obtiene así una métrica cuantitativa de ajuste y una valoración interpretable y accionable para el equipo de reclutamiento.
