# -*- coding: utf-8 -*-
"""s336 B2 — Muestra determinista del mini-GT (30) + volcado de TEXTO COMPLETO.

Cuotas (v3 §1.7, Fable2-2): ≥1 por namespace presente en la diana; el resto a
notifier repartido por estratos de nº-docs. Selección DETERMINISTA (orden por
sha256(id) dentro de cada estrato — reproducible, sin Date/random).

El volcado trae TODOS los chunks de cada doc del producto (v3 §1.7, Sol2-5: el
GT no puede leer la misma ventana de 2 chunks que consume la pasada) y marca las
secciones R9 (enumeración) para navegar. Los ficheros van al scratchpad de la
sesión (lectura mía); el GT etiquetado a mano se escribe aparte en
evals/s336_gt_v1.yaml y se congela con SHA antes de la pasada.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "evals" / "s336_gt_dump"

CUOTAS_MIN = {"ada": 1, "firelite": 2, "kac": 1, "morley": 1, "pepperl-fuchs": 1,
              "sensitron": 1, "spectrex": 2, "systemsensor": 2}
TOTAL = 30
_RX_R9 = re.compile(
    r"descripci[oó]n general|\bmodelos\b|\bmodels\b|ordering information|"
    r"informaci[oó]n de pedido|referencias|\bgama\b|\bversiones\b", re.IGNORECASE)


def _orden(pid: str) -> str:
    return hashlib.sha256(pid.encode()).hexdigest()


def main() -> int:
    censo = json.loads((ROOT / "evals" / "s336_censo_diana_v1.json")
                       .read_text(encoding="utf-8"))["detalle"]
    por_ns = defaultdict(list)
    for d in censo:
        por_ns[d["marca"]].append(d)
    for xs in por_ns.values():
        xs.sort(key=lambda d: _orden(d["id"]))

    muestra = []
    for ns, n in CUOTAS_MIN.items():
        muestra.extend(por_ns.get(ns, [])[:n])
    resto = TOTAL - len(muestra)
    noti = por_ns["notifier"]
    # estratos nº-docs dentro de notifier: 1 doc / 2-3 / 4+ — reparto 8/6/5
    e1 = [d for d in noti if d["n_docs"] == 1]
    e2 = [d for d in noti if 2 <= d["n_docs"] <= 3]
    e3 = [d for d in noti if d["n_docs"] >= 4]
    for grupo, k in ((e1, 8), (e2, 6), (e3, 5)):
        muestra.extend(grupo[:k])
    muestra = muestra[:TOTAL]
    assert len(muestra) == TOTAL, len(muestra)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    esqueleto = []
    with abierto(timeout=45.0) as c:
        for i, d in enumerate(muestra, 1):
            partes = [f"# {d['id']} · canonical={d['canonical_model']!r} · "
                      f"pista_legacy={d['pista_legacy']!r} · n_docs={d['n_docs']}"]
            for sf in d["docs"]:
                filas, offset = [], 0
                while True:
                    r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                              params={"select": "chunk_index,content",
                                      "source_file": f"eq.{sf}",
                                      "order": "chunk_index.asc",
                                      "limit": "100", "offset": str(offset)})
                    r.raise_for_status()
                    lote = r.json()
                    filas.extend(lote)
                    if len(lote) < 100:
                        break
                    offset += 100
                texto = "\n".join((x.get("content") or "") for x in filas)
                marcas_r9 = sorted({m.group(0).lower()
                                    for m in _RX_R9.finditer(texto)})
                partes.append(f"\n\n===== DOC {sf} · {len(filas)} chunks · "
                              f"secciones-R9: {marcas_r9 or 'NINGUNA'} =====\n{texto}")
            destino = OUT_DIR / f"{i:02d}_{d['id'].replace(':', '__')}.txt"
            destino.write_text("\n".join(partes), encoding="utf-8")
            esqueleto.append({"id": d["id"], "categoria": "PENDIENTE",
                              "profundidad_lectura": "PENDIENTE", "duda": False})
            print(f"  [{i:2d}/30] {d['id']} · {d['n_docs']} docs → {destino.name}")

    (OUT_DIR / "_esqueleto_gt.json").write_text(
        json.dumps(esqueleto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nvolcado → {OUT_DIR} (el GT etiquetado va a evals/s336_gt_v1.yaml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
