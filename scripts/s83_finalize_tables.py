#!/usr/bin/env python3
"""s83_finalize_tables.py - FOLD-IN: funde las 29 decisiones adjudicadas con los 985 ya construidos
-> tablas FINALES de los 1014 docs (document_models_final / document_identity_final).

- 985 reconciliados: ya en evals/s83_document_models.jsonl (build determinista, Fix1+higiene). Se copian.
- 29 conflicts: se construyen desde evals/s83_conflicts_resolved.yaml (traducción de las decisiones de Alberto),
  ENRIQUECIENDO cada nombre desde la extracción cruda (aliases/category/evidence/cert por match normalizado).
Read-only sobre los insumos; escribe a evals/. NO toca la DB.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
MERGED = ROOT / "evals" / "s83_full_extraction_merged.jsonl"
MODELS_985 = ROOT / "evals" / "s83_document_models.jsonl"
IDENT_985 = ROOT / "evals" / "s83_document_identity.jsonl"
RESOLVED = ROOT / "evals" / "s83_conflicts_resolved.yaml"
OUT_MODELS = ROOT / "evals" / "s83_document_models_final.jsonl"
OUT_IDENT = ROOT / "evals" / "s83_document_identity_final.jsonl"

sys.path.insert(0, str(ROOT / "scripts"))
from s83_build_document_models import norm, covered, build_identity, build_models  # noqa: E402


def keyset(m: dict) -> set:
    ks = set()
    for v in (m.get("model"), m.get("canonical_model")):
        if v and norm(v):
            ks.add(norm(v))
    for a in (m.get("aliases") or []):
        if a and norm(a):
            ks.add(norm(a))
    return ks


def enrich(name, raw_objs):
    """Busca el nombre en los covered_models crudos (ambos modelos) por match de keyset normalizado.
    Devuelve aliases/category/evidence/cert/confidence/provenance fusionados, o None si no está (Alberto-añadido)."""
    nn = norm(name)
    hits = [m for m in raw_objs if nn in keyset(m)]
    if not hits:
        return None
    aliases, seen = [], {nn}
    for m in hits:
        for v in [m.get("model"), m.get("canonical_model"), *(m.get("aliases") or [])]:
            if v and norm(v) and norm(v) not in seen:
                seen.add(norm(v)); aliases.append(v)
    cats = [m.get("category") for m in hits if m.get("category")]
    certs = []
    for m in hits:
        for c in (m.get("cert") or []):
            if c not in certs: certs.append(c)
    conf_rank = {"high": 3, "medium": 2, "low": 1}
    confidence = max((m.get("confidence") for m in hits), key=lambda c: conf_rank.get(c, 0), default="")
    prov = "body" if any(m.get("provenance") == "body" for m in hits) else (hits[0].get("provenance") or "")
    ev = next((m.get("evidence") for m in hits if m.get("evidence")), None)
    return {"aliases": aliases, "category": (cats or [""])[0], "cert": certs,
            "confidence": confidence, "provenance": prov, "evidence": ev}


def _ks(r):
    return {norm(r["canonical_model"])} | {norm(a) for a in r.get("aliases", [])}


def find_record(name, records):
    nn = norm(name)
    return next((r for r in records if nn in _ks(r)), None)


def build_resolved(entry, raw):
    """BASE = unión canónica (build_models, igual que los 985) → no se pierde el set ACORDADO.
    La adjudicación MODIFICA encima: drop quita; compat/mention sacan de covered; los buckets
    reclasifican rol/categoría; los nombres que Alberto añadió y no están en base entran como adjudication."""
    raw_objs = covered(raw.get("opus")) + covered(raw.get("gpt"))
    # replace=True: la resolución es un OVERRIDE de limpieza (FAD/FS) → ignora la base cruda, usa solo los buckets.
    # Default (centrales multi-producto): base = unión canónica para no perder el set acordado.
    base = [] if entry.get("replace") else build_models(covered(raw.get("opus")), covered(raw.get("gpt")))
    drops = {norm(d) for d in entry.get("drop", [])}
    compat = entry.get("compat", []) or []
    mention = entry.get("mention", []) or []
    compat_n = {norm(c) for c in compat}
    mention_n = {norm(m) for m in mention}
    expl_aliases = entry.get("aliases", {}) or {}

    # códigos internos NNN-NNN (refs de PCB ambiguas, p.ej. MNDT021): drop por SUBSTRING (van embebidos en el nombre)
    code_drops = {d for d in drops if re.match(r"^\d+-\d+$", d)}
    def has_code(s):  # match de TOKEN (límite de palabra), no substring → no borra "CAB-124-128X"
        return any(re.search(r"\b" + re.escape(c) + r"\b", s) for c in code_drops)
    def hits_drop(ks):
        return bool(ks & drops) or any(has_code(k) for k in ks)
    kept = []
    for r in base:
        ks = _ks(r)
        if hits_drop(ks) or ks & compat_n or ks & mention_n:
            continue
        r["aliases"] = [a for a in r["aliases"] if norm(a) not in drops and not has_code(norm(a))]
        kept.append(r)

    def apply(names, role, candidate=False, force_cat=None):
        for name in names:
            if norm(name) in drops:
                continue
            rec = find_record(name, kept)
            if rec:
                rec["role"] = role
                rec["candidate"] = candidate
                if force_cat:
                    rec["category"] = force_cat
            else:  # añadido por Alberto, no en la extracción → registro de adjudicación
                en = enrich(name, raw_objs) or {"aliases": [], "category": "", "cert": [],
                                                "confidence": "", "provenance": "adjudication", "evidence": None}
                aliases = [a for a in en["aliases"] if norm(a) not in drops and norm(a) != norm(name)]
                kept.append({"canonical_model": name, "aliases": aliases, "role": role,
                             "candidate": candidate, "found_by": "both" if en["provenance"] != "adjudication" else "adjudication",
                             "category": force_cat or en["category"], "provenance": en["provenance"],
                             "cert": en["cert"], "confidence": en["confidence"], "evidence": en["evidence"]})

    apply(entry.get("primary", []), "primary")
    apply(entry.get("software", []), "primary", force_cat="software")            # doc ES del software
    apply(entry.get("software_tool", []), "secondary", force_cat="software")     # software accesorio
    apply(entry.get("package", []), "secondary", force_cat="paquete equipo básico")  # bundle/umbrella
    apply(entry.get("secondary", []), "secondary")
    apply(entry.get("candidate", []), "secondary", candidate=True)

    # DEGRADAR a secondary los productos de base-unión que NO son el primary adjudicado:
    # cuando la prosa designa la central como único primary, los módulos heredan 'primary' del crudo → bajar.
    named_primary = {norm(n) for n in (entry.get("primary", []) + entry.get("software", []))}
    if entry.get("primary") or entry.get("software"):
        for r in kept:
            if r["role"] == "primary" and norm(r["canonical_model"]) not in named_primary:
                r["role"] = "secondary"

    for canon, al in expl_aliases.items():
        rec = find_record(canon, kept)
        if rec:
            for a in al:
                if norm(a) not in {norm(x) for x in rec["aliases"]} and norm(a) != norm(rec["canonical_model"]) and norm(a) not in drops:
                    rec["aliases"].append(a)

    kept.sort(key=lambda r: (r["role"] != "primary", r["candidate"], r["canonical_model"]))
    rec = {"source_file": entry["sf"], "models": kept,
           "compatible_with": compat, "mentions": mention}
    flags = {k: entry[k] for k in ("family", "recall_incomplete", "same_doc_as", "confirm", "note") if k in entry}
    if flags:
        rec["doc_flags"] = flags
    return rec


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    merged = {json.loads(l)["source_file"]: json.loads(l)
              for l in MERGED.read_text(encoding="utf-8").splitlines() if l.strip()}
    resolved = yaml.safe_load(RESOLVED.read_text(encoding="utf-8"))
    resolved_sf = {e["sf"] for e in resolved}

    # 985 deterministas (normalizar claves para consistencia)
    m985 = [json.loads(l) for l in MODELS_985.read_text(encoding="utf-8").splitlines() if l.strip()]
    i985 = {json.loads(l)["source_file"]: json.loads(l)
            for l in IDENT_985.read_text(encoding="utf-8").splitlines() if l.strip()}

    # construir todos los registros (985 copiados + 29 resueltos)
    for r in m985:
        r.setdefault("compatible_with", []); r.setdefault("mentions", [])
    res_recs = [(e, build_resolved(e, merged[e["sf"]])) for e in resolved]

    # MAPA GLOBAL alias→canonical (loose = sin separadores) para canonicalizar compat/mention (higiene #1):
    # "AFP 200"/"AFP-200" → el canonical "AFP200" si existe como producto en el corpus.
    def loose(s):
        return re.sub(r"[^A-Z0-9]", "", norm(s))
    loose_canon, loose_alias = {}, {}
    for rec in [*m985, *[r for _, r in res_recs]]:
        for mm in rec["models"]:
            c = mm["canonical_model"]
            if loose(c):
                loose_canon[loose(c)] = c
            for a in mm.get("aliases", []):
                if loose(a):
                    loose_alias.setdefault(loose(a), set()).add(c)
    def canon_target(s):
        ls = loose(s)
        if ls in loose_canon:
            return loose_canon[ls]
        if ls in loose_alias and len(loose_alias[ls]) == 1:
            return next(iter(loose_alias[ls]))
        return s
    n_canon = 0
    for _, rec in res_recs:
        for key in ("compatible_with", "mentions"):
            before = rec[key]
            mapped = []
            for s in before:
                t = canon_target(s)
                if t != s:
                    n_canon += 1
                if t not in mapped:
                    mapped.append(t)
            rec[key] = mapped

    fm = OUT_MODELS.open("w", encoding="utf-8")
    fi = OUT_IDENT.open("w", encoding="utf-8")
    n_models = 0; n_doc = 0
    for r in m985:
        fm.write(json.dumps(r, ensure_ascii=False) + "\n"); n_models += len(r["models"]); n_doc += 1
        fi.write(json.dumps(i985[r["source_file"]], ensure_ascii=False) + "\n")
    n_resolved_models = 0; n_compat = 0; n_recall = 0
    for e, rec in res_recs:
        fm.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n_models += len(rec["models"]); n_resolved_models += len(rec["models"]); n_doc += 1
        n_compat += len(rec["compatible_with"])
        if rec.get("doc_flags", {}).get("recall_incomplete"): n_recall += 1
        ident = {"source_file": e["sf"], **build_identity(merged[e["sf"]])}
        if "family" in e: ident["family"] = e["family"]
        fi.write(json.dumps(ident, ensure_ascii=False) + "\n")
    fm.close(); fi.close()

    print(f"docs finales: {n_doc} (985 deterministas + {len(resolved)} adjudicados)")
    print(f"filas de modelo: {n_models}  (de los 29: {n_resolved_models})")
    print(f"compatible_with capturados: {n_compat} | targets compat/mention canonicalizados: {n_canon}")
    print(f"docs marcados recall_incomplete (candidatos a re-pass): {n_recall}")
    print(f"-> {OUT_MODELS.name} / {OUT_IDENT.name}")
    # sanity: cobertura
    assert n_doc == len(m985) + len(resolved), "conteo de docs no cuadra"
    assert resolved_sf <= set(merged), "algún sf resuelto no existe en el crudo"
    print("OK sanity: 1014 cubiertos, sf válidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
