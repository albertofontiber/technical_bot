import ast
from pathlib import Path

import pytest

from src.rag import coverage_runtime, serving_pipeline
from src.rag.serving_pipeline import RagServingAdapters, execute_rag_turn


def _run(monkeypatch, apply_coverage, *, observe=lambda _query, _chunks: None):
    generated = {}
    monkeypatch.setattr(
        serving_pipeline,
        "apply_profiled_post_rerank_coverage",
        apply_coverage,
    )

    def generate(_query, chunks, *, available_models=None):
        generated["chunks"] = chunks
        return {"answer": "ok", "diagrams": []}

    result = execute_rag_turn(
        query="q",
        query_for_retrieval="q",
        target_models=None,
        available_models=None,
        retrieval_top_k=50,
        rerank_top_k=2,
        adapters=RagServingAdapters(
            retrieve=lambda _query, **_kwargs: [
                {"id": "a", "content": "A"},
                {"id": "b", "content": "B"},
            ],
            rerank=lambda _query, chunks, **_kwargs: list(chunks),
            observe_structural_shadow=observe,
            generate=generate,
        ),
    )
    return result, generated["chunks"]


def test_coverage_cannot_reorder_the_protected_prefix(monkeypatch):
    def malicious(_query, chunks, *, retrieval_pool):
        del retrieval_pool
        return [chunks[1], chunks[0]], {"status": "appended"}

    result, generated = _run(monkeypatch, malicious)

    assert [row["id"] for row in generated] == ["a", "b"]
    assert result["coverage_trace"]["status"] == "error"
    assert result["coverage_trace"]["error_type"] == "ValueError"


def test_coverage_cannot_mutate_the_protected_prefix_in_place(monkeypatch):
    def malicious(_query, chunks, *, retrieval_pool):
        del retrieval_pool
        chunks[0]["content"] = "MUTATED"
        return chunks, {"status": "no_append"}

    result, generated = _run(monkeypatch, malicious)

    assert generated[0]["content"] == "A"
    assert result["coverage_trace"]["status"] == "error"


def test_coverage_append_capacity_and_identity_are_enforced(monkeypatch):
    def overflow(_query, chunks, *, retrieval_pool):
        del retrieval_pool
        return chunks + [{"id": str(index)} for index in range(5)], {
            "status": "appended"
        }

    result, generated = _run(monkeypatch, overflow)

    assert [row["id"] for row in generated] == ["a", "b"]
    assert result["coverage_trace"]["status"] == "error"


def test_shadow_cannot_mutate_the_prefix_seen_by_coverage_or_generation(monkeypatch):
    def shadow(_query, chunks):
        chunks.reverse()
        chunks[0]["content"] = "MUTATED"

    def inert(_query, chunks, *, retrieval_pool):
        del retrieval_pool
        return chunks, {"status": "disabled_or_not_applicable", "lanes": []}

    result, generated = _run(monkeypatch, inert, observe=shadow)

    assert [row["id"] for row in generated] == ["a", "b"]
    assert generated[0]["content"] == "A"
    assert result["coverage_trace"]["protected_prefix_equal"] is True


def test_valid_append_gets_a_recomputed_truthful_receipt(monkeypatch):
    def valid(_query, chunks, *, retrieval_pool):
        del retrieval_pool
        return chunks + [{"id": "c", "content": "C"}], {
            "status": "appended",
            "protected_prefix_rows": 999,
            "protected_prefix_equal": False,
            "appended_ids": ["lie"],
            "lanes": [],
        }

    result, generated = _run(monkeypatch, valid)

    assert [row["id"] for row in generated] == ["a", "b", "c"]
    assert result["coverage_trace"]["protected_prefix_rows"] == 2
    assert result["coverage_trace"]["protected_prefix_equal"] is True
    assert result["coverage_trace"]["appended_ids"] == ["c"]


def test_coverage_cannot_append_an_identity_already_in_the_prefix(monkeypatch):
    def collision(_query, chunks, *, retrieval_pool):
        del retrieval_pool
        return chunks + [{"id": "a", "content": "duplicate"}], {
            "status": "appended"
        }

    result, generated = _run(monkeypatch, collision)

    assert [row["id"] for row in generated] == ["a", "b"]
    assert result["coverage_trace"]["status"] == "error"


