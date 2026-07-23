#!/usr/bin/env python3
"""Self-test for the pure (no-DB) logic of scripts/s281_h0t3_retag_packet.py.

Runs standalone ($0, no network): ``python scripts/s281_h0t3_selftest.py``.
Kept in this lane's territory (scripts/s281_h0t3_*). Covers the non-trivial helpers:
the unknown-pm predicate, the SQL-literal escaper, the composite builder (natural
sort + slash-guard + dedup + min-2), and the natural-sort key.
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# import the packet module by path without running main()
spec = importlib.util.spec_from_file_location(
    "s281_h0t3_pkt", ROOT / "scripts" / "s281_h0t3_retag_packet.py")
mod = importlib.util.module_from_spec(spec)
# guard: the module imports src.config/httpx at import-time but does NOT hit the DB
spec.loader.exec_module(mod)

FAILED: list[str] = []


def check(name: str, got, exp) -> None:
    if got != exp:
        FAILED.append(f"{name}: got {got!r} != expected {exp!r}")
    else:
        print(f"  ok  {name}")


def main() -> int:
    # _nk: normalised alnum key
    check("_nk basic", mod._nk("ZX-5 Se"), "zx5se")
    check("_nk none", mod._nk(None), "")

    # _is_unknown_pm
    check("_unknown literal", mod._is_unknown_pm("unknown"), True)
    check("_unknown None", mod._is_unknown_pm(None), True)
    check("_unknown empty", mod._is_unknown_pm("  "), True)
    check("_unknown real", mod._is_unknown_pm("ZXSe"), False)

    # _sql_lit: single-quote escaping
    check("_sql_lit plain", mod._sql_lit("MIE-MI-600"), "'MIE-MI-600'")
    check("_sql_lit quote", mod._sql_lit("d'Alembert"), "'d''Alembert'")

    # _natkey: numeric-aware ordering ZX1<ZX2<ZX5<ZX10
    seq = sorted(["ZX10Se", "ZX1Se", "ZX5Se", "ZX2Se"], key=mod._natkey)
    check("_natkey order", seq, ["ZX1Se", "ZX2Se", "ZX5Se", "ZX10Se"])

    # _composite_from: natural-sorted, deduped, min-2 model-shaped tokens
    check("composite zxse order",
          mod._composite_from(["ZX10Se", "ZX1Se", "ZX2Se", "ZX5Se"]),
          "ZX1Se/ZX2Se/ZX5Se/ZX10Se")
    check("composite dedup",
          mod._composite_from(["ZX2e", "ZX2e", "ZX5e"]), "ZX2e/ZX5e")
    # slash-guard: any model containing '/' -> ambiguous -> None
    check("composite slash-guard",
          mod._composite_from(["S/2-T1", "S/3-T1"]), None)
    check("composite slash-guard2",
          mod._composite_from(["NX2/R/R", "NX5/R/R"]), None)
    # min-2 clean tokens required
    check("composite single->None", mod._composite_from(["NSRE24"]), None)
    # non-model-shaped (no digit) dropped -> below min-2 -> None
    check("composite descriptive->None",
          mod._composite_from(["Central convencional", "Panel"]), None)

    if FAILED:
        print("\nFAILED:")
        for f in FAILED:
            print("  -", f)
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
