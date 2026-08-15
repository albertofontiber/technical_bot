# -*- coding: utf-8 -*-
"""s323 fase C — runner GOBERNADO de la etapa B: ejecuta el pipeline con el gate
de identidad inyectado.

Existe porque `src/reingest` no puede importar `src/rag` (contrato de imports) y,
sin embargo, el gate NO puede depender de que alguien se acuerde de lanzarlo: la
dependencia entra por INYECCION desde esta capa, que sí puede ver ambas.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

from src.rag.identidad_gate import evaluar  # noqa: E402
from src.reingest.pipeline import DEFAULT_CONFIG, run  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Etapa B con gate de identidad (s323 fase C)")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    run(a.config, a.limit, a.dry_run, a.reset, gate=evaluar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