@pytest.mark.parametrize(
    ("extra_rows", "status"),
    [([{"id": "c"}], "no_append"), ([], "appended")],
)
def test_coverage_status_must_match_the_actual_append(monkeypatch, extra_rows, status):
    def contradictory(_query, chunks, *, retrieval_pool):
        del retrieval_pool
        return chunks + extra_rows, {"status": status}

    result, generated = _run(monkeypatch, contradictory)

    assert [row["id"] for row in generated] == ["a", "b"]
    assert result["coverage_trace"]["status"] == "error"


def test_serving_adapters_do_not_accept_a_coverage_or_selector_override():
    base = {
        "retrieve": lambda *_args, **_kwargs: [],
        "rerank": lambda *_args, **_kwargs: [],
        "observe_structural_shadow": lambda *_args: None,
        "generate": lambda *_args, **_kwargs: {},
    }
    with pytest.raises(TypeError):
        RagServingAdapters(**base, apply_coverage=lambda *_args: None)
    with pytest.raises(TypeError):
        RagServingAdapters(**base, structural_collector=lambda *_args: None)
    with pytest.raises(TypeError):
        RagServingAdapters(**base, document_local_collector=lambda *_args: None)


def test_profiled_facade_keeps_the_real_selector_when_fetch_is_injected(monkeypatch):
    from src.rag import document_local_coverage

    marker = object()
    document_marker = object()
    observed = {}

    def fetcher(*_args, **_kwargs):
        return [], [], {"fetch": "ok"}

    def document_fetcher(*_args, **_kwargs):
        return [], [], {"fetch": "document-ok"}

    def selector(query, seeds, *, fetcher):
        observed.update(query=query, seeds=seeds, fetcher=fetcher)
        return marker

    def document_selector(query, anchors, covered, *, fetcher):
        observed.update(
            document_query=query,
            document_anchors=anchors,
            document_covered=covered,
            document_fetcher=fetcher,
        )
        return document_marker

    def coverage(
        _query,
        reranked,
        *,
        retrieval_pool,
        structural_collector,
        document_local_collector,
    ):
        assert retrieval_pool == [{"id": "pool"}]
        assert structural_collector("q", reranked) is marker
        assert document_local_collector("q", reranked, reranked) is document_marker
        return reranked, {"status": "no_append"}

    monkeypatch.setattr(coverage_runtime, "collect_structural_coverage", selector)
    monkeypatch.setattr(coverage_runtime, "DOCUMENT_LOCAL_COVERAGE", True)
    monkeypatch.setattr(
        document_local_coverage, "collect_document_local_coverage", document_selector
    )
    monkeypatch.setattr(
        coverage_runtime, "apply_post_rerank_coverage_with_trace", coverage
    )

    served, trace = coverage_runtime.apply_profiled_post_rerank_coverage(
        "q",
        [{"id": "a"}],
        retrieval_pool=[{"id": "pool"}],
        structural_fetcher=fetcher,
        document_local_fetcher=document_fetcher,
    )

    assert served == [{"id": "a"}]
    assert trace == {"status": "no_append"}
    assert observed["fetcher"] is fetcher
    assert observed["document_fetcher"] is document_fetcher


def test_user_facing_eval_and_smoke_harnesses_cross_the_serving_seam():
    root = Path(__file__).resolve().parents[1]
    cases = (
        ("scripts/test_bot_vs_gold.py", "run_bot"),
        ("scripts/smoke_test.py", "run_query"),
    )
    for relative, function_name in cases:
        source = (root / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        )
        called_names = []
        for node in ast.walk(function):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                called_names.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.append(node.func.attr)
        assert called_names.count("execute_rag_turn") == 1
        for bypass in (
            "retrieve_chunks",
            "rerank",
            "rerank_chunks",
            "generate_answer",
        ):
            assert bypass not in called_names


def test_serving_eval_keeps_process_release_profile_authoritative():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse(
        (root / "scripts/test_bot_vs_gold.py").read_text(encoding="utf-8")
    )
    load_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "load_dotenv"
    ]
    assert len(load_calls) == 1
    override = next(
        keyword.value
        for keyword in load_calls[0].keywords
        if keyword.arg == "override"
    )
    assert isinstance(override, ast.Constant) and override.value is False
