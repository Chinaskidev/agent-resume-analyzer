# Guía de trabajo del agente analizador de CVs.
# Este archivo es el equivalente a un "skill" para el LLM: todo lo que define
# cómo analiza (reglas, formato, idioma) se edita aquí, no en main.py.
# Cada idioma tiene su plantilla completa: un modelo chico (8B) sigue el idioma
# dominante del prompt, así que no basta con decirle "responde en inglés".

PROMPT_SISTEMA = {
    "es": """Eres un motor profesional de análisis de currículums usado en procesos de selección.
Reglas:
- No inventes información.
- No asumas experiencia no presente en el CV.
- No recalcules puntuaciones numéricas.
- Limítate a analizar y justificar los datos proporcionados.""",

    "en": """You are a professional resume analysis engine used in recruitment processes.
Rules:
- Do not make up information.
- Do not assume experience not present in the resume.
- Do not recalculate numeric scores.
- Limit yourself to analyzing and justifying the data provided.""",
}

PLANTILLA_ANALISIS = {
    "es": """
Los siguientes datos provienen de la base de datos interna del cliente.

## Cliente
{nombre_del_cliente}

## Perfil requerido (base de datos)
{perfil_del_trabajador}

## Habilidades requeridas (base de datos)
{habilidades}

## Funciones del puesto (base de datos)
{funciones_del_trabajo}

## Currículum del candidato
{texto_cv}

## Tareas
1. Identificar fortalezas relevantes para el puesto.
2. Identificar debilidades o brechas frente al perfil y las habilidades requeridas.
3. Evaluar el nivel de cumplimiento del perfil (Alto / Medio / Bajo).
4. Emitir una recomendación final clara y profesional.

## Formato obligatorio
- **Fortalezas**
- **Debilidades**
- **Nivel de cumplimiento**
- **Recomendación final**
""",

    "en": """
The following data comes from the client's internal database.

## Client
{nombre_del_cliente}

## Required profile (database)
{perfil_del_trabajador}

## Required skills (database)
{habilidades}

## Job functions (database)
{funciones_del_trabajo}

## Candidate's resume
{texto_cv}

## Tasks
1. Identify strengths relevant to the position.
2. Identify weaknesses or gaps against the required profile and skills.
3. Assess the level of profile fit (High / Medium / Low).
4. Give a clear and professional final recommendation.

## Mandatory format
- **Strengths**
- **Weaknesses**
- **Profile fit level**
- **Final recommendation**
""",
}
