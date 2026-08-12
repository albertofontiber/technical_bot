# -*- coding: utf-8 -*-
"""s320 E1b — Pre-clasificación de los 620 candidates para QA TOTAL por lotes.

Cobertura 620/620 (r21: no muestras). La atestación va contra CONTENIDO de
chunks (r22: nunca contra el pm/metadata del que un candidato pudo nacer —
estos 620 vienen del bulk s83/s91, pero la regla se aplica igual por diseño).

Lotes (ordenan la sentada, NO deciden):
- «confirmar»: atestado en contenido (≥N chunks lo mencionan) y sin señal de
  veneno → probable consumible.
- «retirar»: veneno léxico (corto/dígitos/palabra común) y 0 atestación.
- «revisar»: el resto, con su conteo.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
CAT = ROOT / "data" / "catalog"

_VENENO = re.compile(r"^\d{1,4}$|^[a-z]{1,2}$|^(fire|alarm|panel|zona|zone|"
                     r"loop|led|usb|pcb|din|ip|tcp|abs)$", re.IGNORECASE)


def _pdf_escape(term: str) -> str:
    return term.replace("%", r"\%").replace("_", r"\_").replace("*", "")


def main() -> int:
    productos = [json.loads(l) for l in
                 (CAT / "products.jsonl").read_text(encoding="utf-8")
                 .splitlines() if l.strip()]
    candidates = [p for p in productos if p.get("candidate")]

    lotes = {"confirmar": [], "retirar": [], "revisar": []}
    with abierto(timeout=20.0) as client:
        for i, p in enumerate(candidates):
            modelo = (p.get("canonical_model") or "").strip()
            veneno = bool(_VENENO.match(modelo)) or len(modelo) < 3
            n_chunks = 0
            if modelo:
                r = client.get(
                    f"{SUPABASE_URL}/rest/v1/chunks_v2",
                    headers={**H, "Prefer": "count=exact", "Range": "0-0"},
                    params={"select": "id",
                            "content": f"ilike.*{_pdf_escape(modelo)}*"})
                if r.status_code in (200, 206):
                    n_chunks = int(r.headers.get("content-range", "/0")
                                   .split("/")[-1])
            fila = {"id": p.get("id"), "modelo": modelo,
                    "chunks_con_mencion": n_chunks, "veneno_lexico": veneno}
            if veneno and n_chunks == 0:
                lotes["retirar"].append(fila)
            elif not veneno and n_chunks >= 3:
                lotes["confirmar"].append(fila)
            else:
                lotes["revisar"].append(fila)
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(candidates)}…", flush=True)

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recibo = {
        "que_es": ("E1b: pre-clasificación de candidates para QA TOTAL "
                   "(620/620). Atestación = COUNT de chunks cuyo CONTENIDO "
                   "menciona el modelo (nunca metadata). Los lotes ordenan, "
                   "la decisión es de Alberto."),
        "utc": utc, "total": len(candidates),
        "lotes": {k: len(v) for k, v in lotes.items()},
        "detalle": lotes,
    }
    destino = ROOT / "evals" / "s320_e1b_candidates_preclasificacion_v1.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"total {len(candidates)} · confirmar {len(lotes['confirmar'])} · "
          f"retirar {len(lotes['retirar'])} · revisar {len(lotes['revisar'])}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
