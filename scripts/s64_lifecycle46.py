#!/usr/bin/env python3
"""s64_lifecycle46.py — Runner del lifecycle post-ciclo-A (TECH_DEBT #46).

PRE-REGISTRO: evals/_s64_lifecycle46_design.md (v3, post-dúo: sub-agente r1 8/8
confirmados + cross-model GPT-5.5 r2 5/5 — tally en adversarial_review_log.jsonl).
Este script EJECUTA el diseño, no lo define.

Fases (se invocan por separado — el ANTES corre con el código de main, el
DESPUÉS con el fix de diversify ya aplicado):

  --phase precheck   Regla-C material PRE-mutación: hechos-gold de cat019/hp001
                     presentes en MC-380-2026-c (F3 r1) + cobertura de secciones
                     MS-416 viejo→nuevo, STOP si <75% (X3 r2).
  --phase before     Pools wide (top_k=50) de los 39 golds dev con embed-cache
                     (evals/s64_embed_cache.json — esta fase puebla, after lee).
                     Marca afectados: 3 viejos (por source_file) + needs_review
                     (por document_id, F8c r1).
  --phase apply      Mutación en `documents`/`chunks_v2` con re-lectura verificada
                     de cada paso (X1 r2: status explícito). Escribe
                     evals/s64_apply_log.yaml con los ids (insumo del rollback).
  --phase after      Pools con el MISMO embed-cache → diff vs before → criterios
                     C1/C2/C2'/C3 (convergencia anti-dado-de-red en no-afectados
                     con diff: re-run; si converge a before → reclasificado).
  --phase rollback   Deshace apply leyendo s64_apply_log.yaml (status back,
                     punteros NULL, document_id NULL, DELETE filas nuevas).

Artefactos: evals/s64_precheck.yaml · evals/s64_pools_{before,after}.json ·
evals/s64_apply_log.yaml · evals/s64_lifecycle46_report.yaml
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import json
import re
import sys
import uuid
from collections import Counter
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", str(ROOT / "evals" / "s64_embed_cache.json"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store  # noqa: E402
from strict_match import norm_ocr  # noqa: E402

URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
EVALS = ROOT / "evals"

F_PRECHECK = EVALS / "s64_precheck.yaml"
F_BEFORE = EVALS / "s64_pools_before.json"
F_AFTER = EVALS / "s64_pools_after.json"
F_APPLY = EVALS / "s64_apply_log.yaml"
F_REPORT = EVALS / "s64_lifecycle46_report.yaml"

# --- Población del #46 (ids verificados en s64_state46.py, 12 jun) -----------
OLD_DOCS = {
    "mad472_v1": {
        "doc_id": "43f4091d-1e7c-46b5-a8e9-a767ae3656a9",
        "source_file": "55347200 Manual Sirena Analogica MAD-472 ES GB FR GB IT",
    },
    "mc380_b": {
        "doc_id": "bc6bdd33-72e6-4054-9ce4-60583be4b5c4",
        "source_file": "CAD-250-MC-380-es",
    },
    "ms416_2020": {
        "doc_id": "03b1ccf6-10cc-43a3-9041-4a2d42be0bc2",
        "source_file": "CAD-250-MS-416-es",
    },
}
MAD472_V2_ID = "27dec7c7-4277-41a8-891a-a3ada52eeb7a"

NEW_DOCS = {
    "mc380_c": {
        "source_file": "CAD-250_Manual-Configuracion-MC-380-es-2026-c",
        "row": {
            "document_family": "CAD 250 MC 380",       # F2 r1: NOT NULL, copiada
            "revision": "c",
            "revision_date": "2026-04-23",             # control de revisiones p2 (s63)
            "language": "es",
            "doc_type": None,
            "manufacturer": "Detnov",
            "product_model": "CAD-250",
            "source_pdf_filename": "CAD-250_Manual-Configuracion-MC-380-es-2026-c.pdf",
            "source_pdf_sha256": "3797d14d071d618d2a6b0343dfb3d0e4bc4a8cebe75016fce5206cd9687ab68e",
            "status": "active",
            "supersedes_id": OLD_DOCS["mc380_b"]["doc_id"],
            "notes": "s64 #46: backfill identidad (lote Detnov jun, pipeline no crea filas); "
                     "supersede de CAD-250-MC-380-es rev-b. sha verificado disco+portal 12-jun.",
        },
        "extraction_sha256": "3797d14d071d618d2a6b0343dfb3d0e4bc4a8cebe75016fce5206cd9687ab68e",
        "expected_chunks": 136,
    },
    "ms416_2026": {
        "source_file": "CAD-250_Manual-software-configuracion-MS-416-es-2026-b",
        "row": {
            "document_family": "CAD 250 MS 416",
            "revision": "b",                            # filename oficial Detnov
            "revision_date": None,                      # tabla interna rota (lección #33)
            "language": "es",
            "doc_type": None,
            "manufacturer": "Detnov",
            "product_model": "CAD-250",
            "source_pdf_filename": "CAD-250_Manual-software-configuracion-MS-416-es-2026-b.pdf",
            "source_pdf_sha256": "e1985c3d8cfb74b30c45a9524b9afd1547a3d1df72c068998a227e37f3d673c8",
            "status": "active",
            "supersedes_id": OLD_DOCS["ms416_2020"]["doc_id"],
            "notes": "s64 #46: backfill identidad; supersede de CAD-250-MS-416-es (2020, "
                     "solo-250) — vigencia anclada en contenido p12 (curación Alberto s63). "
                     "sha verificado disco+portal 12-jun.",
        },
        "extraction_sha256": "e1985c3d8cfb74b30c45a9524b9afd1547a3d1df72c068998a227e37f3d673c8",
        "expected_chunks": 88,
    },
}

# Hechos-gold pre-registrados (diseño §2.3; quotes de cat019 pp.60/61/12 + hp001)
GOLD_FACT_KEYWORDS = {
    "cat019": ["maniobra", "coincidencias", "100.000", "sectorizac"],
    "hp001": ["candado", "2222"],
}
SUCCESSOR_MC380 = NEW_DOCS["mc380_c"]["source_file"]

OLD_SOURCE_FILES = {v["source_file"] for v in OLD_DOCS.values()}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git() -> str | None:
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def get(table: str, params: dict) -> list[dict]:
    r = httpx.get(f"{URL}/rest/v1/{table}", headers=H, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def patch(table: str, filters: dict, body: dict) -> list[dict]:
    r = httpx.patch(f"{URL}/rest/v1/{table}", headers={**H, "Prefer": "return=representation"},
                    params=filters, json=body, timeout=120)
    r.raise_for_status()
    return r.json()


def post(table: str, body: dict) -> list[dict]:
    r = httpx.post(f"{URL}/rest/v1/{table}", headers={**H, "Prefer": "return=representation"},
                   json=body, timeout=60)
    r.raise_for_status()
    return r.json()


def delete(table: str, filters: dict) -> None:
    r = httpx.delete(f"{URL}/rest/v1/{table}", headers=H, params=filters, timeout=60)
    r.raise_for_status()


# ============================================================================
# precheck
# ============================================================================

def _norm_title(t: str) -> str:
    t = norm_ocr(t or "").lower()
    t = re.sub(r"^[\d.\s\-–—]+", "", t)          # números de sección fuera
    t = re.sub(r"[^a-z0-9áéíóúüñ ]", " ", t)
    return " ".join(t.split())


def _title_tokens(t: str) -> set[str]:
    return {w for w in _norm_title(t).split() if len(w) > 2}


def phase_precheck() -> int:
    out = {"ts": _now(), "git": _git(), "checks": {}}
    stop = False

    # 1) hechos-gold en el sucesor MC-380-2026-c (F3 r1)
    facts = {}
    for qid, kws in GOLD_FACT_KEYWORDS.items():
        per_kw = {}
        for kw in kws:
            rows = get("chunks_v2", {
                "select": "id", "source_file": f"eq.{SUCCESSOR_MC380}",
                "content": f"ilike.*{kw}*", "limit": "50"})
            per_kw[kw] = len(rows)
        missing = [k for k, n in per_kw.items() if n == 0]
        facts[qid] = {"hits_por_keyword": per_kw, "missing": missing}
        if missing:
            stop = True
    out["checks"]["hechos_gold_en_sucesor_mc380c"] = facts

    # hp001 mitigación adicional declarada: candado/2222 también en MI-372 (activo)
    mi372 = {}
    for kw in GOLD_FACT_KEYWORDS["hp001"]:
        rows = get("chunks_v2", {
            "select": "id,source_file", "source_file": "ilike.*MI-372*",
            "content": f"ilike.*{kw}*", "limit": "20"})
        mi372[kw] = len(rows)
    out["checks"]["hp001_mitigacion_mi372"] = mi372

    # 2) cobertura de secciones MS-416 viejo → nuevo (X3 r2; umbral 75%)
    old_rows = get("chunks_v2", {
        "select": "section_title,content",
        "source_file": f"eq.{OLD_DOCS['ms416_2020']['source_file']}", "limit": "500"})
    new_rows = get("chunks_v2", {
        "select": "section_title,content",
        "source_file": f"eq.{NEW_DOCS['ms416_2026']['source_file']}", "limit": "500"})

    old_titles = sorted({_norm_title(r["section_title"]) for r in old_rows
                         if r.get("section_title") and _norm_title(r["section_title"])})
    new_title_set = {_norm_title(r["section_title"]) for r in new_rows
                     if r.get("section_title")}
    new_token_sets = [_title_tokens(r["section_title"]) for r in new_rows
                      if r.get("section_title")]

    def covered(title: str) -> bool:
        if title in new_title_set:
            return True
        tok = _title_tokens(title)
        if not tok:
            return False
        for nt in new_token_sets:
            if not nt:
                continue
            j = len(tok & nt) / len(tok | nt)
            if j >= 0.5:
                return True
        return False

    not_covered = [t for t in old_titles if not covered(t)]
    ratio = 1 - (len(not_covered) / len(old_titles)) if old_titles else None
    out["checks"]["cobertura_secciones_ms416"] = {
        "titulos_viejo": len(old_titles),
        "titulos_no_cubiertos": not_covered,
        "cobertura": round(ratio, 3) if ratio is not None else None,
        "umbral_prereg": 0.75,
    }
    if ratio is not None and ratio < 0.75:
        stop = True

    # señal secundaria informativa (no decisoria): shingle-coverage viejo→nuevo
    def shingles(rows: list[dict], w: int = 8) -> set[int]:
        text = norm_ocr(" ".join(r.get("content") or "" for r in rows)).lower().split()
        return {hash(" ".join(text[i:i + w])) for i in range(0, max(0, len(text) - w))}

    sh_old, sh_new = shingles(old_rows), shingles(new_rows)
    out["checks"]["shingle_coverage_informativa"] = {
        "viejo_en_nuevo": round(len(sh_old & sh_new) / len(sh_old), 3) if sh_old else None}

    out["verdict"] = "STOP" if stop else "GO"
    F_PRECHECK.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False),
                          encoding="utf-8")
    print(yaml.safe_dump(out, allow_unicode=True, sort_keys=False))
    print(f"precheck → {out['verdict']}  ({F_PRECHECK})")
    return 1 if stop else 0


# ============================================================================
# pools (before / after)
# ============================================================================

def _needs_review_ids() -> set[str]:
    rows = get("documents", {"select": "id", "status": "neq.active", "limit": "2000"})
    return {r["id"] for r in rows}


def _light(c: dict) -> dict:
    return {"id": c.get("id"), "source_file": c.get("source_file"),
            "product_model": c.get("product_model"),
            "document_id": c.get("document_id"),
            "similarity": c.get("similarity")}


def _run_pools() -> dict[str, list[dict]]:
    from src.rag.retriever import retrieve_chunks
    golds = {g["qid"]: g for g in gold_store.dev()}
    pools = {}
    for qid in sorted(golds):
        pools[qid] = retrieve_chunks(golds[qid]["question"], top_k=50)
        print(f"  {qid}: n={len(pools[qid])}")
    return pools


def _mark_affected(pools: dict[str, list[dict]], inactive_ids: set[str]) -> dict:
    marks = {}
    for qid, pool in pools.items():
        old_hits = [c.get("source_file") for c in pool
                    if c.get("source_file") in OLD_SOURCE_FILES]
        nr_hits = [c.get("id") for c in pool
                   if c.get("document_id") and c["document_id"] in inactive_ids]
        if old_hits or nr_hits:
            marks[qid] = {"docs_viejos_en_pool": sorted(set(old_hits)),
                          "chunks_de_docs_inactivos": nr_hits}
    return marks


def phase_before() -> int:
    print(f"pools BEFORE | git={_git()} | cache={os.environ['EMBED_CACHE_PATH']}")
    pools = _run_pools()
    inactive = _needs_review_ids()
    data = {
        "ts": _now(), "git": _git(), "phase": "before",
        "afectados": _mark_affected(pools, inactive),
        "pools": {qid: {"n": len(p), "ids": [c.get("id") for c in p],
                        "pool": [_light(c) for c in p]} for qid, p in pools.items()},
    }
    F_BEFORE.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"afectados (esperados): {json.dumps(data['afectados'], indent=1, ensure_ascii=False)}")
    print(f"→ {F_BEFORE}")
    return 0


# ============================================================================
# apply
# ============================================================================

def phase_apply() -> int:
    if F_APPLY.exists():
        sys.exit(f"{F_APPLY} ya existe — apply ya corrió. Usa rollback primero si "
                 "quieres repetir (idempotencia defensiva).")
    log: dict = {"ts": _now(), "git": _git(), "steps": []}

    def step(name: str, detail: dict) -> None:
        log["steps"].append({"step": name, **detail})
        print(f"  ✓ {name}: {json.dumps(detail, ensure_ascii=False)[:160]}")

    try:
        # -- 1) INSERT filas nuevas (sucesores Detnov) ------------------------
        for key, nd in NEW_DOCS.items():
            new_id = str(uuid.uuid4())
            body = {"id": new_id, **nd["row"]}
            created = post("documents", body)
            assert len(created) == 1 and created[0]["id"] == new_id, created
            # re-lectura verificada
            back = get("documents", {"select": "id,status,supersedes_id,document_family",
                                     "id": f"eq.{new_id}"})
            assert back and back[0]["status"] == "active" \
                and back[0]["supersedes_id"] == nd["row"]["supersedes_id"], back
            nd["new_id"] = new_id
            step(f"insert_{key}", {"id": new_id,
                                   "supersedes_id": nd["row"]["supersedes_id"]})

        # -- 2) UPDATE chunks_v2.document_id por extraction_sha256 ------------
        for key, nd in NEW_DOCS.items():
            rows = patch("chunks_v2",
                         {"extraction_sha256": f"eq.{nd['extraction_sha256']}",
                          "select": "id"},
                         {"document_id": nd["new_id"]})
            n = len(rows)
            assert n == nd["expected_chunks"], \
                f"{key}: {n} chunks actualizados, esperados {nd['expected_chunks']}"
            back = get("chunks_v2", {"select": "id",
                                     "document_id": f"eq.{nd['new_id']}", "limit": "1000"})
            assert len(back) == nd["expected_chunks"], len(back)
            step(f"link_chunks_{key}", {"document_id": nd["new_id"], "n": n})

        # -- 3) UPDATE viejos: status EXPLÍCITO + puntero (X1 r2) -------------
        chain = {
            OLD_DOCS["mad472_v1"]["doc_id"]: MAD472_V2_ID,
            OLD_DOCS["mc380_b"]["doc_id"]: NEW_DOCS["mc380_c"]["new_id"],
            OLD_DOCS["ms416_2020"]["doc_id"]: NEW_DOCS["ms416_2026"]["new_id"],
        }
        for old_id, new_id in chain.items():
            rows = patch("documents", {"id": f"eq.{old_id}", "select": "id"},
                         {"status": "superseded", "superseded_by_id": new_id})
            assert len(rows) == 1, rows
            back = get("documents", {"select": "id,status,superseded_by_id",
                                     "id": f"eq.{old_id}"})
            assert back[0]["status"] == "superseded" \
                and back[0]["superseded_by_id"] == new_id, back  # status, no punteros
            step("supersede", {"old_id": old_id, "superseded_by_id": new_id})

        # -- 4) V2 del MAD-472: supersedes_id --------------------------------
        rows = patch("documents", {"id": f"eq.{MAD472_V2_ID}", "select": "id"},
                     {"supersedes_id": OLD_DOCS["mad472_v1"]["doc_id"]})
        assert len(rows) == 1, rows
        step("mad472_v2_supersedes", {"id": MAD472_V2_ID,
                                      "supersedes_id": OLD_DOCS["mad472_v1"]["doc_id"]})

        log["result"] = "OK"
    except Exception as e:
        log["result"] = f"FAILED: {type(e).__name__}: {e}"
        F_APPLY.write_text(yaml.safe_dump(log, allow_unicode=True, sort_keys=False),
                           encoding="utf-8")
        print(f"\nAPPLY FALLÓ a mitad — log parcial en {F_APPLY}. "
              "Ejecuta --phase rollback para deshacer los pasos completados.")
        raise

    F_APPLY.write_text(yaml.safe_dump(log, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
    print(f"apply OK → {F_APPLY}")
    return 0


# ============================================================================
# after (+ veredicto C1/C2/C2'/C3)
# ============================================================================

def phase_after() -> int:
    if not F_BEFORE.exists():
        sys.exit("falta s64_pools_before.json — corre --phase before primero")
    before = json.loads(F_BEFORE.read_text(encoding="utf-8"))

    print(f"pools AFTER | git={_git()} | cache={os.environ['EMBED_CACHE_PATH']}")
    pools = _run_pools()

    # convergencia anti-dado-de-red (patrón s63): no-afectado con diff → re-run
    afectados_esperados = set(before["afectados"].keys())
    reclasificados = {}
    for qid, p in list(pools.items()):
        ids_b = before["pools"][qid]["ids"]
        ids_a = [c.get("id") for c in p]
        if ids_a != ids_b and qid not in afectados_esperados:
            from src.rag.retriever import retrieve_chunks
            golds = {g["qid"]: g for g in gold_store.dev()}
            p2 = retrieve_chunks(golds[qid]["question"], top_k=50)
            if [c.get("id") for c in p2] == ids_b:
                pools[qid] = p2
                reclasificados[qid] = "dado-de-red (re-run convergió a before)"
                print(f"  reclasificado {qid}: identico (dado-de-red)")
            else:
                pools[qid] = p2  # diff estable: se reporta con el pool re-corrido

    inactive = _needs_review_ids()  # ahora incluye los 3 superseded
    data = {
        "ts": _now(), "git": _git(), "phase": "after",
        "reclasificados": reclasificados,
        "pools": {qid: {"n": len(p), "ids": [c.get("id") for c in p],
                        "pool": [_light(c) for c in p]} for qid, p in pools.items()},
    }
    F_AFTER.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    # ---- veredicto -----------------------------------------------------------
    verdict: dict = {"ts": _now(), "git": _git(),
                     "design": "evals/_s64_lifecycle46_design.md (v3)",
                     "criterios": {}}

    # C1: ningún doc viejo en ningún pool after
    c1_viol = {qid: [c["source_file"] for c in d["pool"]
                     if c.get("source_file") in OLD_SOURCE_FILES]
               for qid, d in data["pools"].items()}
    c1_viol = {q: v for q, v in c1_viol.items() if v}
    verdict["criterios"]["C1_viejos_fuera"] = {"pass": not c1_viol, "violaciones": c1_viol}

    # C2/C2': sucesores presentes donde los viejos estaban (cat019, cat024) +
    # keyword-gold del sucesor en el top-15 servido de cat019
    succ_mc380 = NEW_DOCS["mc380_c"]["source_file"]
    c2 = {}
    for qid in sorted(afectados_esperados | {"cat019", "cat024"}):
        if qid not in data["pools"]:
            continue
        pool = data["pools"][qid]["pool"]
        c2[qid] = {
            "sucesor_mc380c_en_pool": any(c.get("source_file") == succ_mc380 for c in pool),
            "ms416_2026_en_pool": any(
                c.get("source_file") == NEW_DOCS["ms416_2026"]["source_file"] for c in pool),
            "mad472_v2_en_pool": any(
                "MAD-472 ES GB FR IT_V2" in (c.get("source_file") or "") for c in pool),
        }
    # cat019: keyword-gold en chunk del sucesor dentro del top-15 servido
    if "cat019" in pools:
        top15 = pools["cat019"][:15]
        hit = False
        for c in top15:
            if c.get("source_file") == succ_mc380:
                text = norm_ocr(c.get("content") or "").lower()
                if any(kw.lower() in text for kw in GOLD_FACT_KEYWORDS["cat019"]):
                    hit = True
                    break
        c2["cat019"]["keyword_gold_sucesor_en_top15_servido"] = hit
    verdict["criterios"]["C2_C2p_sucesores"] = c2

    # C3: no-afectados → pool idéntico (tras convergencia)
    c3_viol = {}
    for qid, d in data["pools"].items():
        if qid in afectados_esperados:
            continue
        if d["ids"] != before["pools"][qid]["ids"]:
            b_set, a_set = set(before["pools"][qid]["ids"]), set(d["ids"])
            c3_viol[qid] = {"solo_before": len(b_set - a_set),
                            "solo_after": len(a_set - b_set),
                            "orden_cambiado": b_set == a_set}
    verdict["criterios"]["C3_no_afectados_identicos"] = {
        "pass": not c3_viol, "violaciones": c3_viol,
        "reclasificados_dado_red": reclasificados,
        "atribucion_si_stop": "código main + datos nuevos (pre-declarada, F8a r1)"}

    # afectados: resumen del diff para revisión
    diff_afectados = {}
    for qid in sorted(afectados_esperados):
        if qid not in data["pools"]:
            continue
        b_ids, a_ids = before["pools"][qid]["ids"], data["pools"][qid]["ids"]
        diff_afectados[qid] = {
            "before_n": len(b_ids), "after_n": len(a_ids),
            "marcas_before": before["afectados"][qid],
            "salieron": len(set(b_ids) - set(a_ids)),
            "entraron": len(set(a_ids) - set(b_ids)),
        }
    verdict["afectados_diff"] = diff_afectados

    # fingerprint extendido (dimensión lifecycle — diseño §3)
    st = Counter(r["status"] for r in get(
        "documents", {"select": "status", "limit": "2000"}))
    inact_docs = get("documents", {"select": "id", "status": "neq.active", "limit": "2000"})
    n_excl = 0
    for d in inact_docs:
        rows = httpx.get(f"{URL}/rest/v1/chunks_v2",
                         headers={**H, "Prefer": "count=exact", "Range": "0-0"},
                         params={"select": "id", "document_id": f"eq.{d['id']}"},
                         timeout=30)
        cr = rows.headers.get("content-range", "*/0")
        n_excl += int(cr.split("/")[-1]) if "/" in cr else 0
    verdict["fingerprint_lifecycle"] = {
        "documents_status": dict(st),
        "chunks_excluded_by_lifecycle": n_excl,
    }

    all_pass = (verdict["criterios"]["C1_viejos_fuera"]["pass"]
                and verdict["criterios"]["C3_no_afectados_identicos"]["pass"])
    verdict["verdict"] = "GO (C1+C3 pass; revisar C2/diff de afectados arriba)" \
        if all_pass else "STOP — revisar violaciones (atribución pre-declarada)"
    F_REPORT.write_text(yaml.safe_dump(verdict, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    print(yaml.safe_dump(verdict, allow_unicode=True, sort_keys=False))
    print(f"→ {F_REPORT}")
    return 0 if all_pass else 1


# ============================================================================
# rollback
# ============================================================================

def phase_rollback() -> int:
    if not F_APPLY.exists():
        sys.exit("no hay s64_apply_log.yaml — nada que deshacer")
    log = yaml.safe_load(F_APPLY.read_text(encoding="utf-8"))
    steps = log.get("steps", [])
    # deshacer en orden inverso
    for s in reversed(steps):
        name = s["step"]
        if name == "mad472_v2_supersedes":
            patch("documents", {"id": f"eq.{s['id']}", "select": "id"},
                  {"supersedes_id": None})
            print(f"  ✓ undo {name}")
        elif name == "supersede":
            patch("documents", {"id": f"eq.{s['old_id']}", "select": "id"},
                  {"status": "active", "superseded_by_id": None})
            print(f"  ✓ undo supersede {s['old_id']}")
        elif name.startswith("link_chunks_"):
            patch("chunks_v2", {"document_id": f"eq.{s['document_id']}", "select": "id"},
                  {"document_id": None})
            print(f"  ✓ undo {name}")
        elif name.startswith("insert_"):
            delete("documents", {"id": f"eq.{s['id']}"})
            print(f"  ✓ undo {name} (DELETE)")
    F_APPLY.rename(F_APPLY.with_suffix(".rolledback.yaml"))
    print("rollback completo — apply_log renombrado .rolledback.yaml")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["precheck", "before", "apply", "after", "rollback"])
    args = ap.parse_args()
    return {"precheck": phase_precheck, "before": phase_before, "apply": phase_apply,
            "after": phase_after, "rollback": phase_rollback}[args.phase]()


if __name__ == "__main__":
    sys.exit(main())
