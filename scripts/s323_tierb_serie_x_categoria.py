# -*- coding: utf-8 -*-
"""s323 — REHACE el §0.B con la regla SERIE x CATEGORIA (adjudicado por Alberto).

Historia del criterio, en tres intentos:
 1. La pasada original asignaba los ids que salian de la ETIQUETA de los chunks: para
    la guia de la serie 2X-A, 2 productos de los 40 que tenemos. Arbitrario — el
    documento no nombra ni un modelo (lo cazo Alberto).
 2. Mi propuesta de mapear al PARAGUAS de serie: mejor, pero al construirlo se vio que
    2X-A son 39 miembros en 4 subfamilias con interfaces DISTINTAS (teclado, tactil,
    repetidor, evacuacion). Una guia de funcionamiento describe UNA interfaz.
 3. La regla que se aplica aqui: un documento de serie pertenece a la INTERSECCION
    serie x tipo de producto que documenta. "Centrales de la serie NC", no "la serie NC".
    Usa la categoria de #76, que ya existe poblada para Kidde y Detnov.

NO APLICA NADA: emite el §0.B rehecho, partido en LIMPIAS y PIDEN-TU-OJO, con hueco de
decision bajo cada fila.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl

products = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}
rec = json.loads((ROOT / "evals" / "s322f_e1s2_tierb_docmap_v1.json").read_text(encoding="utf-8"))
filas = rec.get("seccion_0_bloque", [])

# categoria que el documento DECLARA en su cita ("centrales de incendio ..." -> central)
CAT_EN_CITA = [("central", r"\bcentral(es)?\b|\bpanel(es)?\b|\bcontrol panel"),
               ("pulsador", r"\bpulsador(es)?\b|\bcall point"),
               ("sirena", r"\bsirena(s)?\b|\bsounder"),
               ("detector", r"\bdetector(es)?\b"),
               ("repetidor", r"\brepetidor(es)?\b|\brepeater")]
RX_SERIE = re.compile(r"\bserie[s]?\s+([A-Z0-9][A-Z0-9\-]{1,10})", re.I)


def _serie_de(texto: str) -> str | None:
    m = RX_SERIE.search(texto or "")
    return m.group(1).upper().rstrip(".,;") if m else None


def _categoria_de(texto: str) -> str | None:
    t = (texto or "").lower()
    for cat, pat in CAT_EN_CITA:
        if re.search(pat, t):
            return cat
    return None


limpias, ojo = [], []
for f in filas:
    cita = ((f.get("llm") or {}).get("cita") or "")
    serie = _serie_de(cita)
    cat = _categoria_de(cita)
    ids_prop = list(f.get("ids_propuestos") or (f.get("llm") or {}).get("ids_propuestos") or [])
    fila = {"documento": f.get("source_file"), "cita": cita[:120],
            "ids_originales": ids_prop, "serie": serie, "categoria_declarada": cat}
    if serie:
        rx = re.compile(rf"^{re.escape(serie)}[-A-Z0-9]*$", re.I)
        miembros = [pid for pid, p in products.items()
                    if rx.match(p.get("canonical_model") or "")
                    and p.get("estado") == "activo" and not p.get("candidate")
                    and (cat is None
                         or (p.get("clasificacion") or {}).get("categoria") == cat)]
        fila["ids_por_serie_x_categoria"] = sorted(miembros)
        fila["motivo"] = (f"documento de SERIE {serie}"
                          + (f" x categoria {cat}" if cat else " (categoria NO declarada)"))
        # sin categoria declarada, o sin miembros, decide Alberto
        (ojo if (cat is None or not miembros) else limpias).append(fila)
    else:
        fila["motivo"] = "documento de producto (no de serie): asignacion original"
        limpias.append(fila)

salida = {"que_es": __doc__.strip().splitlines()[0],
          "regla": "serie x categoria; sin categoria declarada -> decide Alberto",
          "limpias": limpias, "piden_tu_ojo": ojo}
(ROOT / "evals" / "s323_tierb_v3_serie_x_categoria.json").write_text(
    json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"§0.B rehecho: {len(limpias)} limpias · {len(ojo)} piden tu ojo")
for f in ojo[:8]:
    print(f"   OJO  {f['documento'][:46]:<46} {f['motivo']}")
for f in limpias:
    if f.get("ids_por_serie_x_categoria"):
        print(f"   SERIE {f['documento'][:44]:<44} {f['serie']}x{f['categoria_declarada']} "
              f"-> {len(f['ids_por_serie_x_categoria'])} ids (antes {len(f['ids_originales'])})")
