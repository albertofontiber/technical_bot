"""toc_heuristic.py — detector determinista de páginas de ÍNDICE (s102, L2c).

Una página de índice lista títulos con su nº de página: matchea léxicamente una query
(los títulos contienen los términos) pero rara vez contiene el CONTENIDO. Las señales
exigen números de página NO-DECRECIENTES: es lo que separa un índice de un packing-list
o una tabla de specs (también acaban líneas en dígitos, pero con cantidades pequeñas
repetidas, no una secuencia de páginas).

Historia (evals/s102_toc_measure.yaml): nació como demote en el rerank
(RERANK_DEMOTE_TOC) y se midió NO-GO — 0 GAINS con superficie estocástica ~1-2 TOCs
servidos por run (proxy léxico servido, una extracción), y la exclusión pre-backend
re-baraja el LLM-rerank en el orden del RUIDO BASE (S1: el rerank no es determinista ni
a temp=0 — 2 golds sin TOC en pool también cambiaron slots; la clase DEC-091). El seam
vive en evals/s102_toc_seam.patch por si se re-mide. El consumidor VIVO es el INSTRUMENTO
(factlevel_assessment): matar anclas-TOC en el crédito de soporte cierra la cuarentena
H4 (un TOC-con-anchor clasificaba miss como synthesis-miss cuando el contenido nunca
llegó al generador); la red dual re-adjudica los kills porque un título de índice SÍ
puede soportar hechos nominales ("Importar archivo de licencia (.bin)").

OJO deriva (cross-model s102): el patch del seam lleva su PROPIA copia congelada de esta
heurística (snapshot de lo que se midió). Si cambias is_toc_page aquí y quieres re-medir el
seam, REGENERA el patch — no re-midas con la copia stale.
"""
import re

_TOC_DOT_LEADER_RE = re.compile(r"(?:\.[ \t]?){4,}[ \t]*(\d{1,4})[ \t]*$", re.M)
_TOC_HEADING_RE = re.compile(
    r"(?im)^[\s\d.·|#*—-]{0,12}(índice|indice|sommario|sumario|contenidos?|"
    r"tabla de contenidos?|table of contents|contents)\b[^\n]{0,40}$"
)
_TOC_TRAIL_NUM_RE = re.compile(r"(?:^|[ \t])(\d{1,4})[ \t]*$")


def _nondecreasing_ratio(nums: list[int]) -> float:
    if len(nums) < 2:
        return 0.0
    return sum(1 for a, b in zip(nums, nums[1:]) if b >= a) / (len(nums) - 1)


def is_toc_page(text: str) -> bool:
    """Heurística determinista y CONSERVADORA (preferir falso-negativo a marcar contenido).

    Señal A: ≥4 líneas con dot-leader + nº ("Instalación ..... 12") en secuencia no-decreciente.
    Señal B: cabecera de índice (es/en/it, admite prefijo markdown #/**) al inicio + la mayoría
    de líneas acaban en nº de página no-decreciente (cubre TOCs cuyo OCR perdió los puntos —
    el caso HOP-138-8ES p.2 que motivó todo esto).
    """
    if not text:
        return False
    dot_nums = [int(m.group(1)) for m in _TOC_DOT_LEADER_RE.finditer(text)]
    if len(dot_nums) >= 4 and _nondecreasing_ratio(dot_nums) >= 0.8 and dot_nums[-1] >= 5:
        return True
    if _TOC_HEADING_RE.search(text[:300]):
        lines = [ln for ln in (l.strip() for l in text.splitlines()) if ln]
        nums = [int(m.group(1)) for ln in lines
                if (m := _TOC_TRAIL_NUM_RE.search(ln))]
        if (len(lines) >= 8 and len(nums) >= max(5, len(lines) // 2)
                and _nondecreasing_ratio(nums) >= 0.8 and nums[-1] >= 5):
            return True
    return False
