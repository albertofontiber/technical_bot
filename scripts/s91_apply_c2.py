#!/usr/bin/env python3
"""s91_apply_c2.py — aplica las 6 filas del packet C2 CONFIRMADAS por Alberto en sesión s91
(evals/s91_c2_brands_packet.md v3): MAD-481→detnov · ENScape→kac · NSRE24→ada (OEM al píxel:
'ADA Componentes Electrónicos, S.L.') · FS8→notifier (sin productos) · COELBO→coelbo ·
WR2001/D391→kac. Las 12 filas restantes del packet SIGUEN pendientes de marca (no se tocan).

Patrón: id INMUTABLE → el unresolved:* pasa a redirect → producto nuevo namespaced (gt,
candidate=false). doc_map no se toca (los consumidores siguen redirects). Idempotente."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog_store import CATALOG_DIR, FILES, _read_jsonl, load, validate, write_jsonl  # noqa: E402

PROV = "gt-s91-alberto-c2"

# unresolved_id -> (namespace nuevo, vendido_bajo)
VB = {
    "detnov": ["Detnov", "Golmar"],
    "kac": ["KAC"],
    "ada": ["ADA Componentes Electronicos", "Notifier"],
    "coelbo": ["COELBO", "Notifier (It)"],
}
MOVES = {
    "unresolved:mad-481": "detnov",
    "unresolved:cwss-xx-s5": "kac", "unresolved:cwss-xx-s6": "kac",
    "unresolved:cwss-xx-w5": "kac", "unresolved:cwss-xx-w6": "kac",
    "unresolved:2001": "kac", "unresolved:2004": "kac", "unresolved:2061": "kac",
    "unresolved:2072": "kac", "unresolved:2101": "kac",
    "unresolved:wr2001": "kac", "unresolved:ww2001": "kac",
    "unresolved:nsre24": "ada", "unresolved:estela-1": "ada", "unresolved:estela-2": "ada",
    "unresolved:efd1": "coelbo", "unresolved:efd2": "coelbo",
    "unresolved:efd3": "coelbo", "unresolved:efd4": "coelbo",
}


def main() -> int:
    products = _read_jsonl(CATALOG_DIR / FILES["products"])
    by_id = {r["id"]: r for r in products}
    n_new = n_redir = 0
    for old_id, ns in MOVES.items():
        old = by_id.get(old_id)
        if old is None:
            print(f"[ERROR] no existe {old_id}")
            return 1
        new_id = f"{ns}:{old_id.split(':', 1)[1]}"
        if new_id not in by_id:
            row = {"id": new_id, "canonical_model": old["canonical_model"],
                   "estado": "activo", "candidate": False, "vendido_bajo": VB[ns],
                   "provenance": f"{old['provenance']} | {PROV}", "added_by": "f1-gt"}
            products.append(row)
            by_id[new_id] = row
            n_new += 1
        if old.get("estado") != "redirect":
            old["estado"] = "redirect"
            old["redirect_to"] = new_id
            old["candidate"] = False
            if PROV not in old.get("provenance", ""):
                old["provenance"] = f"{old['provenance']} | {PROV}"
            n_redir += 1
    # alias de ids movidos → re-apuntar al id nuevo (la regla alias↔canonical del validate
    # no sigue redirects — la 1ª pasada de este script lo cazó con 'EFD 1..4')
    aliases = _read_jsonl(CATALOG_DIR / FILES["aliases"])
    n_alias = 0
    for a in aliases:
        if a.get("id") in MOVES:
            a["id"] = f"{MOVES[a['id']]}:{a['id'].split(':', 1)[1]}"
            if PROV not in a.get("provenance", ""):
                a["provenance"] = f"{a.get('provenance', '')} | {PROV}".strip(" |")
            n_alias += 1
    write_jsonl("aliases", aliases, validate_after=False)
    print(f"[aliases] re-apuntados {n_alias}")
    write_jsonl("products", products, validate_after=False)
    errs = validate()
    if errs:
        for e in errs:
            print(f"[ERROR] {e}")
        return 1
    print(f"OK — {n_new} productos nuevos, {n_redir} redirects; catálogo VÁLIDO")
    cat = load()
    for tok, want in [("MAD-481", "detnov:mad-481"), ("NSRE24", "ada:nsre24"),
                      ("EFD1", "coelbo:efd1"), ("ESTELA-1", "ada:estela-1")]:
        r = cat.resolve(tok)
        ok = r and r.get("ids") == [want] and r.get("expand")
        print(f"  {tok!r} → {r.get('ids') if r else None} {'OK' if ok else 'FAIL'}")
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
