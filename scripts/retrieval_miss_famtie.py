#!/usr/bin/env python3
"""retrieval_miss_famtie.py (s85·B0) — re-derivación FAMILY-AWARE EXACTA del retrieval-miss,
sobre el pin del pool del instrumento (sin GPT, re-corrible libre).

POR QUÉ family-aware (corrección de Alberto): el tie por filename-token (by-primary/by-target)
acredita mal. by-target acreditó hp018 vía MIE-MI-310 (familia ZXAE/ZXEE) para una pregunta de
ZXe/MIE-MI-530 = producto DISTINTO que coincide por casualidad → ERROR. El tie correcto =
"¿el chunk-soporte es de la MISMA FAMILIA de producto que el gold?" usando `product_model`.

POR QUÉ exacta (no el ruido de re-retrieve): usa `pool_pin` (id+pm+src guardados por el
instrumento), NO re-recupera el pool → mata el jitter que dio el falso flip de hp001 '2222'.

retrieval-miss FAMILY = hecho CORE con soporte (juez ≥THRESH) pero SIN ningún chunk
same-family en el pool. Bucket family-aware vía `classify` sobre in_top5_fam/in_pool_fam.

Fallback de SOURCE-NAMING (clase DEC-065, gold-provenance ≠ corpus-filename): para resolver la
familia-gold cuando doc_tokens falla — normaliza guiones (MN-DT-722→MNDT722) + token descriptivo
(DXc). Verificado: cat020/hp010=DXc, cat021/cat022=40-40.

Uso: python scripts/retrieval_miss_famtie.py evals/s85_retrieval_miss_DEF.yaml
"""
import os, sys, re, json, httpx
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
import yaml
from collections import Counter
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from scripts.audit_retrieval_funnel import classify

THRESH_FIRM = 4
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
_STOP = {"manual", "de", "variaciones", "mercado", "version", "configuracion", "config",
         "pdf", "base", "el", "la", "para", "guia", "instalacion", "usuario",
         "eventos", "averias", "equipos", "datos", "tabla", "hoja", "rev", "anexo",
         "sistema", "central", "panel", "detector", "documento", "ficha"}


def fam_norm(pm: str) -> str:
    """Normaliza product_model a su FAMILIA. Colapsa variantes 40-40L/U/R/M/I → 40-40."""
    u = (pm or "").upper().strip()
    if not u or u == "UNKNOWN":
        return ""
    if u.startswith("40-40"):
        return "40-40"
    return u


def _families_for_pattern(pat: str) -> set[str]:
    if len(pat) < 3:
        return set()
    try:
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                      params={"select": "product_model", "source_file": f"ilike.*{pat}*", "limit": "150"},
                      timeout=20)
        return {fam_norm(x.get("product_model")) for x in r.json()}
    except Exception:
        return set()


_GF_CACHE: dict = {}


def gold_family(primary: list[str], targets: list[str], fuente: str) -> set[str]:
    """Familia(s) de producto del gold = product_model de los manuales primario/target.
    Source-naming fallback: tokens + guion-normalizado + token descriptivo del fuente."""
    key = (tuple(primary), tuple(targets), fuente)
    if key in _GF_CACHE:
        return _GF_CACHE[key]
    toks = list(primary) or list(targets)
    patterns = set(toks)
    for t in toks:                       # MN-DT-722 → MNDT722 (guion-mismatch DEC-065)
        nh = t.replace("-", "")
        patterns.add(nh)
        patterns.add(re.sub(r"[_-][A-Za-z]$", "", nh))   # MNDT722_B → MNDT722 (sufijo de revisión)
        m = re.match(r"^([A-Za-z]+\d+)", nh)             # core alfa+dígito: MNDT722
        if m:
            patterns.add(m.group(1))
    if not toks:                          # fuente descriptiva sin token-dígito (DXc): palabra distintiva
        for w in re.findall(r"[A-Za-z]{3,}", fuente):
            if w.lower() not in _STOP and (any(c.isupper() for c in w[1:]) or w[0].isupper()):
                patterns.add(w)
    fams: set[str] = set()
    for p in patterns:
        fams |= _families_for_pattern(p)
    fams.discard("")
    _GF_CACHE[key] = fams
    return fams


def rederive(run_path: str) -> dict:
    d = yaml.safe_load(open(run_path, encoding="utf-8"))
    results = d["reps"][0]["results"]
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(os.path.join(os.getcwd(), "evals", "gold_answers_v1.yaml"), encoding="utf-8"))}
    agg = Counter()
    per_gold = {}
    misses = []
    for res in results:
        fuente = ((golds.get(res["qid"], {}).get("_provenance") or {}).get("fuente", ""))
        gfam = gold_family(res.get("primary") or [], res.get("targets") or [], fuente)
        pin = {c["id"]: c for c in res.get("pool_pin", [])}
        man = {c["id"]: c for c in res.get("manual_pin", [])}
        top5 = set(res.get("top5_ids", []))
        gb = Counter()
        for f in res["facts"]:
            if f["valor"] == "manual de variaciones Espana":   # meta-ref, no es dato recuperable
                continue
            sup = [i for i, v in (f.get("votes") or {}).items() if v >= THRESH_FIRM]

            def same_fam(cid):
                c = pin.get(cid) or man.get(cid)
                return bool(c) and ((not gfam) or (fam_norm(c.get("pm")) in gfam))

            in_top5 = any((cid in top5) and same_fam(cid) for cid in sup)
            in_pool = any((cid in pin) and same_fam(cid) for cid in sup)
            in_man = any((cid in man) and same_fam(cid) for cid in sup)
            bucket = classify(in_top5, in_pool, in_pool or in_man)
            gb[bucket] += 1
            agg[bucket] += 1
            if bucket == "RETRIEVAL":
                sup_fams = sorted({fam_norm((pin.get(i) or man.get(i) or {}).get("pm")) for i in sup})
                misses.append({"qid": res["qid"], "valor": f["valor"], "gold_family": sorted(gfam),
                               "sup_fams": [x for x in sup_fams if x]})
        per_gold[res["qid"]] = dict(gb)
    return {"agg": dict(agg), "retrieval_miss_family": agg.get("RETRIEVAL", 0),
            "n_facts": sum(agg.values()), "misses": misses, "per_gold": per_gold}


if __name__ == "__main__":
    out = rederive(sys.argv[1] if len(sys.argv) > 1 else "evals/s85_retrieval_miss_DEF.yaml")
    print(json.dumps({k: out[k] for k in ("agg", "retrieval_miss_family", "n_facts")},
                     ensure_ascii=False))
    print(f"\nretrieval-miss FAMILY-AWARE = {out['retrieval_miss_family']} (de {out['n_facts']} hechos)")
    print("\nMISSES (canal de identidad/familia = sup_fams != gold_family):")
    for m in out["misses"]:
        print(f"  {m['qid']:8} {m['valor'][:26]!r:28} gold_fam={m['gold_family']} sup_fams={m['sup_fams']}")
