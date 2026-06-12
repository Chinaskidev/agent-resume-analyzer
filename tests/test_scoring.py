# Tests de la logica de scoring: funciones puras de main.py, sin DB ni LLM.
# Correr con: .virtual/bin/python -m pytest
#
# Ojo: calibrar_puntuacion y decidir documentan la calibracion vigente
# (PISO=0.25, TECHO=0.65, umbrales de decision). Si se recalibra con datos
# acumulados, estos tests deben actualizarse a conciencia.

import pytest

from main import (
    PESO_SEMANTICO,
    calibrar_puntuacion,
    combinar_puntuaciones,
    decidir,
    extraer_puntuacion_llm,
    fragmentar,
)


# ==========================================================
# fragmentar
# ==========================================================

def test_fragmentar_texto_corto_devuelve_un_fragmento():
    texto = "ingeniero de software con cinco años de experiencia"
    assert fragmentar(texto) == [texto]


def test_fragmentar_texto_largo_divide_con_solape():
    palabras = [f"palabra{i}" for i in range(300)]
    fragmentos = fragmentar(" ".join(palabras), tamano=150, solape=30)

    assert len(fragmentos) > 1
    # cada fragmento tiene como maximo `tamano` palabras
    assert all(len(f.split()) <= 150 for f in fragmentos)
    # las ultimas `solape` palabras de un fragmento abren el siguiente
    cola = fragmentos[0].split()[-30:]
    cabeza = fragmentos[1].split()[:30]
    assert cola == cabeza


def test_fragmentar_cubre_todo_el_texto():
    palabras = [f"palabra{i}" for i in range(500)]
    fragmentos = fragmentar(" ".join(palabras))
    # la ultima palabra del texto aparece en el ultimo fragmento
    assert "palabra499" in fragmentos[-1]


# ==========================================================
# calibrar_puntuacion (mapeo lineal de [0.25, 0.65] a 0-10)
# ==========================================================

@pytest.mark.parametrize("coseno, esperado", [
    (0.25, 0.0),    # piso exacto
    (0.10, 0.0),    # bajo el piso: clamp a 0
    (-0.3, 0.0),    # coseno negativo (texto sin relacion alguna)
    (0.65, 10.0),   # techo exacto
    (0.90, 10.0),   # sobre el techo: clamp a 10
    (0.45, 5.0),    # punto medio
    (0.50, 6.25),
])
def test_calibrar_puntuacion(coseno, esperado):
    assert calibrar_puntuacion(coseno) == esperado


def test_calibrar_puntuacion_redondea_a_dos_decimales():
    resultado = calibrar_puntuacion(0.57)
    assert resultado == round(resultado, 2)
    # el caso que motivo el redondeo: 0.57 debe dar 8.0 exacto, no 7.9999
    assert resultado == 8.0


# ==========================================================
# extraer_puntuacion_llm (parsear salida de un 8B es fragil)
# ==========================================================

@pytest.mark.parametrize("feedback, esperado", [
    ("PUNTUACION: 8/10", 8.0),
    ("SCORE: 9/10", 9.0),
    ("**PUNTUACION: 8.5/10**", 8.5),                      # negritas de markdown
    ("- **PUNTUACION: 7/10** (esta es la última línea)", 7.0),
    ("puntuación: 7,5/10", 7.5),                          # minúsculas, acento y coma decimal
    ("Puntuacion : 6 / 10", 6.0),                         # espacios alrededor de : y /
    ("SCORE:10/10", 10.0),                                # sin espacios
    ("PUNTUACION: 0/10", 0.0),                            # cero es puntuacion valida
])
def test_extraer_puntuacion_formatos(feedback, esperado):
    assert extraer_puntuacion_llm(feedback) == esperado


def test_extraer_puntuacion_dentro_de_feedback_realista():
    feedback = """### Análisis del candidato

- **Fortalezas**: experiencia sólida en Python y FastAPI.
- **Debilidades**: sin experiencia en Docker.
- **Nivel de cumplimiento**: Alto
- **Recomendación final**: avanzar a entrevista técnica.
- **PUNTUACION: 8.5/10**"""
    assert extraer_puntuacion_llm(feedback) == 8.5


def test_extraer_puntuacion_toma_la_ultima_si_hay_varias():
    feedback = "El sistema calculó SCORE: 5/10 antes.\n\n**PUNTUACION: 9/10**"
    assert extraer_puntuacion_llm(feedback) == 9.0


def test_extraer_puntuacion_sin_linea_devuelve_none():
    assert extraer_puntuacion_llm("El candidato es bueno pero no dejo puntaje.") is None


def test_extraer_puntuacion_placeholder_sin_numero_devuelve_none():
    # el LLM a veces repite la instruccion literal sin reemplazar la X
    assert extraer_puntuacion_llm("**PUNTUACION: X/10**") is None


def test_extraer_puntuacion_fuera_de_rango_se_recorta():
    assert extraer_puntuacion_llm("PUNTUACION: 15/10") == 10.0


def test_extraer_puntuacion_feedback_vacio():
    assert extraer_puntuacion_llm("") is None


# ==========================================================
# combinar_puntuaciones (hibrido semantico + LLM)
# ==========================================================

def test_combinar_pondera_segun_peso_semantico():
    esperado = round(PESO_SEMANTICO * 5.0 + (1 - PESO_SEMANTICO) * 9.0, 2)
    assert combinar_puntuaciones(5.0, 9.0) == esperado


def test_combinar_sin_puntaje_llm_devuelve_el_semantico():
    assert combinar_puntuaciones(7.3, None) == 7.3


def test_combinar_extremos():
    assert combinar_puntuaciones(0.0, 0.0) == 0.0
    assert combinar_puntuaciones(10.0, 10.0) == 10.0


def test_combinar_el_ancla_semantica_hunde_al_fuera_de_rubro():
    # caso chef: aunque el LLM regale puntos, el semantico 0 lo deja en Deficiente
    final = combinar_puntuaciones(0.0, 2.0)
    assert decidir(final) == "Deficiente"


# ==========================================================
# decidir (umbrales de decision)
# ==========================================================

@pytest.mark.parametrize("score, esperado", [
    (10.0, "Alto"),
    (8.0, "Alto"),            # borde inferior de Alto
    (7.99, "Promedio Alto"),
    (7.0, "Promedio Alto"),
    (6.0, "Promedio Bajo"),
    (4.0, "Bajo"),
    (3.99, "Deficiente"),
    (0.0, "Deficiente"),
])
def test_decidir_umbrales(score, esperado):
    assert decidir(score) == esperado
