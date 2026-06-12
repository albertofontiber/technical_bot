"""s67 — verificación de la VENTANA del GO (X2) + freeze del instrumento (X1, dúo r1).

El GO del re-gate CE (s66, DEC-047) vale mientras los fingerprints materiales sean
IDÉNTICOS a los del gate (`s66_gate_pools.json:meta`, copiados a
`s66_gate_report.yaml:meta`): corpus_fingerprint (con lifecycle) + registry_fingerprint
+ pg_proc.proconfig/SHA de las RPCs + config retrieval. CUALQUIER drift material →
re-gate (~$5-6) ANTES de pagar el A/B.

X1 (cross-model r1 s67): el exit-0 de este script no puede coexistir con instrumento
drifteado — además de la DB verifica el CÓDIGO material (modelos CE/LLM, retriever,
generador, juez, gold_store): working tree LIMPIO en esos paths + `git diff
<code-baseline>..HEAD` VACÍO sobre ellos. La baseline es el commit del BUILD del A/B
(`--code-baseline`; falla-CERRADO si falta — verificar a ciegas es peor que abortar).

Sesión DB readonly — cero escritura. Exit code 0 = ventana VIGENTE, 1 = DRIFT.
"""
from __future__ import annotations

import os

# chunks_v2 + HyDE OFF (= paridad harness/prod) ANTES de importar config/retriever.
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
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

# Paths cuyo drift invalida la ventana (X1): retrieval/rerank/generación/juez/puerta.
CODE_PATHS = ["src/", "config/", "scripts/bvg_kmajority.py", "scripts/test_bot_vs_gold.py",
              "scripts/gold_store.py", "scripts/strict_match.py", "requirements.txt"]


def _git(*a: str) -> str:
    import subprocess
    r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"git {' '.join(a)} falló: {r.stderr.strip()[:200]}"
    return r.stdout.strip()


def check_code(baseline: str | None) -> list[str]:
    """X1: instrumento congelado. Devuelve lista de drifts (vacía = OK)."""
    drifts = []
    dirty = _git("status", "--porcelain", "--", *CODE_PATHS)
    if dirty:
        drifts.append(f"working tree SUCIO en paths materiales:\n{dirty}")
    if baseline is None:
        drifts.append("--code-baseline ausente (falla-CERRADO): pasa el sha del commit "
                      "del build del A/B")
        return drifts
    diff = _git("diff", "--stat", f"{baseline}..HEAD", "--", *CODE_PATHS)
    if diff:
        drifts.append(f"código material cambió desde {baseline}:\n{diff}")
    return drifts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-baseline", default=None,
                    help="sha del commit del build del A/B (X1; falla-cerrado si falta)")
    ap.add_argument("--db-only", action="store_true",
                    help="solo X2-DB (modo pre-build, sin check de código)")
    args = ap.parse_args()

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

    code_drifts = [] if args.db_only else check_code(args.code_baseline)
    for d in code_drifts:
        print(f"DRIFT  codigo (X1): {d}")

    print()
    if drift or code_drifts:
        print(f"VENTANA X2/X1: DRIFT en {drift + (['codigo'] if code_drifts else [])} "
              f"-> re-gate (~$5-6) / re-build ANTES del A/B (diseño s66 §3-v4 + X1 r1-s67)")
        return 1
    modo = "X2-DB (sin codigo, --db-only)" if args.db_only else "X2+X1"
    print(f"VENTANA {modo}: VIGENTE (gate git={gate_meta['git']} at={gate_meta['at']}) "
          f"-> el GO habilita el A/B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
