#!/usr/bin/env python3
"""s91_apply_homonyms.py — aplica la adjudicación de Alberto (s91) de los 25 homónimos
cross-brand por la puerta `catalog_store`.

Fuente de la adjudicación: `evals/s91_homonyms_preqa.md` (G1 ✅ · G2 ✅ · G3 ✏️×3 · G4 B-clarify),
adjudicado por Alberto en sesión s91 sobre evidencia corpus+web+píxel. Transcripción FIEL
(clase de error H5: re-leer el packet antes de tocar cada token).

Qué hace por cada A-merge: winner → candidate=false + vendido_bajo adjudicado + oem declarado;
losers → estado=redirect (id INMUTABLE, nunca borrado); relación rebrand-of; el homónimo del
token se RETIRA (el token pasa a resolver por exact/alias + redirect). APIC (G4) → homónimo
adjudicado politica=clarify candidate=false; sus productos QUEDAN candidate a propósito
(canonical_model idéntico "APIC" — consumirlos a ciegas sería la clase hp011).

Extras adjudicados: umbrella B500 (tabla de Alberto), alias ESS-RP1R-SUPRA (catálogo Esser p4),
oem=System Sensor en LPB-620 y MI-DCZM (© SS verificado al píxel).

Idempotente: los guards saltan lo ya aplicado. Valida el catálogo completo al final (la puerta).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog_store import (CATALOG_DIR, FILES, _read_jsonl, load, norm_token,  # noqa: E402
                           validate, write_jsonl)

PROV = "gt-s91-alberto-homonyms"

# (termino, winner, [losers], vendido_bajo, oem_manufacturer_marca | None)
# Transcrito 1:1 de evals/s91_homonyms_preqa.md — NO añadir tokens que no estén adjudicados.
MERGES: list[tuple[str, str, list[str], list[str], str | None]] = [
    # ── G1 · OEM System Sensor (canonical → systemsensor:*) ──
    ("B501AP", "systemsensor:b501ap", ["morley:b501ap", "notifier:b501ap"],
     ["System Sensor", "Notifier", "Morley-IAS"], None),
    ("B501", "systemsensor:b501", ["notifier:b501"],
     ["System Sensor", "Notifier"], None),                      # Alberto: vendedor SOLO Notifier
    ("REFL20", "systemsensor:refl20", ["notifier:refl20"], ["System Sensor", "Notifier"], None),
    ("REFL30", "systemsensor:refl30", ["notifier:refl30"], ["System Sensor", "Notifier"], None),
    ("REFL40", "systemsensor:refl40", ["notifier:refl40"], ["System Sensor", "Notifier"], None),
    ("REFL50", "systemsensor:refl50", ["notifier:refl50"], ["System Sensor", "Notifier"], None),
    ("REFL60", "systemsensor:refl60", ["notifier:refl60"], ["System Sensor", "Notifier"], None),
    ("6500R", "systemsensor:6500r", ["notifier:6500r"], ["System Sensor", "Notifier"], None),
    ("6500RS", "systemsensor:6500rs", ["notifier:6500rs"], ["System Sensor", "Notifier"], None),
    # 6424: el producto SS no existía en corpus (evidencia = datasheet web + gemelos M/N) → se CREA
    ("6424", "systemsensor:6424", ["morley:6424", "notifier:6424"],
     ["System Sensor", "Notifier", "Morley-IAS"], None),
    ("DH500", "systemsensor:dh500", ["notifier:dh500"], ["System Sensor", "Notifier"], None),
    ("DH500ACDC-E", "systemsensor:dh500acdc-e", ["notifier:dh500acdc-e"],
     ["System Sensor", "Notifier"], None),
    # ── G2 · OEM tercero (canonical → el OEM) ──
    ("SMART 2", "sensitron:smart-2", ["notifier:smart-2"], ["Sensitron", "Notifier"], None),
    ("Z978", "pepperl-fuchs:z978", ["notifier:z978"], ["Pepperl+Fuchs", "Notifier"], None),
    ("777163", "spectrex:777163", ["notifier:777163"], ["Spectrex", "Notifier"], None),
    ("140KIT160", "firebeam:140kit160", ["detnov:140kit160"], ["Firebeam", "Detnov"], None),
    ("70KIT140", "firebeam:70kit140", ["detnov:70kit140"], ["Firebeam", "Detnov"], None),
    ("M700KAC", "kac:m700kac", ["notifier:m700kac"], ["KAC", "Notifier"], None),
    ("M700KACI", "kac:m700kaci", ["notifier:m700kaci"], ["KAC", "Notifier"], None),
    # ── G3 · Intra-Honeywell ──
    # UCIP: Alberto NO declaró oem (portada HLSI = evidencia, no adjudicación) — oem=None
    # (revisor s91 cazó el añadido H5); HLSI queda en vendido_bajo, que SÍ está en el packet
    ("UCIP", "notifier:ucip", ["morley:ucip", "unresolved:ucip"],
     ["Honeywell Life Safety Iberia", "Notifier", "Morley-IAS (Supra)"], None),
    ("UCIP-GPRS", "notifier:ucip-gprs", ["morley:ucip-gprs"],
     ["Honeywell Life Safety Iberia", "Notifier", "Morley-IAS (Supra)"], None),
    # VSN-4REL AJUSTADO por Alberto: NO Morley-only (NFS-Supra también); oem=Esser (catálogo
    # extinción Esser p3 + ESS-RP1R-SUPRA p4); canonical notifier pragmático (branded Notifier)
    ("VSN-4REL", "notifier:vsn-4rel", ["morley:vsn-4rel"],
     ["Notifier", "Morley-IAS", "Esser"], "Esser"),
    # VSN panels: 'Vision = marca de línea' (packet) ≠ OEM → va en vendido_bajo, NO en oem
    # (revisor s91); la fila aprobada cubre los TRES tokens con el MISMO vendido_bajo
    ("VSN 4 PLUS", "morley:vsn-4-plus", ["notifier:vsn4-plus"],
     ["Morley-IAS", "Notifier", "Vision (HLSI)"], None),
    ("VSN12-2Plus", "morley:vsn12-2plus", ["notifier:vsn12-2plus"],
     ["Morley-IAS", "Notifier", "Vision (HLSI)"], None),
    ("VSN-CO", "morley:vsn-co", ["notifier:vsn-co"],
     ["Morley-IAS", "Notifier", "Vision (HLSI)"], None),
    ("IDR-6A", "notifier:idr-6a", ["morley:idr6a"], ["Notifier"], None),
    ("CMX-10RM", "notifier:cmx-10rm", ["morley:cmx-10rm"],
     ["Notifier", "Morley-IAS"], "Xtralis"),                    # AJUSTE Alberto: oem=Xtralis (ficha ADI)
    ("MI-DCZM", "morley:mi-dczm", ["notifier:mi-dczm"],
     ["Morley-IAS"], "System Sensor"),                          # © SS 2005 al píxel; mención N=compat
    ("M710", "notifier:m710", ["morley:m710"], ["Notifier"], None),  # mención M=compat, NO vendido_bajo
    ("2010-2-PAK-RMSDK", "kidde:2010-2-pak-rmsdk", ["edwards:2010-2-pak-rmsdk"],
     ["Kidde Commercial", "Edwards", "Ziton"], "Carrier"),      # AJUSTE Alberto: oem=Carrier (ficha ADI)
]

# Producto que se CREA (sin doc propio en corpus; evidencia web+gemelos, adjudicado G1)
NEW_PRODUCTS = [{
    "id": "systemsensor:6424", "canonical_model": "6424", "estado": "activo",
    "candidate": False, "vendido_bajo": ["System Sensor", "Notifier", "Morley-IAS"],
    "provenance": f"{PROV} (OEM SS: datasheet systemsensor.com A05-0217; manuales GEMELOS "
                  "MIE-MI-140/MIDT750 al pixel)", "added_by": "f1-gt",
}]

# oem declarado sobre productos que NO son parte de un merge
OEM_ONLY = {
    "notifier:lpb-620": "System Sensor",   # © SS 2002 en las 4 páginas (píxel s91, PDF notifier.es)
}

UMBRELLA_B500 = {
    "termino": "B500", "tipo": "serie", "divergent": True, "candidate": False,
    "ids": ["systemsensor:b501", "systemsensor:b501dg", "systemsensor:b524htr",
            "systemsensor:b524ieft-1"],
    "provenance": f"{PROV} (tabla serie B500 de Alberto: B501/B501DG/B524HTR/B524IEFT-1/"
                  "B524RTE; B524RTE declarado SIN doc en corpus, no incluible)",
    "added_by": "f1-gt",
}

ALIAS_ESS = {
    "alias": "ESS-RP1R-SUPRA", "id": "notifier:rp1r-supra", "tipo": "codigo-comercial",
    "provenance": f"{PROV} (catalogo extincion Esser p4: 'central ESS-RP1R-SUPRA')",
    "added_by": "f1-gt",
}

APIC = {"termino": "APIC", "politica": "clarify",
        "provenance": f"{PROV} (G4 B-clarify: tarjetas INCOMPATIBLES Aritech/ModuLaser vs "
                      "Notifier/Stratos; productos quedan candidate a proposito — "
                      "canonical_model identico 'APIC')"}


def _tag(row: dict) -> None:
    if PROV not in row.get("provenance", ""):
        row["provenance"] = f"{row.get('provenance', '')} | {PROV}".strip(" |")


def main() -> int:
    products = _read_jsonl(CATALOG_DIR / FILES["products"])
    by_id = {r["id"]: r for r in products}
    aliases = _read_jsonl(CATALOG_DIR / FILES["aliases"])
    umbrellas = _read_jsonl(CATALOG_DIR / FILES["umbrellas"])
    homonyms = _read_jsonl(CATALOG_DIR / FILES["homonyms"])
    relations = _read_jsonl(CATALOG_DIR / FILES["relations"])
    n_redir = n_win = 0

    for np_ in NEW_PRODUCTS:
        if np_["id"] not in by_id:
            products.append(np_)
            by_id[np_["id"]] = np_
            print(f"[+prod] {np_['id']}")

    rel_seen = {(r["origen"], r["destino"], r["tipo"]) for r in relations}
    for termino, winner, losers, vb, oem in MERGES:
        w = by_id.get(winner)
        if w is None:
            print(f"[ERROR] winner inexistente: {winner}")
            return 1
        w["candidate"] = False
        w["vendido_bajo"] = vb
        if oem:
            w["oem_manufacturer_marca"] = oem
        else:
            w.pop("oem_manufacturer_marca", None)   # idempotente: sana un oem no-adjudicado previo
        _tag(w)
        n_win += 1
        for lid in losers:
            lo = by_id.get(lid)
            if lo is None:
                print(f"[ERROR] loser inexistente: {lid}")
                return 1
            if lo.get("estado") != "redirect":
                lo["estado"] = "redirect"
                lo["redirect_to"] = winner
                lo["candidate"] = False
                _tag(lo)
                n_redir += 1
            if (lid, winner, "rebrand-of") not in rel_seen:
                relations.append({"origen": lid, "destino": winner, "tipo": "rebrand-of",
                                  "provenance": PROV})
                rel_seen.add((lid, winner, "rebrand-of"))

    merged_terms = {t for t, *_ in MERGES}
    before = len(homonyms)
    homonyms = [h for h in homonyms if h["termino"] not in merged_terms]
    print(f"[homonyms] retirados {before - len(homonyms)} adjudicados (quedan {len(homonyms)})")
    for h in homonyms:
        if h["termino"] == APIC["termino"]:
            h["politica"] = APIC["politica"]
            h["candidate"] = False
            h["provenance"] = APIC["provenance"]
            h["added_by"] = "f1-gt"
            print("[APIC] adjudicado clarify (candidate=false)")

    for pid, oem in OEM_ONLY.items():
        row = by_id.get(pid)
        if row is not None and row.get("oem_manufacturer_marca") != oem:
            row["oem_manufacturer_marca"] = oem
            _tag(row)
            print(f"[oem] {pid} → {oem}")

    if not any(u["termino"] == UMBRELLA_B500["termino"] for u in umbrellas):
        umbrellas.append(UMBRELLA_B500)
        print("[+umbrella] B500 (serie, divergent=true)")
    # el gt s78 ya trae "ESS-RP1r-Supra" (norm-igual) → comparar NORMALIZADO, no exacto;
    # y limpiar el dup que la 1ª pasada de este script llegó a escribir
    k_ess = norm_token(ALIAS_ESS["alias"])
    aliases = [a for a in aliases
               if not (norm_token(a["alias"]) == k_ess and PROV in a.get("provenance", ""))]
    if not any(norm_token(a["alias"]) == k_ess for a in aliases):
        aliases.append(ALIAS_ESS)
        print("[+alias] ESS-RP1R-SUPRA → notifier:rp1r-supra")
    else:
        print("[alias] ESS-RP1R-SUPRA ya cubierto (gt-s78 'ESS-RP1r-Supra')")

    write_jsonl("products", products, validate_after=False)
    write_jsonl("relations", relations, validate_after=False)
    write_jsonl("homonyms", homonyms, validate_after=False)
    write_jsonl("umbrellas", umbrellas, validate_after=False)
    write_jsonl("aliases", aliases, validate_after=False)
    errs = validate()
    if errs:
        for e in errs:
            print(f"[ERROR] {e}")
        return 1
    print(f"OK — {n_win} winners, {n_redir} redirects nuevos, catálogo VÁLIDO")

    # smoke de resolución de los tokens adjudicados
    cat = load()
    fails = []
    for termino, winner, _losers, _vb, _oem in MERGES:
        r = cat.resolve(termino)
        if not r or r.get("ids") != [winner] or not r.get("expand"):
            fails.append(f"{termino!r} → {r} (esperaba [{winner}] expand=True)")
    for tok, want_ids, want_expand in [
        ("APIC", 2, False),               # clarify: 2 opciones, sin expandir
        ("B500", 4, True),                # umbrella serie
        ("ESS-RP1R-SUPRA", 1, True),      # alias Esser → rp1r-supra
        ("REFLEX 20", 1, True),           # alias del manual LPB-620 → SS vía redirect
    ]:
        r = cat.resolve(tok)
        ok = r and len(r.get("ids", [])) == want_ids and r.get("expand") == want_expand
        if not ok:
            fails.append(f"{tok!r} → {r} (esperaba {want_ids} ids, expand={want_expand})")
    if fails:
        print("[SMOKE-FAIL]")
        for f in fails:
            print("  " + f)
        return 1
    print(f"SMOKE OK — {len(MERGES)} tokens adjudicados resuelven a su canonical + 4 casos extra")
    return 0


if __name__ == "__main__":
    sys.exit(main())
