#!/usr/bin/env python3
"""s334 — EVIDENCIA para desbloquear MANUALES HUÉRFANOS promoviendo sus candidates.

EL REENCUADRE ES DE ALBERTO (21-ago) y es el correcto: «lo mejor creo que es
enfocarlo desde el punto de vista de manuales huérfanos». Un candidate suelto no
le sirve a nadie; **un manual que no puede servir a nadie es una pérdida
contable**. Hay 245 huérfanos — documentos con fila de `doc_map` cuyos ids son
TODOS no consumibles, así que el bot no los alcanza por catálogo.

QUÉ HACE ESTE SCRIPT. Para cada huérfano, mira sus candidates y separa los que se
pueden promover con seguridad de los que no, y **para cada uno extrae la CITA
VERIFICADA de su propio documento** — que es lo que R4 exige y lo que el «el
token aparece» de la clase A todavía no era. Sin cita no entra en el lote.

LAS CLASES, y por qué cada una:
  A — nombrado, con marca resuelta y token distintivo: candidato a promoción.
  B — acrónimo corto sin dígitos: riesgo léxico REAL (`VIEW` sale 1.648 veces en
      el corpus porque es una palabra inglesa). Fuera del lote autónomo.
  C — `unresolved:`: sin marca. Asignar fabricante es ADJUDICACIÓN, no mecánica.
  D — código de norma (R14): jamás es un producto; se retira, no se promueve.
  E — su nombre no está en el texto de su propio documento (sonda s334): sin cita
      posible, fuera por construcción.
  F — el huérfano no tiene candidates: sus ids están retirados o son redirect.
      Promover no lo arregla; es otro problema y se lista aparte.

LO QUE NO HACE: escribir. Produce el fichero de evidencia que alimenta el plan
del lote firmado, que a su vez pasa por dry-run + censo del radio de explosión +
dúo antes de `--aplicar`.

Uso:  python scripts/s334_huerfanos_evidencia.py [--marca notifier]
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
SALIDA = ROOT / "evals/s334_huerfanos_evidencia_v1.json"

#: Códigos de normativa. R14: una norma JAMÁS es un producto.
NORMA = re.compile(r"^(EN\s?-?5?4|NFS?[\s-]?32|BS\s?5839|ISO\s?8201|AS\s?2220|UL\s?\d|VdS)", re.I)
#: Cota de la cita, igual que el resto del repo.
CITA_MAX = 200


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _paginado(c: httpx.Client, tabla: str, params: dict) -> list[dict]:
    out, off = [], 0
    while True:
        p = dict(params)
        p.update({"limit": "1000", "offset": str(off)})
        r = c.get(f"{SUPABASE_URL}/rest/v1/{tabla}", headers=H, params=p)
        r.raise_for_status()
        pag = r.json()
        out += pag
        if len(pag) < 1000:
            return out
        off += 1000


def cita_de(texto: str, token: str) -> str | None:
    """La frase del documento donde aparece el token, recortada a `CITA_MAX`.

    Busca con FRONTERA DE PALABRA sobre el texto original (no normalizado) para
    que la cita sea copiable y verificable a ojo. Si el token sólo aparece
    pegado a otra cosa —dentro de una palabra más larga— NO devuelve cita: eso
    es justo la «sospecha de prefijo» que el packet marcaba, y sin cita limpia
    la fila no entra en el lote."""
    if not texto or not token:
        return None
    pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", re.I)
    m = pat.search(texto)
    if not m:
        return None
    ini = max(0, m.start() - CITA_MAX // 2)
    fin = min(len(texto), m.end() + CITA_MAX // 2)
    return re.sub(r"\s+", " ", texto[ini:fin]).strip()


def main() -> int:
    marca_filtro = (sys.argv[sys.argv.index("--marca") + 1]
                    if "--marca" in sys.argv else None)

    prod = {p["id"]: p for p in (json.loads(l) for l in
            (ROOT / "data/catalog/products.jsonl").read_text("utf-8").splitlines() if l.strip())}
    dm = [json.loads(l) for l in (ROOT / "data/catalog/doc_map.jsonl")
          .read_text("utf-8").splitlines() if l.strip()]

    def consumible(pid: str) -> bool:
        p = prod.get(pid)
        return bool(p) and p.get("estado") == "activo" and not p.get("candidate")

    huerfanos = []
    for fila in dm:
        ids = [e["id"] for e in fila.get("entries", []) if e.get("id") in prod]
        if ids and not any(consumible(i) for i in ids):
            huerfanos.append((str(fila.get("source_file") or ""), ids))
    print(f"manuales huérfanos: {len(huerfanos)}")

    # el texto de cada documento huérfano, UNA vez
    docs = sorted({sf for sf, _ in huerfanos})
    print(f"leyendo el texto de {len(docs)} documentos…")
    texto: dict[str, str] = {}
    with httpx.Client(timeout=90) as c:
        for i, sf in enumerate(docs, 1):
            filas = _paginado(c, "chunks_v2", {"select": "content", "source_file": f"eq.{sf}"})
            texto[sf] = " ".join(str(f.get("content") or "") for f in filas)
            if i % 40 == 0:
                print(f"  …{i}/{len(docs)}", flush=True)

    def clase(pid: str, sf: str) -> str:
        p = prod[pid]
        tok = p["canonical_model"]
        if NORMA.match(tok):
            return "D"
        if pid.startswith("unresolved:"):
            return "C"
        if len(tok) <= 4 and not any(ch.isdigit() for ch in tok):
            return "B"
        return "A" if cita_de(texto.get(sf, ""), tok) else "E"

    listos, por_clase, sin_candidates = defaultdict(list), defaultdict(int), []
    for sf, ids in huerfanos:
        cands = [i for i in ids if prod[i].get("candidate")]
        if not cands:
            sin_candidates.append(sf)
            por_clase["F"] += 1
            continue
        mejores = []
        for pid in cands:
            cl = clase(pid, sf)
            por_clase[cl] += 1
            if cl != "A":
                continue
            tok = prod[pid]["canonical_model"]
            cuerpo = texto.get(sf, "")
            mejores.append({
                "id": pid,
                "canonico": tok,
                "marca": pid.split(":", 1)[0],
                "cita": cita_de(cuerpo, tok),
                "menciones_en_su_doc": len(re.findall(
                    rf"(?<![A-Za-z0-9]){re.escape(tok)}(?![A-Za-z0-9])", cuerpo, re.I)),
            })
        if mejores:
            listos[sf] = mejores

    print("\n=== CANDIDATES DE LOS HUÉRFANOS, POR CLASE ===")
    etiquetas = {"A": "nombrado + marca + CITA verificada → promovible",
                 "B": "acrónimo corto (riesgo léxico) → fuera del lote autónomo",
                 "C": "sin marca (`unresolved:`) → adjudicación, no mecánica",
                 "D": "código de NORMA (R14) → retirar, nunca promover",
                 "E": "sin cita limpia en su propio documento → fuera",
                 "F": "el huérfano no tiene candidates (ids retirados/redirect)"}
    for k in "ABCDEF":
        if por_clase.get(k):
            print(f"  {k}: {por_clase[k]:4d}  {etiquetas[k]}")

    por_marca = defaultdict(lambda: {"manuales": set(), "ids": []})
    for sf, ms in listos.items():
        for m in ms:
            por_marca[m["marca"]]["manuales"].add(sf)
            por_marca[m["marca"]]["ids"].append(m)

    print(f"\n=== LOTES POR FABRICANTE (clase A, con cita) ===")
    print(f"  manuales que se desbloquean: {len(listos)}")
    for marca, d in sorted(por_marca.items(), key=lambda x: -len(x[1]["manuales"])):
        print(f"    {marca:16s} {len(d['manuales']):3d} manuales · {len(d['ids']):3d} ids")

    salida = {
        "que_es": "Evidencia para desbloquear manuales huérfanos promoviendo sus candidates de "
                  "clase A (nombrado, con marca y CON CITA verificada en su propio documento). "
                  "NADA aplicado: alimenta el plan del lote firmado.",
        "reencuadre": "Alberto, 21-ago: la unidad es el MANUAL huérfano, no el candidate suelto.",
        "resumen": {"huerfanos": len(huerfanos), "desbloqueables_clase_A": len(listos),
                    "por_clase": dict(por_clase),
                    "por_marca": {k: {"manuales": len(v["manuales"]), "ids": len(v["ids"])}
                                  for k, v in por_marca.items()}},
        "lotes": {marca: {"manuales": sorted(d["manuales"]), "ids": d["ids"]}
                  for marca, d in por_marca.items()
                  if not marca_filtro or marca == marca_filtro},
        "sin_candidates": sin_candidates,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
