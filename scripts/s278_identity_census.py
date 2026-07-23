#!/usr/bin/env python3
"""s278 identity census — census catalog-wide OFFLINE de la politica de identidad add|replace.

Paso 3 del handoff s277 (docs/HANDOFF_P1_B92FF51_2026-07-22.md §8.1 / §9.3): antes de decidir
`replace` global, censar CADA umbrella/alias/miembro comparando models add-vs-replace y la
alcanzabilidad de documentos via doc_map (no-empty / no-wrong-family estructural).

REGLAS DURAS respetadas:
  - worktree READ-ONLY (solo lectura de data/catalog + config locales);
  - CERO red: guard socket instalado ANTES de importar modulos del repo;
  - NUNCA resolve_for_retrieval (dispararia _shadow_log -> Supabase);
  - IDENTITY_RESOLVE queda off (detect/resolve_query/apply_to_models no lo consultan);
  - salidas SOLO en el scratchpad.

Semantica verificada contra el codigo (worktree s277 @ c4b7136):
  - detect() es policy-independiente (catalog_resolver.py:201-213); se ejecuta 2x por query
    (env add / env replace) y se verifica igualdad; ademas los controles se re-ejecutan en 2
    SUBPROCESOS con la policy fijada en el env del proceso (anti cache-de-modulo).
  - apply_to_models lee IDENTITY_RESOLVE_POLICY en CADA llamada (catalog_resolver.py:289).
  - drop_tokens solo si via in {paraguas, alias, homonimo} y expand=True
    (catalog_resolver.py:260-263) => models_replace SUBSET models_add siempre.
  - Alcanzabilidad de docs = proxy catalogo-side: pseudo-entradas doc_map (canonical_model del
    id de cada entry, tras redirects) filtradas con la regla nivel-1 REAL (substring de
    normalize_model, retriever.py:2024-2028) + la union protectora seam-2 (retriever.py:1993-1998:
    docs de allowed_sources siempre re-incorporados). El fail-open <3 (retriever.py:2067-2069),
    el nivel-2 series y los brazos rescue NO se emulan (dependen del pool retrieval real; se
    declara y se marca `series_registry_applicable` donde el nivel-2 aplicaria).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Rutas derivadas del repo (el script vive en scripts/). La salida se puede desviar con
# S278_CENSUS_OUTDIR (el run original s278 escribio a un scratchpad; canonico = evals/).
WORKTREE = str(Path(__file__).resolve().parents[1])
OUTDIR = Path(os.environ.get("S278_CENSUS_OUTDIR", str(Path(__file__).resolve().parents[1] / "evals")))
RESULT_JSON = OUTDIR / "s278_identity_census_result.json"
REPORT_MD = OUTDIR / "s278_identity_census_report.md"

# ---------------------------------------------------------------- guard anti-red (ANTES de imports del repo)
import socket

_NET_ATTEMPTS: list[str] = []


def _deny(*a, **k):  # noqa: ANN002
    _NET_ATTEMPTS.append(repr(a[:2]))
    raise AssertionError("NETWORK BLOCKED — census s278 es estrictamente offline")


socket.socket.connect = _deny            # type: ignore[method-assign]
socket.create_connection = _deny         # type: ignore[assignment]
socket.getaddrinfo = _deny               # type: ignore[assignment]

# ---------------------------------------------------------------- env higiene + imports del repo
os.environ.pop("IDENTITY_RESOLVE", None)          # off (default) — detect/resolve no lo consultan
os.environ.pop("IDENTITY_FETCH", None)
if "--arm-probe" not in sys.argv:
    # en el modo subproceso la policy DEBE quedarse fijada en el env del proceso entero
    os.environ.pop("IDENTITY_RESOLVE_POLICY", None)
for _f in ("LEVER2_IDENTITY", "LEVER2_PM_RESCUE", "IDENTITY_MAP"):
    os.environ.pop(_f, None)
os.environ["CHUNKS_TABLE"] = "chunks_v2"          # config.py fail-fast exige chunks_v2

sys.path.insert(0, WORKTREE)
os.chdir(WORKTREE)

from src.rag import catalog as C                      # noqa: E402
from src.rag import catalog_resolver as R             # noqa: E402  (auto-inserta scripts/)
import catalog_store                                  # noqa: E402
from src.rag import series_registry as SR             # noqa: E402
from src.rag.retriever import (                       # noqa: E402
    extract_product_models,
    _filter_to_query_models,
)

CLASS_RANK = {"NO_DETECTION": 0, "SAME": 1, "REPLACE_NARROWS": 2,
              "ADD_BROADENS": 3, "REPLACE_DROPS_DOC": 4, "REPLACE_EMPTIES": 5}


# ---------------------------------------------------------------- catalogo + universo doc_map
def load_universe():
    cat = catalog_store.load()
    doc_entries = []                       # (source_file, document_id, pid, pm_norm)
    docs_by_pid: dict[str, set[str]] = {}
    for dm in cat.doc_map:
        src = dm.get("source_file") or ""
        did = str(dm.get("document_id") or "")
        if not src or not did:
            continue
        for e in dm.get("entries") or []:
            pid = cat.follow_redirect(e["id"])
            p = cat.products.get(pid) or {}
            cm = p.get("canonical_model") or ""
            doc_entries.append((src, did, pid, SR.normalize_model(cm)))
            docs_by_pid.setdefault(pid, set()).add(src)
    return cat, doc_entries, docs_by_pid


CAT, DOC_ENTRIES, DOCS_BY_PID = load_universe()
_core_cache: dict[str, frozenset[str]] = {}


def _docs_for_core(core: str) -> frozenset[str]:
    got = _core_cache.get(core)
    if got is None:
        got = frozenset(src for src, _d, _p, pmn in DOC_ENTRIES if pmn and core in pmn)
        _core_cache[core] = got
    return got


def reachable_docs(models: list[str], allowed: frozenset[str]):
    """(matched_nivel1, final_con_union_seam2). None = sin filtro (models vacios:
    retriever.py:1717 solo filtra `if models`)."""
    cores = [SR.normalize_model(m) for m in models if m and SR.normalize_model(m)]
    if not cores:
        return None, None
    matched: set[str] = set()
    for c in cores:
        matched |= _docs_for_core(c)
    return matched, matched | set(allowed or ())


# ---------------------------------------------------------------- evaluacion por query
def eval_query(query: str) -> dict:
    res = R.resolve_query(query)
    models_before = extract_product_models(query)
    arms: dict[str, dict] = {}
    detects: dict[str, list[str]] = {}
    for pol in ("add", "replace"):
        os.environ["IDENTITY_RESOLVE_POLICY"] = pol
        detects[pol] = R.detect(query)                       # detect 2x — debe ser identico
        models = R.apply_to_models(list(models_before), res)
        matched, final = reachable_docs(models, res["allowed_sources"])
        arms[pol] = {"models": models,
                     "matched": matched, "final": final}
    os.environ.pop("IDENTITY_RESOLVE_POLICY", None)
    assert detects["add"] == detects["replace"], f"detect() NO policy-independiente: {query!r}"

    allowed = set(res["allowed_sources"])
    add, rep = arms["add"], arms["replace"]
    qclass, flags = classify_query(res, add, rep, allowed)

    out = {
        "query": query,
        "detected": res["detected"],
        "records": [{k: r.get(k) for k in ("token", "via", "politica", "expand", "ids")}
                    for r in res["records"]],
        "drop_tokens": res["drop_tokens"],
        "models_before": models_before,
        "models_add": add["models"],
        "models_replace": rep["models"],
        "allowed_sources_n": len(allowed),
        "docs_add_n": None if add["final"] is None else len(add["final"]),
        "docs_replace_n": None if rep["final"] is None else len(rep["final"]),
        "docs_matched_add_n": None if add["matched"] is None else len(add["matched"]),
        "docs_matched_replace_n": None if rep["matched"] is None else len(rep["matched"]),
        "class": qclass,
        "flags": flags,
        "series_registry_applicable": bool(SR.series_enabled() and SR.any_series(add["models"])),
    }
    if add["final"] is not None and rep["final"] is not None:
        lost = sorted(add["final"] - rep["final"])
        if lost:
            out["docs_lost_under_replace"] = lost
        if qclass in ("REPLACE_EMPTIES", "REPLACE_DROPS_DOC", "ADD_BROADENS"):
            out["docs_add"] = sorted(add["final"])
            out["docs_replace"] = sorted(rep["final"])
            out["allowed_sources"] = sorted(allowed)
    return out


def classify_query(res, add, rep, allowed):
    flags: list[str] = []
    if not res["detected"]:
        return "NO_DETECTION", flags
    expanded = any(r.get("expand") for r in res["records"])
    if not res["drop_tokens"]:
        flags.append("no_drop_tokens" + ("" if expanded else "_no_expansion(policy_noop)"))
        if add["final"] is not None and not add["final"] and not expanded:
            flags.append("no_docs_either_arm")
        elif add["final"] is not None and not add["final"]:
            flags.append("no_docs_either_arm")
        return "SAME", flags
    if add["models"] == rep["models"]:
        flags.append("drop_token_dedup_por_variante")
        return "SAME", flags
    # brazos distintos
    if rep["final"] is not None and not rep["final"]:
        return "REPLACE_EMPTIES", flags
    lost = (add["final"] or set()) - (rep["final"] or set())
    lost_family = lost & allowed
    if lost_family:
        flags.append(f"family_docs_perdidos:{len(lost_family)}")
        return "REPLACE_DROPS_DOC", flags
    if lost:
        flags.append(f"docs_solo_bajo_add:{len(lost)}")
        return "ADD_BROADENS", flags
    if add["final"] is not None and not add["final"]:
        flags.append("no_docs_either_arm")
    return "REPLACE_NARROWS", flags


# ---------------------------------------------------------------- unidades del census
def alias_eligibility(a: dict) -> tuple[bool, str | None]:
    """Replica los criterios del detector (_resolvable_terms, catalog_resolver.py:99-139)."""
    if a.get("candidate"):
        return False, "alias candidate"
    if not CAT._consumable(a["id"]):
        return False, "destino no consumible (candidate/retirado)"
    if a.get("tipo") not in R.DETECT_ALIAS_TIPOS and not any(ch.isdigit() for ch in a["alias"]):
        return False, "nombre-largo sin digito (excluido del detector)"
    nk = C.normkey(a["alias"])
    segs = "".join(re.findall(r"[a-z]+|\d+", C._fold(a["alias"])))
    if not segs or segs.isdigit():
        return False, "normkey digit-only (pre-exclusion del detector)"
    if nk in R.DETECT_STOPWORDS:
        return False, "DETECT_STOPWORDS"
    return True, None


def build_units():
    units, fuera = [], {"aliases": {}, "products_sin_umbrella": 0,
                        "miembros_no_consumibles": [], "otros": []}
    # 1) CADA umbrella
    for u in CAT.umbrellas:
        t = u["termino"]
        units.append({
            "unit_id": f"umbrella:{t}", "kind": "umbrella", "surface": t,
            "catalog_ref": {"tipo": u.get("tipo"), "divergent": u.get("divergent"),
                            "candidate": u.get("candidate"), "ids": u.get("ids")},
            "queries": [t, f"manual de {t}", f"averia en la central {t}"],
        })
    # 2) CADA homonimo (producen drop_tokens via homonimo-prefer; clarify/fail-open = no-op)
    for h in CAT.homonyms:
        t = h["termino"]
        units.append({
            "unit_id": f"homonym:{t}", "kind": "homonym", "surface": t,
            "catalog_ref": {"politica": h.get("politica"), "candidate": h.get("candidate"),
                            "ids": h.get("ids")},
            "queries": [t, f"manual de {t}"],
        })
    # 3) CADA alias detector-elegible (via=alias => drop_token bajo replace)
    for a in CAT.aliases:
        ok, reason = alias_eligibility(a)
        if not ok:
            fuera["aliases"][reason] = fuera["aliases"].get(reason, 0) + 1
            continue
        al = a["alias"]
        units.append({
            "unit_id": f"alias:{al}", "kind": "alias", "surface": al,
            "catalog_ref": {"tipo": a.get("tipo"), "id": a["id"],
                            "target": CAT.follow_redirect(a["id"])},
            "queries": [al, f"manual de {al}"],
        })
    # 4) CADA producto miembro de alguna umbrella (pertenencia a umbrella)
    member_ids: dict[str, list[str]] = {}
    for u in CAT.umbrellas:
        for pid in u.get("ids") or []:
            member_ids.setdefault(CAT.follow_redirect(pid), []).append(u["termino"])
    for pid, umbs in sorted(member_ids.items()):
        p = CAT.products.get(pid) or {}
        if not (p.get("estado") == "activo" and not p.get("candidate")):
            fuera["miembros_no_consumibles"].append(
                {"id": pid, "estado": p.get("estado"), "candidate": p.get("candidate"),
                 "umbrellas": umbs})
            continue
        cm = p["canonical_model"]
        units.append({
            "unit_id": f"product:{pid}", "kind": "product_member", "surface": cm,
            "catalog_ref": {"umbrellas": umbs, "canonical_model": cm},
            "queries": [cm, f"manual de {cm}"],
        })
    # productos NO miembros de umbrella: resolucion exact => sin drop_tokens => policy-noop
    n_active = sum(1 for p in CAT.products.values()
                   if p.get("estado") == "activo" and not p.get("candidate"))
    fuera["products_sin_umbrella"] = n_active - len(
        [pid for pid in member_ids
         if (CAT.products.get(pid) or {}).get("estado") == "activo"
         and not (CAT.products.get(pid) or {}).get("candidate")])
    fuera["otros"].append(f"relations.jsonl ({len(CAT.relations)} filas) y docrel.jsonl "
                          f"({len(CAT.docrel)}): relacionales, no resolubles por query — sin "
                          f"unidad de census")
    fuera["otros"].append("doc_map.jsonl: consumido como sustrato de alcanzabilidad, no unidad")
    fuera["otros"].append(f"products activos no-candidate sin umbrella: "
                          f"{fuera['products_sin_umbrella']} — exact-only, replace==add por "
                          f"construccion (drop_tokens solo en paraguas/alias/homonimo, "
                          f"catalog_resolver.py:260-263)")
    return units, fuera


# ---------------------------------------------------------------- controles obligatorios
CONTROL_QUERIES = [
    "conectar una sirena convencional en Morley ZXe",      # hp018 (pinned test :123-139)
    "manual de la central ZX2e/ZX5e",                      # hp018 forma rango
    "central ZXe",                                          # hp009 (pinned tests :96-120)
]


def run_controls() -> dict:
    controls: dict[str, dict] = {}

    fam_docs = (DOCS_BY_PID.get("morley:zx1e", set())
                | DOCS_BY_PID.get("morley:zx2e", set())
                | DOCS_BY_PID.get("morley:zx5e", set()))
    legacy_docs = (DOCS_BY_PID.get("morley:zxae", set())
                   | DOCS_BY_PID.get("morley:zxee", set())) - fam_docs

    # ---- hp018
    checks = []
    for q in CONTROL_QUERIES[:2]:
        r = eval_query(q)
        docs_rep = set(r.get("docs_replace") or []) or None
        if docs_rep is None:
            _, fin = None, None
            res = R.resolve_query(q)
            os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"
            m = R.apply_to_models(list(extract_product_models(q)), res)
            _, fin = reachable_docs(m, res["allowed_sources"])
            os.environ.pop("IDENTITY_RESOLVE_POLICY", None)
            docs_rep = fin or set()
        res2 = R.resolve_query(q)
        os.environ["IDENTITY_RESOLVE_POLICY"] = "add"
        m_add = R.apply_to_models(list(extract_product_models(q)), res2)
        _, docs_add = reachable_docs(m_add, res2["allowed_sources"])
        os.environ.pop("IDENTITY_RESOLVE_POLICY", None)
        checks.append({
            "query": q,
            "replace_excluye_legacy_310": sorted(docs_rep & legacy_docs) == [],
            "replace_conserva_530_combinados": bool(fam_docs & docs_rep),
            "add_arrastra_legacy (clase del bug)": bool(set(docs_add or ()) & legacy_docs),
            "docs_replace_familia": sorted(docs_rep & (fam_docs | legacy_docs)),
            "docs_add_familia": sorted(set(docs_add or ()) & (fam_docs | legacy_docs)),
            "census_class": r["class"],
        })
    # replicacion sintetica del test pineado (tests/test_catalog_resolver.py:123-139)
    os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"
    res = R.resolve_query("conectar una sirena convencional en Morley ZXe")
    models = R.apply_to_models(["ZXE"], res)
    chunks = ([{"product_model": "ZXAE/ZXEE", "source_file": "MIE-MI-310", "content": "x"}] * 3
              + [{"product_model": "ZX2e/ZX5e", "source_file": "MIE-MI-530rv001", "content": "x"}] * 3)
    out = _filter_to_query_models(chunks, models, identity_allowed=res["allowed_sources"])
    os.environ.pop("IDENTITY_RESOLVE_POLICY", None)
    synth_hp018 = ({c["product_model"] for c in out} == {"ZX2e/ZX5e"}
                   and {c["source_file"] for c in out} == {"MIE-MI-530rv001"}
                   and "ZXE" not in models)
    hp018_pass = synth_hp018 and all(
        c["replace_excluye_legacy_310"] and c["replace_conserva_530_combinados"]
        for c in checks)
    controls["hp018"] = {"verdict": "PASS" if hp018_pass else "FAIL",
                         "synthetic_pinned_test_replica": synth_hp018,
                         "probes": checks}

    # ---- hp009
    r9 = eval_query("central ZXe")
    combined = [{"product_model": "ZX2e/ZX5e", "source_file": "MIE-MI-530", "content": "x"}] * 3
    synth = {}
    for pol in ("add", "replace"):
        os.environ["IDENTITY_RESOLVE_POLICY"] = pol
        resq = R.resolve_query("central ZXe")
        m = R.apply_to_models(["ZXE"], resq)
        synth[pol] = len(_filter_to_query_models(combined, m)) == 3
    os.environ.pop("IDENTITY_RESOLVE_POLICY", None)
    hp009_pass = (set(r9["models_replace"]) == {"ZX1e", "ZX2e", "ZX5e"}
                  and (r9["docs_replace_n"] or 0) > 0
                  and synth["add"] and synth["replace"])
    controls["hp009"] = {
        "verdict": "PASS" if hp009_pass else "FAIL",
        "models_replace": r9["models_replace"],
        "docs_replace_n": r9["docs_replace_n"],
        "no_se_vacia_bajo_replace": (r9["docs_replace_n"] or 0) > 0,
        "family_level_chunks_sobreviven_add": synth["add"],
        "family_level_chunks_sobreviven_replace": synth["replace"],
    }

    # ---- cat017 INSPIRE/E10/E15 — identidades sin gobernar (hallazgo, no fallo del script)
    probes = ["INSPIRE", "E10", "E15", "INSPIRE E10", "INSPIRE E15",
              "Notifier INSPIRE E10", "Notifier INSPIRE E15", "manual de INSPIRE E10",
              "Como genero el fichero de licencia .bin en CLSS para una central INSPIRE E10"]
    rows = []
    for q in probes:
        det = R.detect(q)
        seed = extract_product_models(q)
        rows.append({"query": q, "detect": det, "extract_product_models_seed": seed})
    all_ungoverned = all(not r["detect"] for r in rows)
    controls["cat017_inspire"] = {
        "verdict": "DOCUMENTED_UNGOVERNED" if all_ungoverned else "UNEXPECTED_DETECTION",
        "detalle": rows,
        "nota": ("detect()==[] en todas las formas => el catalogo gobernado NO resuelve "
                 "INSPIRE/E10/E15 (handoff §8.2: 7 identidades candidate sin gobernar). El seed "
                 "MODEL_PATTERN del retriever si detecta formas 'INSPIRE E10' (retriever.py:56) "
                 "— la deteccion legacy existe pero SIN resolucion/doc_map gobernados."),
    }
    return controls


# ---------------------------------------------------------------- aislamiento por proceso
def arm_probe_main(arm: str) -> None:
    """Subproceso: policy fijada en el ENV del proceso entero (anti cache-de-modulo)."""
    out = {}
    for q in CONTROL_QUERIES:
        res = R.resolve_query(q)
        out[q] = R.apply_to_models(list(extract_product_models(q)), res)
    sys.stdout.write(json.dumps({"arm": arm, "models": out}, ensure_ascii=False))


def process_isolation_check() -> dict:
    me = str(Path(__file__).resolve())
    inproc = {}
    for pol in ("add", "replace"):
        os.environ["IDENTITY_RESOLVE_POLICY"] = pol
        inproc[pol] = {q: R.apply_to_models(list(extract_product_models(q)), R.resolve_query(q))
                       for q in CONTROL_QUERIES}
    os.environ.pop("IDENTITY_RESOLVE_POLICY", None)
    result = {"match": True, "detail": {}}
    for pol in ("add", "replace"):
        env = os.environ.copy()
        env["IDENTITY_RESOLVE_POLICY"] = pol
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run([sys.executable, me, "--arm-probe", pol],
                           capture_output=True, cwd=WORKTREE, env=env, timeout=300)
        try:
            sub = json.loads(p.stdout.decode("utf-8"))
        except Exception:
            result["match"] = False
            result["detail"][pol] = {"error": p.stderr.decode("utf-8", "replace")[-800:]}
            continue
        same = sub["models"] == inproc[pol]
        result["detail"][pol] = {"subprocess_equals_inprocess": same}
        if not same:
            result["match"] = False
            result["detail"][pol]["subprocess"] = sub["models"]
            result["detail"][pol]["inprocess"] = inproc[pol]
    return result


# ---------------------------------------------------------------- census principal
def unit_aggregate(unit: dict) -> dict:
    qresults = [eval_query(q) for q in unit["queries"]]
    best = max(qresults, key=lambda r: CLASS_RANK[r["class"]])
    flags = sorted({f for r in qresults for f in r["flags"]})
    detected_q = [r for r in qresults if r["detected"]]
    if detected_q and all(r["docs_add_n"] == 0 for r in detected_q):
        flags.append("no_docs_either_arm_all_queries")
    # ¿la resolucion apunta a la unidad? (superficie secuestrada por exact/homonimo)
    match_unit = None
    tgt = None
    if unit["kind"] == "alias":
        tgt = unit["catalog_ref"]["target"]
    elif unit["kind"] == "product_member":
        tgt = unit["unit_id"].split(":", 1)[1]
    if tgt is not None:
        ids = {i for r in qresults for rec in r["records"] for i in (rec.get("ids") or [])}
        match_unit = tgt in ids if ids else False
        if match_unit is False and any(r["detected"] for r in qresults):
            flags.append("resolucion_no_apunta_a_la_unidad")
    out = dict(unit)
    out["class"] = best["class"]
    out["flags"] = flags
    out["query_results"] = qresults
    if match_unit is not None:
        out["resolution_matches_unit"] = match_unit
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-probe", choices=("add", "replace"))
    args = ap.parse_args()
    if args.arm_probe:
        arm_probe_main(args.arm_probe)
        return 0

    t0 = time.time()
    units, fuera = build_units()
    results = [unit_aggregate(u) for u in units]
    controls = run_controls()
    iso = process_isolation_check()

    by_class: dict[str, int] = {}
    for r in results:
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    by_kind_class: dict[str, dict[str, int]] = {}
    for r in results:
        by_kind_class.setdefault(r["kind"], {}).setdefault(r["class"], 0)
        by_kind_class[r["kind"]][r["class"]] += 1

    catalog_commit = R.catalog_commit()
    summary = {
        "worktree": WORKTREE,
        "catalog_commit": catalog_commit,
        "units_total": len(results),
        "by_class": by_class,
        "by_kind_class": by_kind_class,
        "controls": {k: v["verdict"] for k, v in controls.items()},
        "process_isolation_check": iso["match"],
        "detect_policy_independent": True,   # assert por-query; una violacion habria abortado
        "net_attempts_blocked": len(_NET_ATTEMPTS),
        "runtime_s": round(time.time() - t0, 1),
        "n_queries": sum(len(u["queries"]) for u in units),
    }
    payload = {"summary": summary, "controls": controls,
               "process_isolation": iso, "fuera_de_census": fuera, "units": results}
    RESULT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    write_report(summary, controls, iso, fuera, results)
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


def write_report(summary, controls, iso, fuera, results) -> None:
    L: list[str] = []
    a = L.append
    a("# s278 — Census catalog-wide de identidad (add vs replace) — OFFLINE")
    a("")
    a(f"Worktree: `{WORKTREE}` (READ-ONLY) · catalog_commit: `{summary['catalog_commit']}` · "
      f"{summary['units_total']} unidades · {summary['n_queries']} queries de sondeo · "
      f"{summary['runtime_s']}s · 0 red (guard socket activo, "
      f"{summary['net_attempts_blocked']} intentos bloqueados)")
    a("")
    a("## 1. Conteos por clase")
    a("")
    a("| Clase | Unidades |")
    a("|---|---:|")
    for cls in ("REPLACE_EMPTIES", "REPLACE_DROPS_DOC", "ADD_BROADENS",
                "REPLACE_NARROWS", "SAME", "NO_DETECTION"):
        a(f"| {cls} | {summary['by_class'].get(cls, 0)} |")
    a("")
    a("Por tipo de unidad:")
    a("")
    kinds = sorted(summary["by_kind_class"])
    a("| kind | " + " | ".join(("REPLACE_EMPTIES", "REPLACE_DROPS_DOC", "ADD_BROADENS",
                                "REPLACE_NARROWS", "SAME", "NO_DETECTION")) + " |")
    a("|---|" + "---:|" * 6)
    for k in kinds:
        row = summary["by_kind_class"][k]
        a(f"| {k} | " + " | ".join(str(row.get(c, 0)) for c in
                                   ("REPLACE_EMPTIES", "REPLACE_DROPS_DOC", "ADD_BROADENS",
                                    "REPLACE_NARROWS", "SAME", "NO_DETECTION")) + " |")
    a("")

    def _dump_units(cls: str, title: str, with_docs: bool) -> None:
        rows = [r for r in results if r["class"] == cls]
        a(f"## {title} — {len(rows)} unidades (lista COMPLETA)")
        a("")
        if not rows:
            a("(ninguna)")
            a("")
            return
        for r in rows:
            a(f"### `{r['unit_id']}`")
            a(f"- ref catalogo: `{json.dumps(r['catalog_ref'], ensure_ascii=False)}`")
            a(f"- flags: {', '.join(r['flags']) or '—'}")
            for q in r["query_results"]:
                if q["class"] != cls:
                    continue
                a(f"- query: `{q['query']}`")
                a(f"  - models add → replace: `{q['models_add']}` → `{q['models_replace']}`")
                a(f"  - docs add/replace (con union seam-2): {q['docs_add_n']} / {q['docs_replace_n']}")
                if with_docs and q.get("docs_lost_under_replace"):
                    a(f"  - docs perdidos bajo replace: `{q['docs_lost_under_replace']}`")
                if with_docs and q.get("docs_replace") is not None and cls == "REPLACE_EMPTIES":
                    a(f"  - allowed_sources: `{q.get('allowed_sources')}`")
            a("")

    _dump_units("REPLACE_EMPTIES", "2. REPLACE_EMPTIES", with_docs=True)
    _dump_units("REPLACE_DROPS_DOC", "3. REPLACE_DROPS_DOC (docs de familia perdidos)", with_docs=True)
    _dump_units("ADD_BROADENS", "4. ADD_BROADENS (la clase del bug hp018)", with_docs=True)

    a("## 5. Controles obligatorios")
    a("")
    for name, c in controls.items():
        a(f"### {name} — **{c['verdict']}**")
        a("```json")
        a(json.dumps({k: v for k, v in c.items() if k != "detalle"},
                     ensure_ascii=False, indent=1, default=str))
        a("```")
        if name == "cat017_inspire":
            a("Sondeos (detect gobernado vs seed legacy):")
            a("")
            a("| query | detect() | seed extract |")
            a("|---|---|---|")
            for row in c["detalle"]:
                a(f"| `{row['query'][:60]}` | `{row['detect']}` | "
                  f"`{row['extract_product_models_seed']}` |")
            a("")
    a(f"### Aislamiento por proceso — {'PASS' if iso['match'] else 'FAIL'}")
    a("Los controles se re-ejecutaron en subprocesos con `IDENTITY_RESOLVE_POLICY` fijada en el "
      "env del proceso completo; resultados identicos al toggling in-process "
      "(`apply_to_models` lee el env en cada llamada, catalog_resolver.py:289; `detect()` no "
      "consulta la policy y se verifico 2x por query con assert de igualdad).")
    a("")

    a("## 6. Fuera de census (sin truncado silencioso)")
    a("")
    a("| Grupo | Motivo | N |")
    a("|---|---|---:|")
    for reason, n in sorted(fuera["aliases"].items()):
        a(f"| aliases | {reason} | {n} |")
    a(f"| products | activos no-candidate sin umbrella (exact-only ⇒ replace==add por "
      f"construccion, catalog_resolver.py:260-263) | {fuera['products_sin_umbrella']} |")
    a(f"| miembros de umbrella | no consumibles (candidate/retirado) — no probeables | "
      f"{len(fuera['miembros_no_consumibles'])} |")
    for o in fuera["otros"]:
        a(f"| otros | {o} | — |")
    a("")
    if fuera["miembros_no_consumibles"]:
        a("Miembros no consumibles: " + ", ".join(
            f"`{m['id']}` ({m['estado']}{', candidate' if m.get('candidate') else ''})"
            for m in fuera["miembros_no_consumibles"]))
        a("")

    a("## 7. Honestidad del instrumento — lo que este census NO juzga")
    a("")
    a("- **Wrong-family SEMANTICO** mas alla de los drop_tokens estructurales: el census compara "
      "conjuntos de documentos via doc_map; decidir si un doc extra es contenido incorrecto para "
      "la pregunta requiere lectura humana/duo. Aqui solo se marca la clase estructural.")
    a("- **Nondeterminismo del `LIMIT` de content_search**: requiere DB (plan fisico de Postgres); "
      "prohibido en este census offline. Queda pendiente del candidate-context gate (handoff §8.1).")
    a("- **Alcanzabilidad = proxy catalogo-side**: pseudo-entradas de doc_map (canonical_model de "
      "cada entry tras redirects) con la regla nivel-1 REAL (substring sobre "
      "`series_registry.normalize_model`, retriever.py:2024-2028) + union protectora seam-2 "
      "(retriever.py:1993-1998). NO son los tags `product_model` reales de la DB (combinados tipo "
      "'ZX2e/ZX5e' o 'unknown' difieren; la union seam-2 es exactamente lo que protege esa clase).")
    a("- **No emulado por ser pool-dependiente**: fail-open `<3` (retriever.py:2067-2069), nivel-2 "
      "series (vetos de hermanos), brazos rescue (flags OFF), vector search, reranker. Las "
      "unidades donde el nivel-2 aplicaria van marcadas `series_registry_applicable`.")
    n_series = sum(1 for r in results
                   if any(q.get("series_registry_applicable") for q in r["query_results"]))
    a(f"  - unidades con series-registry aplicable: {n_series}")
    a("- **La conducta answer/clarify NO se toca**: expand=False (clarify/unknown/candidate) es "
      "no-op de policy por contrato (drop solo bajo expand=True) — esas unidades son SAME aqui, "
      "no evidencia de que clarify sea correcto para la pregunta.")
    a("- El census usa la ruta harness offline (`resolve_query`/`apply_to_models`); "
      "`resolve_for_retrieval` (shadow-log a Supabase) NO se llama nunca.")
    a("")
    REPORT_MD.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
