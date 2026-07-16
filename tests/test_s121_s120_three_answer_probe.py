import importlib.util
from pathlib import Path

import yaml


def _module():
    path = Path("scripts/s121_s120_three_answer_probe.py")
    spec = importlib.util.spec_from_file_location("s121_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preregistration_is_exactly_three_calls_and_no_upstream_work():
    prereg = yaml.safe_load(
        Path("evals/s121_s120_three_answer_probe_prereg_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert prereg["authorization"]["authorized_qids"] == ["hp005", "hp009", "hp017"]
    assert prereg["scope"]["maximum_fresh_generator_calls"] == 3
    assert prereg["scope"]["retrieval_calls"] == 0
    assert prereg["scope"]["reranker_calls"] == 0
    assert prereg["scope"]["database_writes"] == 0


def test_diagnostic_surface_checks_cover_exact_four_claims():
    module = _module()
    answers = {
        "hp005": "Seleccione Circuito Sirena 1 y pulse Activar; seleccione equipos del lazo.",
        "hp009": "Es un lazo cerrado: Inicio Lazo OUT vuelve a Retorno.",
        "hp017": (
            "La Regla 1 indica que cualquier entrada de alarma activa todas las sirenas. "
            "Elimine las dos reglas por defecto."
        ),
    }
    rows = [claim for qid, answer in answers.items() for claim in module.fact_checks(qid, answer)]
    assert len(rows) == 4
    assert all(row["deterministic_surface_present"] for row in rows)


def test_generation_contract_hash_is_order_stable_and_content_sensitive():
    module = _module()
    assert module.stable_sha256({"b": 2, "a": 1}) == module.stable_sha256(
        {"a": 1, "b": 2}
    )
    assert module.stable_sha256({"a": 1}) != module.stable_sha256({"a": 2})
