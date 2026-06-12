"""s67 — verificación de la VENTANA del GO (X2, diseño s66 §3-v4).

El GO del re-gate CE (s66, DEC-047) vale mientras los fingerprints materiales sean
IDÉNTICOS a los del gate (`s66_gate_pools.json:meta`, copiados a
`s66_gate_report.yaml:meta`): corpus_fingerprint (con lifecycle) + registry_fingerprint
+ pg_proc.proconfig/SHA de las RPCs + config retrieval. El modelo CE y el modelo
LLM-rerank viven en código → los cubre `git diff <gate>..HEAD -- src/ scripts/ config/`
(debe ser vacío), no este script. CUALQUIER drift material → re-gate (~$5-6) ANTES de
pagar el A/B.

Sesión DB readonly — cero escritura. Exit code 0 = ventana VIGENTE, 1 = DRIFT.
"""
from __future__ import annotations

import os

# chunks_v2 + HyDE OFF (= paridad harness/prod) ANTES de importar config/retriever.
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import json
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import psycopg2  # noqa: E402
from bvg_kmajority import corpus_fingerprint  # noqa: E402
from s59_gate1 import db_state  # noqa: E402
from src.config import CHUNKS_TABLE, RETRIEVAL_TOP_K  # noqa: E402
from src.rag.series_registry import registry_fingerprint, series_enabled  # noqa: E402


def main() -> int:
    gate_meta = json.loads((ROOT / "evals" / "s66_gate_pools.json")
                           .read_text(encoding="utf-8"))["meta"]

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True)
    conn.autocommit = True
    state = db_state(conn.cursor())
    conn.close()

    hoy = {
        "db_state": state,
        "corpus_fingerprint": corpus_fingerprint(),
        "registry_fingerprint": registry_fingerprint(),
        "series_enabled": series_enabled(),
        "retrieve_k": RETRIEVAL_TOP_K,
        "hyde": os.environ.get("HYDE_ENABLED"),
        "chunks_table": CHUNKS_TABLE,
    }
    gate = {k: gate_meta[k] for k in
            ("db_state", "corpus_fingerprint", "registry_fingerprint",
             "series_enabled", "retrieve_k", "hyde")}
    gate["chunks_table"] = "chunks_v2"

    drift = []
    for k in gate:
        if hoy[k] == gate[k]:
            print(f"OK     {k}")
        else:
            drift.append(k)
            print(f"DRIFT  {k}")
            print(f"       gate: {yaml.safe_dump(gate[k], allow_unicode=True, default_flow_style=True).strip()}")
            print(f"       hoy : {yaml.safe_dump(hoy[k], allow_unicode=True, default_flow_style=True).strip()}")

    print()
    if drift:
        print(f"VENTANA X2: DRIFT en {drift} -> re-gate (~$5-6) ANTES del A/B (diseño s66 §3-v4)")
        return 1
    print(f"VENTANA X2: VIGENTE (gate git={gate_meta['git']} at={gate_meta['at']}) -> el GO habilita el A/B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
