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


def _pm_by_ids(ids: list[str]) -> dict:
    """product_model de chunks por ID (deterministe). Salva el bug manual_pin pm=None sin re-juzgar."""
    out = {}
    ids = [i for i in ids if i]
    for i in range(0, len(ids), 50):
        ch = ids[i:i + 50]; q = ",".join(f'"{x}"' for x in ch)
        try:
            r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                          params={"select": "id,product_model", "id": f"in.({q})"}, timeout=20)
            for x in r.json():
                out[x["id"]] = x.get("product_model")
        except Exception:
            pass
    return out


# Meta-referencia = el `valor` es un PUNTERO (nombre de manual/sección/apéndice/tabla), NO un dato
# recuperable. No debe contar como retrieval-miss. Predicado principial (no string hardcodeado).
_META_RE = re.compile(r"^\s*(ap[eé]ndice|anexo|secci[oó]n|cap[ií]tulo|tabla|manual|figura|p[aá]gina)\b",
                      re.I)


def _is_meta_ref(valor: str) -> bool:
    return bool(_META_RE.match(valor or ""))


def rederive(run_path: str) -> dict:
    d = yaml.safe_load(open(run_path, encoding="utf-8"))
    results = d["reps"][0]["results"]
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(os.path.join(os.getcwd(), "evals", "gold_answers_v1.yaml"), encoding="utf-8"))}
    agg = Counter()
    per_gold = {}
    misses = []
    unresolved = []          # golds sin familia resoluble (NO fail-open: se excluyen y reportan)
    n_meta = 0
    for res in results:
        fuente = ((golds.get(res["qid"], {}).get("_provenance") or {}).get("fuente", ""))
        gfam = gold_family(res.get("primary") or [], res.get("targets") or [], fuente)
        pin = {c["id"]: c for c in res.get("pool_pin", [])}
        man = {c["id"]: c for c in res.get("manual_pin", [])}
        # CRÍTICO #1 fix: manual_pin venía con pm=None (SELECT sin product_model). Lo parcheo
        # por-ID (sin re-juzgar). Solo los chunks-manual votados (no todo el manual).
        man_need = [i for i, c in man.items() if c.get("pm") in (None, "")]
        if man_need:
            for cid, pmv in _pm_by_ids(man_need).items():
                if cid in man:
                    man[cid] = {**man[cid], "pm": pmv}
        top5 = set(res.get("top5_ids", []))

        # CRÍTICO #2 fix: si la familia del gold NO se resuelve → UNRESOLVED (excluir+reportar),
        # NO fail-open (que desinflaría misses silenciosamente).
        measurable_facts = [f for f in res["facts"] if not _is_meta_ref(f["valor"])]
        if not gfam and measurable_facts:
            unresolved.append(res["qid"])
            per_gold[res["qid"]] = {"UNRESOLVED": len(measurable_facts)}
            continue

        gb = Counter()
        for f in res["facts"]:
            if _is_meta_ref(f["valor"]):     # meta-ref (Apéndice/Manual/Tabla…): no es dato recuperable
                n_meta += 1
                continue
            sup = [i for i, v in (f.get("votes") or {}).items() if v >= THRESH_FIRM]

            def same_fam(cid):
                c = pin.get(cid) or man.get(cid)
                return bool(c) and (fam_norm(c.get("pm")) in gfam)   # gfam garantizado no-vacío aquí

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
            "n_facts": sum(agg.values()), "misses": misses, "per_gold": per_gold,
            "unresolved": unresolved, "n_meta_excluded": n_meta}


if __name__ == "__main__":
    out = rederive(sys.argv[1] if len(sys.argv) > 1 else "evals/s85_retrieval_miss_DEF.yaml")
    print(json.dumps({k: out[k] for k in ("agg", "retrieval_miss_family", "n_facts")},
                     ensure_ascii=False))
    print(f"\nretrieval-miss FAMILY-AWARE = {out['retrieval_miss_family']} (de {out['n_facts']} hechos)")
    print("\nMISSES (canal de identidad/familia = sup_fams != gold_family):")
    for m in out["misses"]:
        print(f"  {m['qid']:8} {m['valor'][:26]!r:28} gold_fam={m['gold_family']} sup_fams={m['sup_fams']}")
