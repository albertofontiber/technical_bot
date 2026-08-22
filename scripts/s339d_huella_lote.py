#!/usr/bin/env python3
"""s339d — huella de detección en el corpus de TODO lo que el lote s339 promueve.

Generaliza `s336g` a un lote entero. La pregunta es la de DEC-272 (NAS: 231→11
documentos): un canónico corto y sin dígitos puede disparar en cientos de documentos
que no son suyos, y entonces promoverlo no rescata un manual — envenena el retrieval.

Dos medidas, y hacen falta las dos:
  · AJENOS  — documentos donde el término dispara y el `doc_map` NO se los asigna.
    Es el riesgo R19: el token está en el texto y eso no lo hace producto de ese doc.
  · ROBO    — de esos ajenos, cuántos tienen HOY un producto consumible propio. Ahí
    el término nuevo no rellena un hueco: compite con un dueño que ya existe (R20).

**`roba_a_dueño` es TRIAGE, no veredicto.** Verificado mirando los contextos reales de este
lote: los conteos altos de `MAD-421`, `MAD-441` y `MAD-473` son CROSS-REFERENCES legítimas
—tablas de consumo, esquemas de conexionado y listas de compatibilidad de la propia Detnov—
y ahí promover es justo lo correcto: el técnico que pregunta por el MAD-441 quiere llegar a
esa tabla. Es el confundidor que DEC-272 ya documentó («el nº de fabricantes marcaba
CROSS-REFERENCES como categorías»). Y en `NAS`, 16 de 20 documentos hablan del producto
(MNDT742/744/747/748, 22-66 apariciones cada uno): lo que el número llamaba «robo» era el
`doc_map` incompleto, no un secuestro.

Así que la cifra ORDENA por dónde mirar; quien decide es el contexto. Un `robo` alto obliga
a abrir los contextos antes de promover — nunca a promover ni a descartar por el número.

Read-only. No escribe catálogo.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

import httpx  # noqa: E402

from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402
from src.rag import catalog_store as cs  # noqa: E402

SB = SUPABASE_URL.rstrip("/") + "/rest/v1"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
PLAN = RAIZ / "evals" / "s339c_plan_lote.json"
SALIDA = RAIZ / "evals" / "s339d_huella_lote.json"


def pagina(tabla: str, params: dict, orden: str = "id") -> list[dict]:
    """Paginar SIN `order` es un bug: PostgREST no garantiza orden estable entre rangos,
    así que la paginación salta y duplica filas. Con `order` es determinista, y se
    comprueba contra el total de `count=exact`."""
    out, off = [], 0
    with httpx.Client(timeout=300) as c:
        r0 = c.get(f"{SB}/{tabla}", headers={**H, "Prefer": "count=exact"},
                   params={**params, "limit": "1"})
        total = int((r0.headers.get("content-range") or "0/0").split("/")[-1] or 0)
        while True:
            r = c.get(f"{SB}/{tabla}", headers={**H, "Range-Unit": "items",
                      "Range": f"{off}-{off + 999}"}, params={**params, "order": orden})
            r.raise_for_status()
            d = r.json()
            out += d
            if len(d) < 1000:
                break
            off += 1000
    if len(out) != total:
        raise SystemExit(f"paginación incompleta en {tabla}: {len(out)} de {total}")
    return out


def core(modelo: str) -> str:
    """Regex separator-insensitive, como `catalog._core`: el corpus escribe «AM-LCD»,
    «AM LCD» y «AM/LCD» para lo mismo, y medir sólo una grafía subestima la huella."""
    tramos = [x for x in re.findall(r"[A-Za-z]+|[0-9]+", modelo) if x]
    return r"[-\s/.+_]*".join(re.escape(t) for t in tramos)


def main() -> int:
    plan = json.loads(PLAN.read_text("utf-8"))
    cat = cs.load()

    # Qué términos entran en juego: el canónico de todo lo que se promueve o se da de alta.
    # Se mide el canónico FINAL, no el de partida: un id que el lote renombra o redirige
    # no deja su nombre viejo en juego, y contarlo inventa un término de riesgo que no
    # existirá (pasó con «VISION PLUS», que el lote convierte en «VSN Plus»).
    renombrado = {o["id"]: o["canonico_nuevo"] for o in plan["operaciones"]
                  if o["op"] == "renombrar_canonico"}
    redirigido = {o["id"] for o in plan["operaciones"] if o["op"] in ("redirect", "eliminar")}
    terminos: dict[str, str] = {}   # término -> id dueño
    for o in plan["operaciones"]:
        if o["op"] == "promover":
            if o["id"] in redirigido:
                continue                     # reenvía: su canónico no queda en juego
            p = cat.products.get(o["id"])
            if p:
                terminos[renombrado.get(o["id"], p["canonical_model"])] = o["id"]
        elif o["op"] == "alta":
            terminos[o["canonical_model"]] = o["id"]
        elif o["op"] == "alias":
            terminos[o["alias"]] = o["id"]

    fuentes: dict[str, set[str]] = defaultdict(set)
    dueno_de_doc: dict[str, list[str]] = defaultdict(list)
    for f in cat.doc_map:
        did = str(f.get("document_id"))
        for e in f.get("entries", []):
            fuentes[str(e.get("id"))].add(did)
            dueno_de_doc[did].append(str(e.get("id")))

    print(f"términos a medir: {len(terminos)}")
    print("bajando chunks …", flush=True)
    ch = pagina("chunks_v2", {"select": "document_id,content"})
    por_doc: dict[str, list[str]] = defaultdict(list)
    for x in ch:
        por_doc[str(x.get("document_id"))].append(x.get("content") or "")
    print(f"  {len(ch)} chunks en {len(por_doc)} documentos\n")

    filas = []
    for term, pid in sorted(terminos.items()):
        rx = re.compile(rf"(?<![a-z0-9]){core(term)}(?![a-z0-9])", re.I)
        hits = {d for d, ts in por_doc.items() if any(rx.search(t or "") for t in ts)}
        suyos = hits & fuentes.get(pid, set())
        ajenos = hits - suyos
        # De los ajenos, ¿cuántos YA tienen dueño consumible? Ahí no se rellena un hueco.
        robo = {d for d in ajenos if any(cat._consumable(i) for i in dueno_de_doc.get(d, []))}
        riesgo = ("ALTO" if len(robo) >= 10 else
                  "MEDIO" if len(robo) >= 3 or len(ajenos) >= 25 else "bajo")
        filas.append({"termino": term, "id": pid, "documentos": len(hits),
                      "suyos": len(suyos), "ajenos": len(ajenos), "roba_a_dueño": len(robo),
                      "riesgo": riesgo,
                      "ejemplos_robo": sorted(robo)[:5]})

    filas.sort(key=lambda f: (-f["roba_a_dueño"], -f["ajenos"]))
    SALIDA.write_text(json.dumps(
        {"corpus": {"chunks": len(ch), "documentos": len(por_doc)}, "filas": filas},
        ensure_ascii=False, indent=1), "utf-8")

    print(f"{'término':<40} {'docs':>5} {'suyos':>6} {'ajenos':>7} {'ROBA':>5}  riesgo")
    print("-" * 78)
    for f in filas:
        marca = {"ALTO": "✗", "MEDIO": "·", "bajo": " "}[f["riesgo"]]
        print(f"{marca}{f['termino'][:39]:<39} {f['documentos']:>5} {f['suyos']:>6} "
              f"{f['ajenos']:>7} {f['roba_a_dueño']:>5}  {f['riesgo']}")
    altos = [f for f in filas if f["riesgo"] == "ALTO"]
    print(f"\n{len(altos)} término(s) en riesgo ALTO"
          + (": " + ", ".join(f["termino"] for f in altos) if altos else ""))
    print("  (ordena por dónde mirar, NO decide: cross-references legítimas puntúan igual "
          "que un secuestro — abre los contextos antes de promover)")
    print(f"→ {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
