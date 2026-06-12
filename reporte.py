# Genera el informe PDF de un analisis, con marca de agua de Ixtli.
import os
import re
import markdown
from fpdf import FPDF

LOGO_CHICO = os.path.join(os.path.dirname(__file__), "ixtli-logo-chico.png")

class ReporteIxtli(FPDF):
    def header(self):
        #marca de agua diagonal, en cada pagina
        with self.local_context(fill_opacity=0.08):
            self.set_font("helvetica", "B", 48)
            self.set_text_color(30, 30, 30)
            with self.rotation(45, x=self.w / 2, y=self.h / 2):
                self.text(x=self.w / 2 - 80, y=self.h / 2, text="Generado por Ixtli")

    def footer(self):
        # logo chico a la izquierda (fpdf2 incrusta la imagen una sola vez
        # aunque se dibuje en todas las paginas) + leyenda centrada
        if os.path.exists(LOGO_CHICO):
            self.image(LOGO_CHICO, x=10, y=self.h - 17, w=9)
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Información generada por Ixtli · página {self.page_no()}", align="C")


# helvetica solo soporta latin-1: reemplaza caracteres fuera de ese rango
# (emojis, guiones largos del LLM) para que la generacion nunca explote
def _latin1(texto) -> str:
    return str(texto).encode("latin-1", "replace").decode("latin-1")


def generar_pdf_analisis(analisis, nombre_cliente: str) -> bytes:
    pdf = ReporteIxtli()
    pdf.add_page()

    # titulo (el logo va en el pie de pagina)
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "Ixtli - Informe de análisis de CV", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # datos del analisis
    datos = [
        ("Candidato", analisis.nombre_del_candidato or "-"),
        ("Archivo", analisis.archivo),
        ("Puesto", analisis.titulo_trabajo),
        ("Cliente", nombre_cliente or "-"),
        ("Fecha", analisis.creado_en.strftime("%d/%m/%Y %H:%M") if analisis.creado_en else "-"),
    ]
    for etiqueta, valor in datos:
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(30, 7, _latin1(f"{etiqueta}:"))
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 7, _latin1(valor), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # puntaje y decision
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, _latin1(f"Match score: {analisis.match_score}/10 - {analisis.decision}"),
             new_x="LMARGIN", new_y="NEXT")
    if analisis.alerta_inyeccion:
        pdf.set_text_color(180, 60, 0)
        pdf.set_font("helvetica", "B", 11)
        pdf.multi_cell(0, 6, _latin1("ALERTA: el CV contiene texto que intenta manipular el análisis. "
                                     "Puntaje del LLM descartado; revisar manualmente."))
        pdf.set_text_color(30, 30, 30)
    pdf.ln(4)

    # feedback: markdown -> html -> pdf (con fallback a texto plano)
    pdf.set_font("helvetica", "", 11)
    try:
        html = markdown.markdown(analisis.feedback)
        pdf.write_html(_latin1(html))
    except Exception:
        texto_plano = re.sub(r"[*#_`]", "", analisis.feedback)
        pdf.multi_cell(0, 6, _latin1(texto_plano))

    return bytes(pdf.output())
