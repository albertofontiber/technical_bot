"""s286e — el instrumento fact-level v3 cruza el seam de serving.

`scripts/factlevel_assessment.py` fija los DEMO_FLAGS y luego ASSERTA constantes de
`src.config` que se resuelven en import-time (`RERANK_TOP_K == 10`, `LLM_MAX_TOKENS == 3500`).
Importarlo dentro del proceso de pytest sería frágil: cualquier test anterior que ya haya
importado `src.config` congela esos valores con los defaults del repo (5 / 2048) y el módulo
abortaría. Por eso el comportamiento se ejerce en un SUBPROCESO hermético (mismo patrón que
`tests/test_c1_release_gate.py`), con adapters stubbeados: cero red, cero llamada de pago.
"""

import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = ROOT / "scripts/factlevel_assessment.py"
GENERATOR = ROOT / "src/rag/generator.py"

# Los 8 pines nuevos: los 7 flags-hoja env-resueltos del seam de coverage + el observer.
SEAM_LEAF_FLAGS = (
    "TABLE_PREAMBLE_CLOSURE",
    "CANONICAL_HYQ_COVERAGE",
    "COMPATIBILITY_BUNDLE_COVERAGE",
    "RERANK_POOL_COVERAGE",
    "STRUCTURAL_CASCADE_COVERAGE",
    "LOGICAL_RECORD_COVERAGE",
    "EVIDENCE_DERIVATION_OVERLAY",
    "STRUCTURAL_NEIGHBOR_SHADOW",
)


