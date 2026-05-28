#!/usr/bin/env python3
"""Post-procesa el artefacto de fix_null_manufacturer (#6) — SIN Haiku ni BD.

Aplica los refinamientos acordados sobre las propuestas crudas de Haiku:
  1. Canonicalizar nombres de marca (FIDEGAS/Fidegas, AVOTEC/Avotec, LGM .../Ltd,
     LDA/LDA audioTech).
  2. Combine con documents.manufacturer (docX): Haiku clava marcas NUEVAS;
     docX clava las 3 legacy cuando la portada no nombra la marca, y refina
     "Honeywell" → marca-hija (Notifier/Morley).
  3. Asignar acción: 'auto' (alta confianza, atribución resuelta) vs 'manual'
     (unknown, baja confianza, o desacuerdo Haiku/docX).
  Software de producto se MANTIENE (se atribuye a su marca, no se excluye).

Escribe logs/null_mfr_refined_<ts>.json (final_manufacturer/final_model/action/
flags) y un resumen. Lo consume luego fix_null_manufacturer.py --apply.

Uso:
    python scripts/refine_null_mfr_review.py [ruta_artefacto.json]
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONF = 0.75
LEGACY3 = {"Notifier", "Morley", "Detnov"}
_SUFFIX = re.compile(r"[\s,]+(ltda?|s\.?\s*l\.?|inc|gmbh|ltd|co)\.?$", re.IGNORECASE)
_ALIASES = {
    "lda": "LDA audioTech",
    "lda audiotech": "LDA audioTech",
    "fidegas": "Fidegas",
    "avotec": "Avotec",
    "lgm products": "LGM Products",
}


def canon_brand(b: str | None) -> str | None:
    if not b:
        return None
    b = b.strip()
    if not b or b.lower() == "unknown":
        return None
    if "," in b:               # malformado tipo "Notifier, Morley"
        return None
    b1 = _SUFFIX.sub("", b).strip()
    return _ALIASES.get(b1.casefold(), b1)


def resolve(p: dict) -> dict:
    haiku = canon_brand(p.get("proposed_manufacturer"))
    conf = p.get("confidence") or 0.0
    docX = canon_brand(p.get("documents_mfr_crosscheck"))

    final, source, flag = None, None, None
    if haiku and haiku not in ("Honeywell",) and haiku not in LEGACY3 and conf >= CONF:
        final, source = haiku, "haiku-new-brand"          # marca nueva: Haiku manda
        if docX and docX != haiku:
            flag = f"docX={docX} (legacy-stale, se ignora)"
    elif haiku == "Honeywell" and docX in {"Notifier", "Morley"}:
        final, source = docX, "honeywell->docX-child"      # refina a marca-hija
    elif (not haiku or conf < CONF):
        if docX in LEGACY3:
            final, source = docX, "docX-rescue"            # 3-legacy sin marca en portada
        else:
            final, source = None, "manual-unknown"
    elif haiku in LEGACY3:
        final, source = haiku, "haiku-legacy"
        if docX and docX in LEGACY3 and docX != haiku:
            flag = f"DESACUERDO Haiku={haiku} docX={docX}"  # revisar
    else:  # Honeywell sin docX-child, etc.
        final, source = haiku, "haiku-other"

    action = "auto" if final and not (flag and "DESACUERDO" in flag) else "manual"
    return {**p, "final_manufacturer": final, "resolve_source": source,
            "resolve_flag": flag, "action": action}


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else max(
        glob.glob(os.path.join(ROOT, "logs", "null_mfr_review_*.json")), key=os.path.getmtime)
    print(f"== refine · {os.path.basename(path)} ==\n")
    proposals = json.load(open(path, encoding="utf-8"))
    refined = [resolve(p) for p in proposals]

    auto = [r for r in refined if r["action"] == "auto"]
    manual = [r for r in refined if r["action"] == "manual"]
    by_final = Counter(r["final_manufacturer"] or "∅(manual)" for r in refined)
    by_source = Counter(r["resolve_source"] for r in refined)
    disagree = [r for r in refined if r.get("resolve_flag") and "DESACUERDO" in r["resolve_flag"]]
    junk_models = [r for r in auto if r.get("current_model_ok") is False]

    print(f"Propuestas: {len(refined)}  |  AUTO: {len(auto)}  MANUAL: {len(manual)}")
    print(f"\nMarca final (tras canonicalizar + docX-combine):")
    for m, n in by_final.most_common():
        print(f"  {m:<22} {n}")
    print(f"\nCómo se resolvió cada una:")
    for s, n in by_source.most_common():
        print(f"  {s:<22} {n}")
    print(f"\nDesacuerdos Haiku/docX (a revisar): {len(disagree)}")
    for r in disagree[:10]:
        print(f"  {r['source_file']:<32} {r['resolve_flag']}")
    print(f"\nAUTO con corrección de product_model (junk→real): {len(junk_models)}")
    print(f"MANUAL (unknown/baja confianza, a tu revisión): {len(manual)}")
    print(f"  muestra 12 manual:")
    for r in sorted(manual, key=lambda x: x.get("confidence") or 0)[:12]:
        print(f"    conf={r.get('confidence')} {r['source_file']:<30} "
              f"haiku={r.get('proposed_manufacturer')} docX={r.get('documents_mfr_crosscheck')} "
              f"model={r.get('proposed_product_model')}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = os.path.join(ROOT, "logs", f"null_mfr_refined_{ts}.json")
    json.dump(refined, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nArtefacto refinado -> {out}")


if __name__ == "__main__":
    main()
