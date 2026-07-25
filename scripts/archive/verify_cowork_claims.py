#!/usr/bin/env python3
"""Verificación documental determinista de los claims de la auto-auditoría de Cowork.

NO es juicio de LLM: abre los PDF del corpus y reporta en qué páginas aparece
literalmente cada término. La interpretación la hace Claude leyendo el output.
"""
import sys
import fitz  # PyMuPDF
import glob
import os

sys.stdout.reconfigure(encoding="utf-8")

ALL_PDFS = [p for p in glob.glob("**/*.pdf", recursive=True) if ".git" not in p]


def find_pdf(patterns):
    """Devuelve el primer PDF cuyo basename contiene alguno de los patrones."""
    for pat in patterns:
        for p in ALL_PDFS:
            if pat.lower() in os.path.basename(p).lower():
                return p
    return None


_CACHE = {}


def page_texts(pdf):
    if pdf not in _CACHE:
        doc = fitz.open(pdf)
        _CACHE[pdf] = [pg.get_text() for pg in doc]
        doc.close()
    return _CACHE[pdf]


def search(pdf, terms):
    texts = page_texts(pdf)
    out = {}
    for t in terms:
        hits = [i + 1 for i, txt in enumerate(texts) if t.lower() in txt.lower()]
        out[t] = hits
    return out, len(texts)


# Cada claim: qid, descripción, patrones de PDF, términos a buscar
CLAIMS = [
    ("hp009", "RFL 6,8 kOhm en sec 3.4.4 Circuitos de Sirena (Morley ZXe)",
     ["MIE-MI-530"], ["6,8", "6.8", "6k8", "6K8", "fin de línea", "fin de linea", "Circuitos de Sirena", "3.4.4", "kΩ"]),
    ("hp001", "Contrasena 4 digitos / niveles usuario-instalador sec 5.3 (CAD-250)",
     ["CAD-250-MC-380"], ["contraseña", "4 dígitos", "USUARIOS", "instalador", "AVANZADO", "OTROS", "REINICIAR", "tiempo de inactividad"]),
    ("hp003", "Orden conexion red-bateria: sec 2.3 no 1.2 (CAD-150-8)",
     ["CAD-150-8 Instalacion"], ["2.3", "1.2", "Alimentación de la central", "baterías", "para su seguridad", "puede dañar", "2.5"]),
    ("hp004", "Variante 220V del DGD-600: el manual especifica AC/DC?",
     ["DGD-600"], ["180", "240", "V CC", "V CA", "VCC", "VCA", "220", "corriente alterna", "230 V"]),
    ("cm003", "ASD531 datos tecnicos p91: temperatura y humedad",
     ["ASD531_OM"], ["-10", "+55", "+60", "55 °C", "60 °C", "70 %", "80 %", "95 %", "humedad", "condensación"]),
    ("cm001/cm005", "Doc Honeywell compatibilidad Notifier-Morley: respuesta cerrada",
     ["Compatibilidad-entre-equipos-Notifier-y-Morley"], ["No, no es posible", "no es posible", "protocolo", "AVERÍA DE TRANSMISIÓN", "avería de transmisión", "incompat"]),
    ("hp015", "CCD-103 central convencional 3 zonas + sec 6.4.4 anulacion por zona",
     ["CCD-103", "CCD103"], ["Convencional", "3 Zonas", "tres zonas", "6.4.4", "anulación", "anular", "zona"]),
    ("hp012", "AM2020/AFP1010: lazos y dispositivos por lazo (99+99 / 990 / 1980)",
     ["MNDT285", "MIDT280", "MSDT280", "AM2020", "AM-2020", "MFDT280"], ["99", "990", "1980", "lazos", "lazo", "detectores", "módulos", "SLC"]),
    ("hp014", "Conexionado aisladores ID2000 (sec 3.x del MI-DT-180/MIDT180)",
     ["MIDT180", "MI-DT-180"], ["aislador", "aislamiento", "isolador", "Clase A", "Clase B", "3.", "lazo"]),
    ("hp005", "ID3000 pantalla coincidencia 2 equipos sec 7.6.1.1 (MPDT190)",
     ["MPDT190"], ["COINCIDENCIA 2 EQUIPOS", "coincidencia", "7.6.1.1", "UN ÚNICO EQUIPO", "doble"]),
    ("hp008", "Detectores compatibles ID3000 - Apendice C (MIDT190)",
     ["MIDT190"], ["Apéndice C", "compatibles", "SDX-751", "NFXI-OPT", "FSI-851", "serie 500", "B501"]),
    ("hp007", "VESDA-E VEP Tabla 7-1 mantenimiento - tareas anuales",
     ["VEP-A00", "VEP-A10", "VEP"], ["Tabla 7", "mantenimiento", "anual", "humo", "filtro", "flujo", "Anualmente"]),
    ("cm004", "ID3000 capacidad: 198 equipos/lazo, EN54-2 512",
     ["MIDT190", "MPDT190"], ["198", "512", "EN54-2", "EN 54-2", "13.7", "99", "8 lazos"]),
    ("cm008", "MIE-MI-600 (ZXSe) menciona 'ZXe'?",
     ["MIE-MI-600"], ["ZXe", "ZX2e", "ZX5e", "convencional", "ZXSe"]),
    ("mc003", "Retardo sirena ID3000 / Vision LT rangos (MCDT190 / MIE-MI-580)",
     ["MCDT190"], ["retardo", "delay", "256", "segundos", "múltiplos de 8", "código"]),
    ("mc003b", "Vision LT retardos R1/R2 (MIE-MI-580)",
     ["MIE-MI-580"], ["retardo", "R1", "R2", "300", "30", "10 min", "0-300"]),
]


def main():
    print(f"Corpus: {len(ALL_PDFS)} PDFs\n" + "=" * 70)
    for qid, desc, pdf_pats, terms in CLAIMS:
        pdf = find_pdf(pdf_pats)
        print(f"\n[{qid}] {desc}")
        if not pdf:
            print(f"   PDF NO LOCALIZADO (patrones: {pdf_pats})")
            continue
        res, npages = search(pdf, terms)
        print(f"   PDF: {os.path.basename(pdf)} ({npages} pág.)")
        for t, hits in res.items():
            if hits:
                show = hits[:10]
                more = f" (+{len(hits)-10})" if len(hits) > 10 else ""
                print(f"      '{t}': págs {show}{more}")
            else:
                print(f"      '{t}': -- no aparece --")


if __name__ == "__main__":
    main()