# ─────────────────────────── driver hermético ───────────────────────────
_DRIVER = r'''
import importlib.util, json, os, sys
from pathlib import Path

ROOT = Path(sys.argv[1])
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("fla", ROOT / "scripts/factlevel_assessment.py")
fla = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fla)

from src.rag import serving_pipeline
import src.rag.generator as gen

out = {"demo_flags": fla.DEMO_FLAGS, "instrument_version": fla.INSTRUMENT_VERSION}

# ── (f) freeze-contract del código: closure de imports del seam ──
fingerprint = fla.pipeline_fingerprint()
out["closure_modules"] = fingerprint["modules"]
out["closure_assets"] = fingerprint["assets"]

# ── (b) run_pipeline sobre el SEAM REAL con adapters stubbeados ──
POOL = [
    {"id": "p0", "content": "pool cero", "similarity": 0.9, "product_model": "fam"},
    {"id": "p1", "content": "pool uno", "similarity": 0.8, "product_model": "fam"},
    {"id": "p2", "content": "pool dos", "similarity": 0.2, "product_model": "fam"},
]
APPEND = {"id": "cov1", "content": "append content", "similarity": 0.01,
          "retrieval_lane": "structural_neighbor_coverage_v1", "product_model": "fam"}
seen = {"retrieve": 0, "rerank": 0, "generate": 0, "coverage": 0, "generated_ids": None,
        "rerank_strict": None}


def fake_retrieve(query, top_k=50, **kwargs):
    seen["retrieve"] += 1
    return [dict(row) for row in POOL[:top_k]]


def fake_rerank(query, chunks, top_k=10, strict=False, **kwargs):
    seen["rerank"] += 1
    seen["rerank_strict"] = strict
    return [dict(row) for row in chunks[:top_k]]


def fake_generate(query, chunks, available_models=None):
    seen["generate"] += 1
    seen["generated_ids"] = [row.get("id") for row in chunks]
    return {"answer": "respuesta", "diagrams": []}


def fake_coverage(query, reranked, *, retrieval_pool, **kwargs):
    seen["coverage"] += 1
    return list(reranked) + [dict(APPEND)], {
        "status": "appended",
        "lanes": [{"lane": "structural_neighbor_coverage_v1", "selected_ids": ["cov1"]}],
    }


fla.retrieve_chunks = fake_retrieve
fla.rerank = fake_rerank
fla.generate_answer = fake_generate
serving_pipeline.apply_profiled_post_rerank_coverage = fake_coverage
# la fila apendizada NO supera el umbral: entra SOLO por ser coverage validada
gen.is_validated_coverage_chunk = lambda chunk: chunk.get("id") == "cov1"

pipe = fla.run_pipeline("pregunta")
out["pipeline"] = {
    "pool_ids": pipe["pool_ids"],
    "topk_ids": pipe["topk_ids"],
    "served_ids": pipe["served_ids"],
    "appended_ids": pipe["appended_ids"],
    "chunk_ids": [row.get("id") for row in pipe["chunks"]],
    "appended_lane": pipe["appended_lane"],
    "coverage_status": pipe["coverage_status"],
    "coverage_degraded": pipe["coverage_degraded"],
    "answer": pipe["answer"],
    "seen": dict(seen),
}

# ── (d) coverage que errorea SIEMPRE: retry 1x y gold degradado ──
errors = {"n": 0}


def raising_coverage(query, reranked, *, retrieval_pool, **kwargs):
    errors["n"] += 1
    raise RuntimeError("lane rota")


serving_pipeline.apply_profiled_post_rerank_coverage = raising_coverage
degraded = fla.run_pipeline("pregunta")
out["degraded"] = {
    "coverage_degraded": degraded["coverage_degraded"],
    "coverage_status": degraded["coverage_status"],
    "coverage_attempts": errors["n"],
    "appended_ids": degraded["appended_ids"],
    "served_ids": degraded["served_ids"],
}
_EMPTY_HIST = {"OK": 1, "synthesis-miss": 0, "rerank-miss": 0, "retrieval-miss": 0,
               "corpus-gap": 0, "meta-ref": 0}
out["axis"] = fla.gold_juez_axis(
    [
        {"qid": "sano", "hist": dict(_EMPTY_HIST), "facts": [], "family_resolved": True,
         "coverage_degraded": False},
        {"qid": "roto", "hist": dict(_EMPTY_HIST), "facts": [], "family_resolved": True,
         "coverage_degraded": True},
    ],
    {},
)

# ── (c) clasificación: append servido, excerpt truncado, precedencia de rerank-miss ──
EXCERPTS = {}
fla.coverage_context_content = (
    lambda chunk, **kwargs: EXCERPTS.get(chunk.get("id"), chunk.get("content") or "")
)


def fake_judge_fact(valor, texto, chunks, workers=6):
    """Juez fake LÉXICO: acredita el chunk cuyo contenido contiene el valor.
    Sobre la vista servida el 'contenido' es el excerpt — ahí vive el split."""
    votes = {row["id"]: fla.K for row in chunks if valor in (row.get("content") or "")}
    return {"votes": votes, "models": ["fake"], "n_fail": 0}


fla.judge_fact = fake_judge_fact
fla.judge_conveyed21 = lambda valor, texto, answer, workers=6: {
    "yes": fla.K if valor in (answer or "") else 0, "n_fail": 0}
fla.judge_conveyed_dual = lambda valor, texto, answer, workers=5: {
    "yes": 0, "n_fail": 0, "n_valid": fla.K, "firm": False}
fla.target_servable = lambda gold: (True, {"target_tokens": []})
fla.fetch_manual_chunks = lambda targets: []
fla.gold_family = lambda *args, **kwargs: {"fam"}
fla.fam_norm = lambda value: value
fla.doc_tokens = lambda value: []
fla._pm_by_ids = lambda ids: {}
fla.measurable = lambda valor, texto: False        # no-anclable: sin guard L1 ni dual léxico
fla._is_meta_ref = lambda valor: False


def canned_pipe(pool, topk_ids, appended, answer):
    served = [row for row in [*pool, *appended] if row["id"] in {*topk_ids, *(a["id"] for a in appended)}]
    chunks = [row for row in pool if row["id"] in topk_ids] + list(appended)
    return {
        "answer": answer, "pool": pool, "topk": [r for r in pool if r["id"] in topk_ids],
        "served": served, "chunks": chunks, "appended": list(appended),
        "topk_ids": list(topk_ids), "served_ids": [r["id"] for r in served],
        "pool_ids": [r["id"] for r in pool],
        "appended_ids": [r["id"] for r in appended],
        "appended_lane": {r["id"]: r.get("retrieval_lane") for r in appended},
        "coverage_status": "appended", "coverage_degraded": False,
    }


def measure(valor, pipe, excerpts):
    EXCERPTS.clear()
    EXCERPTS.update(excerpts)
    fla.run_pipeline = lambda question: pipe
    gold = {"qid": "t", "question": "q", "_provenance": {"fuente": "doc.pdf"},
            "atomic_facts": [{"tipo": "core", "estado": "presente",
                              "valor": valor, "texto": "relacion"}]}
    result = fla.measure_gold(gold, workers=1, do_submotivo=False, do_stability=False)
    fact = result["facts"][0]
    return {"clase": fact["clase"], "hist": result["hist"],
            "via_coverage_append": fact.get("via_coverage_append"),
            "in_pool": fact.get("in_pool"), "in_topk": fact.get("in_topk"),
            "reaches_gen": fact.get("reaches_gen"),
            "submotivo": fact.get("submotivo")}


BASE_POOL = [{"id": "p0", "content": "prosa sin el dato", "similarity": 0.9,
              "product_model": "fam"}]
APPEND_ROW = {"id": "cov1", "content": "el append dice VALOR_A y tambien VALOR_B",
              "similarity": 0.01, "retrieval_lane": "structural_neighbor_coverage_v1",
              "product_model": "fam"}

# c1: soporte SOLO en el append servido, y sus excerpts SÍ lo llevan -> llega al generador
out["c_only_in_append"] = measure(
    "VALOR_A",
    canned_pipe(BASE_POOL, ["p0"], [APPEND_ROW], "la respuesta transmite VALOR_A"),
    {"cov1": "el append dice VALOR_A"},
)

# c2: el valor esta en el CONTENT del append pero fuera de sus excerpts servidos
out["c_view_truncated"] = measure(
    "VALOR_B",
    canned_pipe(BASE_POOL, ["p0"], [APPEND_ROW], "la respuesta no lo dice"),
    {"cov1": "el append dice VALOR_A"},
)

# c3: ademas hay soporte en pool-no-topk -> la senal UPSTREAM manda (r2-3)
BURIED_POOL = [
    {"id": "p0", "content": "prosa sin el dato", "similarity": 0.9, "product_model": "fam"},
    {"id": "p9", "content": "enterrado: VALOR_B", "similarity": 0.5, "product_model": "fam"},
]
out["c_rerank_wins"] = measure(
    "VALOR_B",
    canned_pipe(BURIED_POOL, ["p0"], [APPEND_ROW], "la respuesta no lo dice"),
    {"cov1": "el append dice VALOR_A"},
)

sys.stdout.write("<<<JSON>>>" + json.dumps(out))
'''


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    script = tmp_path_factory.mktemp("s286e") / "driver.py"
    script.write_text(_DRIVER, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    # Credenciales-placeholder: el modulo las exige en import-time y el driver no
    # hace ni una llamada de red (retrieve/rerank/generate/coverage van stubbeados).
    for name in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        env.setdefault(name, "test-placeholder")
    env["GENERATOR_INCLUDE_CONTEXT"] = ""      # el modulo assertea que esta apagado
    completed = subprocess.run(
        [sys.executable, str(script), str(ROOT)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300, check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "<<<JSON>>>" in completed.stdout, completed.stdout[-2000:]
    return json.loads(completed.stdout.split("<<<JSON>>>", 1)[1])


def _function(source: str, name: str):
    tree = ast.parse(source)
    return next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def _called_names(function) -> list[str]:
    names = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)
    return names


# ─────────────────── (a) paridad del filtro de admision ───────────────────
# Rama del pre-check 0: generator.py NO esta sha-pineado por ningun sello vivo
# (no aparece en EXPECTED_RUNTIME_INPUTS de tests/test_c1_release_gate.py ni en
# evals/s277_c1_live_reachability_receipt_v1.json; los sha de los prereg historicos
# son fotos, no contratos contra el arbol). Por eso el filtro se EXPORTA (spec r2-4)
# en vez de replicarse, y el anti-drift consiste en probar que hay UNA sola
# implementacion, no dos que puedan divergir.
def test_the_admission_filter_has_exactly_one_implementation():
    generator_source = GENERATOR.read_text(encoding="utf-8")
    assessment_source = ASSESSMENT.read_text(encoding="utf-8")

    generate = _function(generator_source, "generate_answer")
    assert "admitted_evidence_rows" in _called_names(generate), (
        "generate_answer dejo de usar el filtro exportado: el instrumento mediria otra vista"
    )
    # el cuerpo del generador ya no puede llevar una copia del predicado
    generate_body = ast.get_source_segment(generator_source, generate) or ""
    assert "RELEVANCE_THRESHOLD" not in generate_body
    assert generate_body.count("complete_compatibility_bundle") == 0

    admitted = _function(generator_source, "admitted_evidence_rows")
    admitted_body = ast.get_source_segment(generator_source, admitted) or ""
    for token in (
        "RELEVANCE_THRESHOLD",
        "is_validated_coverage_chunk",
        "complete_compatibility_bundle",
        "COMPATIBILITY_LANE",
    ):
        assert token in admitted_body, token

    # el instrumento IMPORTA la funcion y la usa; no define su propio umbral servido
    assert "admitted_evidence_rows" in assessment_source
    run_pipeline = _function(assessment_source, "run_pipeline")
    assert "admitted_evidence_rows" in _called_names(run_pipeline)
    assert "c.get(\"similarity\", 0) >= RELEVANCE_THRESHOLD" not in assessment_source, (
        "el instrumento volvio a replicar el umbral del generador (deriva r2-4)"
    )


def test_the_exported_filter_admits_validated_coverage_below_the_bar(monkeypatch):
    from src.rag import generator

    rows = [
        {"id": "a", "similarity": 0.9, "content": "alta"},
        {"id": "b", "similarity": 0.1, "content": "baja"},
        {"id": "c", "similarity": 0.01, "content": "coverage"},
    ]
    monkeypatch.setattr(
        generator, "is_validated_coverage_chunk", lambda chunk: chunk.get("id") == "c"
    )
    admitted = [row["id"] for row in generator.admitted_evidence_rows(rows)]
    assert admitted == ["a", "c"]


# ─────────────────── (e) DEMO_FLAGS pinea el flag-set del seam ───────────────────
def test_demo_flags_pin_the_whole_seam_flag_set(driver):
    flags = driver["demo_flags"]
    for name in SEAM_LEAF_FLAGS:
        assert flags.get(name) == "off", f"{name} sin pinear: un .env sucio mediria otra stack"
    # s287 P0: v3.0→v3.1 (kilo-bridge en el guard L1 — S5 cerrado, DEC-096c)
    assert driver["instrument_version"] == "v3.1"


# ─────────────────── (f) pipe_sha = closure del seam ───────────────────
def test_pipeline_fingerprint_covers_the_seam_closure(driver):
    modules = driver["closure_modules"]
    for expected in (
        "src/rag/serving_pipeline.py",
        "src/rag/post_rerank_coverage.py",
        "src/release_profiles.py",
        "src/rag/structural_neighbor_coverage.py",
        # el trio que v2.2 ya hasheaba NO se pierde
        "src/rag/retriever.py",
        "src/rag/reranker.py",
        "src/rag/generator.py",
    ):
        assert expected in modules, expected
    assert modules == sorted(modules), "el orden del closure debe ser estable"
    assert "config/structural_neighbor_coverage_v1.yaml" in driver["closure_assets"]


# ─────────────────── (b) run_pipeline expone la vista servida ───────────────────
def test_run_pipeline_exposes_pool_topk_served_and_appends(driver):
    pipeline = driver["pipeline"]
    seen = pipeline["seen"]

    assert seen["retrieve"] == 1 and seen["rerank"] == 1 and seen["generate"] == 1
    assert seen["rerank_strict"] is True, "el harness debe rerankear en modo estricto (patron bvg)"

    assert pipeline["pool_ids"] == ["p0", "p1", "p2"]          # capturado DENTRO del seam
    assert pipeline["topk_ids"] == ["p0", "p1", "p2"]          # prefijo protegido
    assert pipeline["appended_ids"] == ["cov1"]
    assert pipeline["chunk_ids"] == ["p0", "p1", "p2", "cov1"]
    # p2 (0.2) cae por umbral; cov1 (0.01) entra por ser coverage validada
    assert pipeline["served_ids"] == ["p0", "p1", "cov1"]
    assert pipeline["appended_lane"] == {"cov1": "structural_neighbor_coverage_v1"}
    assert pipeline["coverage_status"] == "appended"
    assert pipeline["coverage_degraded"] is False
    # el generador recibe la composicion COMPLETA (prefijo + appends), no la filtrada
    assert seen["generated_ids"] == ["p0", "p1", "p2", "cov1"]
    assert pipeline["answer"] == "respuesta"


# ─────────────────── (d) fail-open persistente ───────────────────
def test_persistent_coverage_error_degrades_and_is_excluded(driver):
    degraded = driver["degraded"]
    assert degraded["coverage_attempts"] == 2, "el fail-open debe reintentar exactamente 1 vez"
    assert degraded["coverage_status"] == "error"
    assert degraded["coverage_degraded"] is True
    assert degraded["appended_ids"] == []
    # el prefijo protegido sigue sirviendose (fail-open), pero el gold queda marcado
    assert degraded["served_ids"] == ["p0", "p1"]

    axis_qids = [row["qid"] for row in driver["axis"]]
    assert axis_qids == ["sano"], "un gold coverage_degraded no puede alimentar inferencias"


# ─────────────────── (c) clasificacion ───────────────────
def test_support_only_in_a_served_append_is_not_a_retrieval_miss(driver):
    case = driver["c_only_in_append"]
    assert case["in_pool"] is False and case["in_topk"] is False
    assert case["reaches_gen"] is True
    assert case["via_coverage_append"] is True
    assert case["clase"] == "OK"
    assert case["hist"]["retrieval-miss"] == 0 and case["hist"]["corpus-gap"] == 0


def test_value_outside_the_served_excerpts_is_append_view_truncated(driver):
    case = driver["c_view_truncated"]
    assert case["reaches_gen"] is False
    assert case["clase"] == "synthesis-miss"
    assert case["submotivo"]["submotivo"] == "append_view_truncated"
    assert case["submotivo"]["chunk_ids"] == ["cov1"]
    assert case["hist"]["retrieval-miss"] == 0 and case["hist"]["corpus-gap"] == 0


def test_append_view_truncated_never_outranks_rerank_miss(driver):
    case = driver["c_rerank_wins"]
    assert case["in_pool"] is True and case["in_topk"] is False
    assert case["clase"] == "rerank-miss"
    assert case["submotivo"] in ("pos-buried", "lexical-distractor")
