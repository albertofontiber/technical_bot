#!/usr/bin/env python3
"""s93_docmap_fix.py — fixes de datos del diagnóstico s92 (cat013 'CLIP'), por la puerta.

MECÁNICOS (declarados para nod de Alberto en la PR, no adjudicación de mercado):
1. unresolved:id3000 → notifier:id3000 (redirect; evidencia: 106 chunks DB pm=ID3000
   manufacturer=Notifier unánimes + numeración MIDT/MNDT = Notifier).
2. notifier:sdx-751 candidate→false (single-namespace, sin homónimo; el detector óptico
   estrella de cat013/LEVER2_PM_RESCUE — mecánico puro).
3. doc_map: MIDT190 (manual ID3000, SIN entrada) → primary notifier:id3000 +
   secondary notifier:sdx-751 (el juez s85 encontró ahí el soporte 'CLIP' de cat013:
   el protocolo CLIP del SDX-751 se documenta en el manual del panel).

Idempotente; validate al final."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog_store import CATALOG_DIR, FILES, _read_jsonl, load, validate, write_jsonl  # noqa: E402

PROV = "s93-mecanico (diagnostico s92 cat013)"


def main() -> int:
    products = _read_jsonl(CATALOG_DIR / FILES["products"])
    by_id = {r["id"]: r for r in products}

    old = by_id.get("unresolved:id3000")
    if old is None:
        print("[ERROR] unresolved:id3000 no existe")
        return 1
    if "notifier:id3000" not in by_id:
        products.append({"id": "notifier:id3000", "canonical_model": old["canonical_model"],
                         "estado": "activo", "candidate": False, "vendido_bajo": ["Notifier"],
                         "provenance": f"{old['provenance']} | {PROV}: 106 chunks DB "
                                       "pm=ID3000/Notifier unánimes", "added_by": "f1-gt"})
        by_id["notifier:id3000"] = products[-1]
    if old.get("estado") != "redirect":
        old.update(estado="redirect", redirect_to="notifier:id3000", candidate=False)

    sdx = by_id.get("notifier:sdx-751")
    if sdx and sdx.get("candidate"):
        sdx["candidate"] = False
        sdx["provenance"] += f" | {PROV}: promocion mecanica single-namespace"

    dms = _read_jsonl(CATALOG_DIR / FILES["doc_map"])
    if not any(d.get("source_file") == "MIDT190" for d in dms):
        dms.append({"document_id": "s93-midt190-id3000", "source_file": "MIDT190",
                    "entries": [
                        {"id": "notifier:id3000", "role": "primary", "scope": "doc",
                         "provenance": PROV},
                        {"id": "notifier:sdx-751", "role": "secondary", "scope": "doc",
                         "provenance": f"{PROV}: soporte 'CLIP' de cat013 vive aqui (juez s85)"},
                    ]})
        print("[+doc_map] MIDT190")

    # aliases que apunten a unresolved:id3000 → re-apuntar (regla validate alias↔canonical)
    aliases = _read_jsonl(CATALOG_DIR / FILES["aliases"])
    n = 0
    for a in aliases:
        if a.get("id") == "unresolved:id3000":
            a["id"] = "notifier:id3000"
            n += 1
    write_jsonl("aliases", aliases, validate_after=False)
    write_jsonl("products", products, validate_after=False)
    write_jsonl("doc_map", dms, validate_after=False)
    errs = validate()
    if errs:
        for e in errs[:5]:
            print(f"[ERROR] {e}")
        return 1
    cat = load()
    r1, r2 = cat.resolve("ID3000"), cat.resolve("SDX-751")
    print(f"aliases re-apuntados: {n} | ID3000 → {r1 and r1['ids']} | SDX-751 → {r2 and r2['ids']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
