#!/usr/bin/env python3
"""s334 — G4-B: verificación AISLADA, par a par (id × su manual huérfano CONCRETO).

POR QUÉ EXISTE. La G4 original tenía dos confundidores que el dúo r42 (Sol #2)
señaló y que son reales:
  1. agrupaba TODOS los `source_file` del id y daba por bueno el desbloqueo si
     aparecía **cualquiera** — el crédito podía venir de un manual del mismo id
     que ni siquiera era huérfano;
  2. promovía los 110 candidates **a la vez**, así que un id cuyo canónico se
     detecta como el término de OTRO id del lote recibía crédito ajeno.

Aquí se cierra por construcción: para cada par (id, manual huérfano DE ESE id) se
promueve **sólo ese id** sobre una copia limpia del catálogo y se exige que
`resolve_query(canónico)` traiga **ese `source_file` concreto**.

Uso:  python scripts/s334_huerfanos_g4b.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"      # el brazo de producción

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.rag import catalog_store as cs                            # noqa: E402
from src.rag import catalog_resolver as R                          # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, FILES               # noqa: E402

SALIDA = ROOT / "evals/s334_huerfanos_g4b_v1.json"
LOTES = ("pequenos", "notifier")


def main() -> int:
    prod = {}
    for l in (ROOT / "data/catalog/products.jsonl").read_text("utf-8").splitlines():
        if l.strip():
            p = json.loads(l)
            prod[p["id"]] = p
    dm = [json.loads(l) for l in (ROOT / "data/catalog/doc_map.jsonl")
          .read_text("utf-8").splitlines() if l.strip()]

    def consumible(pid: str) -> bool:
        p = prod.get(pid)
        return bool(p) and p.get("estado") == "activo" and not p.get("candidate")

    huerf: dict[str, list[str]] = {}
    for f in dm:
        ids = [e["id"] for e in f.get("entries", []) if e["id"] in prod]
        if ids and not any(consumible(i) for i in ids):
            huerf[str(f.get("source_file") or "")] = ids

    lote = [c for n in LOTES for c in json.loads(
        (ROOT / f"evals/s334_huerfanos_lote_{n}_plan.json").read_text("utf-8"))["products_confirmar"]]
    pares = [(c["id"], c["canonical_model"], sf)
             for c in lote for sf, ids in huerf.items() if c["id"] in ids]
    print(f"pares (id × manual huérfano suyo): {len(pares)}  ·  ids: {len({p[0] for p in pares})}"
          f"  ·  manuales: {len({p[2] for p in pares})}")

    orig = cs.load
    base = Path(tempfile.mkdtemp())
    cache: dict[str, set[str]] = {}
    ok, ko = [], []
    try:
        for i, (pid, canon, sf) in enumerate(pares, 1):
            if pid not in cache:
                d = base / f"c{i}"
                d.mkdir()
                for _, fn in FILES.items():
                    if (CATALOG_DIR / fn).exists():
                        shutil.copy(CATALOG_DIR / fn, d / fn)
                ruta = d / FILES["products"]
                filas = [json.loads(l) for l in ruta.read_text("utf-8").splitlines() if l.strip()]
                for p in filas:
                    if p["id"] == pid:
                        p["candidate"] = False
                ruta.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in filas), "utf-8")
                cs.load = lambda *a, _d=d, **k: orig(_d)
                R._loaded = False
                R._pattern = None
                R._build()
                cache[pid] = set(R.resolve_query(canon)["allowed_sources"])
                shutil.rmtree(d)
            (ok if sf in cache[pid] else ko).append({"id": pid, "canonico": canon, "manual": sf})
            if i % 25 == 0:
                print(f"  …{i}/{len(pares)}", flush=True)
    finally:
        cs.load = orig
        R._loaded = False
        R._pattern = None

    print("\n=== G4-B (aislado, por manual huérfano concreto) ===")
    print(f"  el manual huérfano SÍ llega .... {len(ok)}")
    print(f"  NO llega ....................... {len(ko)}")
    for k in ko:
        print("     ", k)
    manuales = sorted({r["manual"] for r in ok})
    print(f"\n  ids con al menos 1 manual desbloqueado: {len({r['id'] for r in ok})}")
    print(f"  MANUALES realmente desbloqueados ....: {len(manuales)}")
    print(f"  huérfanos: {len(huerf)} → {len(huerf) - len(manuales)}")

    SALIDA.write_text(json.dumps(
        {"que_es": "G4-B: verificación AISLADA por (id × su manual huérfano concreto), bajo la "
                   "política de producción (`replace`). Cierra los dos confundidores que el dúo "
                   "r42 encontró en la G4 original. NADA aplicado.",
         "pares": len(pares), "llega": len(ok), "no_llega": len(ko),
         "huerfanos_antes": len(huerf), "huerfanos_despues": len(huerf) - len(manuales),
         "ids_con_desbloqueo": sorted({r["id"] for r in ok}),
         "manuales_desbloqueados": manuales,
         "fallos": ko}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
