"""s287 V1 (cierre 2) — PARIDAD DE CLASE match-config ↔ card-config, POR LANE.

El defecto que cierra este test NO es un arquetipo concreto: es una CLASE.  Una
lane que puntúa candidatos con un *match-config* y fabrica sus cards con OTRO
*card-config* deja una grieta silenciosa — cualquier arquetipo añadido solo al
lado del match aprueba el gate, sale con ``coverage_cards: []`` y ``_attest``
(post_rerank_coverage.py) lo rechaza.  El síntoma es «la lane selecciona pero no
apendiza JAMÁS», y no lo caza ningún test de lane porque cada mitad es correcta
por separado.  Ocurrió de verdad en s287 con ``variant_differentiation``
(añadido a retrieval_facets_v3 + evidence_coverage_facets_v4, ausente de v2).

Contrato pineado: **por CADA lane**, todo arquetipo de SU match-config existe en
SU card-config.  NO se exige paridad ENTRE lanes: la fragmentación v2/v4/v5/
cascade es deliberada (vocabularios y políticas de alineación distintos por lane)
y exigirla rompería lanes vivas — el par de cada lane es la unidad correcta.

Los pares se LEEN del código que sirve (defaults de la firma / kwargs del call
site vía AST), nunca de una lista de rutas copiada a mano: una lista copiada
volvería a divergir exactamente igual que las configs.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.rag import post_rerank_coverage, rerank_pool_coverage
from src.rag.doc_scoped_hyq_coverage import (
    LANE as HYQ_LANE,
    collect_document_scoped_hyq,
)
from src.rag.evidence_coverage import (
    MULTIFACET_CONFIG,
    POOL_COMPLEMENT_CONFIG,
    STRICT_ALIGNED_CONFIG,
)
from src.rag.structural_neighbor_coverage import (
    CASCADED_EVIDENCE_CONFIG,
    select_structural_neighbors,
)

ROOT = Path(__file__).resolve().parents[1]


def _signature_default(function, parameter: str) -> Path:
    value = inspect.signature(function).parameters[parameter].default
    assert isinstance(value, Path), f"{parameter} must default to a Path"
    return value


def _call_kwarg_paths(
    module, function_name: str, callee_name: str, kwargs: tuple[str, ...]
) -> dict[str, Path]:
    """Resolve, vía AST, los kwargs de un call site real a rutas de config.

    Leer el CALL SITE (y no una constante recordada) es lo que hace que el test
    detecte el día en que alguien re-apunte el card-config de una lane.
    """
    source = Path(inspect.getsourcefile(module)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == callee_name
    ]
    assert len(calls) == 1, (
        f"{function_name} debe llamar a {callee_name} exactamente una vez "
        f"(encontradas {len(calls)}) — si eso cambia, revisa este contrato"
    )
    resolved: dict[str, Path] = {}
    for keyword in calls[0].keywords:
        if keyword.arg not in kwargs:
            continue
        assert isinstance(keyword.value, ast.Name), (
            f"{function_name}: {keyword.arg} debe ser una constante de módulo"
        )
        value = getattr(module, keyword.value.id)
        assert isinstance(value, Path)
        resolved[keyword.arg] = value
    assert set(resolved) == set(kwargs), (
        f"{function_name}: faltan kwargs explícitos {set(kwargs) - set(resolved)}"
    )
    return resolved


def _served_lane_pairs() -> dict[str, dict[str, Path]]:
    """(match_config, card_config) POR LANE, leídos del código que sirve."""
    cascade = _call_kwarg_paths(
        post_rerank_coverage,
        "collect_cascaded_structural_coverage",
        "select_structural_neighbors",
        ("evidence_match_config_path", "evidence_card_config_path"),
    )
    return {
        # structural_neighbor_coverage.py:189-190 — la lane structural entra por
        # los DEFAULTS de la firma (collect_structural_coverage no los pasa).
        "same_blob_structural_neighbor_coverage_v1": {
            "match": _signature_default(
                select_structural_neighbors, "evidence_match_config_path"
            ),
            "card": _signature_default(
                select_structural_neighbors, "evidence_card_config_path"
            ),
        },
        # cascada: call site explícito en post_rerank_coverage.py.
        "cascaded_structural_neighbor_coverage_v1": {
            "match": cascade["evidence_match_config_path"],
            "card": cascade["evidence_card_config_path"],
        },
        # pool: mismo fichero en las dos mitades, por construcción del módulo.
        "rerank_pool_coverage_v1": {
            "match": POOL_COMPLEMENT_CONFIG,
            "card": POOL_COMPLEMENT_CONFIG,
        },
        # hyq (s288b): el par es un RETRIEVAL-config (match) + un evidence-config
        # (card), y AMBOS son defaults de la firma del colector — se leen por
        # introspección para que re-apuntar cualquiera de los dos rompa aquí.
        HYQ_LANE: {
            "match": _signature_default(
                collect_document_scoped_hyq, "query_facets_path"
            ),
            "card": _signature_default(
                collect_document_scoped_hyq, "evidence_config_path"
            ),
        },
    }


LANE_PAIRS = _served_lane_pairs()


def _archetypes(path: Path) -> dict[str, Any]:
    """EXTRACTOR: normaliza las dos formas de declarar ``archetypes`` a un mapping.

    Los card-configs (``evidence_coverage_facets_*``) los declaran como MAPPING
    ``id -> [facetas]``; los match-configs de retrieval (``retrieval_facets_*``)
    como LISTA de objetos con ``id``.  Mientras cada lane emparejó dos configs de
    evidencia el test no vio nunca la segunda forma; el par de la lane hyq
    (retrieval_facets_v4 -> evidence_coverage_facets_v5) SÍ la trae, y sin este
    extractor ``set(...)`` sobre la lista revienta con TypeError (dict no
    hashable) en vez de comparar arquetipos.
    """
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))["archetypes"]
    if isinstance(payload, dict):
        return payload
    assert isinstance(payload, list) and payload, (
        f"{path.name}: ``archetypes`` debe ser un mapping o una lista no vacía"
    )
    extracted: dict[str, Any] = {}
    for entry in payload:
        archetype_id = entry["id"]
        assert archetype_id not in extracted, (
            f"{path.name}: arquetipo duplicado {archetype_id}"
        )
        # El valor solo se usa para la prueba de "starvation" del lado CARD; se
        # conserva el contenido declarado (needs) para que un arquetipo vacío
        # siguiera siendo falsy si algún día una lista se usara como card-config.
        extracted[archetype_id] = entry.get("needs") or []
    return extracted


def test_the_served_pairs_are_the_ones_this_contract_believes():
    """Ancla explícita: si una lane re-apunta su config, el test lo dice por
    nombre en vez de seguir pasando contra un par distinto del revisado."""
    assert LANE_PAIRS["same_blob_structural_neighbor_coverage_v1"] == {
        "match": STRICT_ALIGNED_CONFIG,
        "card": MULTIFACET_CONFIG,
    }
    assert LANE_PAIRS["cascaded_structural_neighbor_coverage_v1"] == {
        "match": CASCADED_EVIDENCE_CONFIG,
        "card": CASCADED_EVIDENCE_CONFIG,
    }
    assert LANE_PAIRS["rerank_pool_coverage_v1"] == {
        "match": POOL_COMPLEMENT_CONFIG,
        "card": POOL_COMPLEMENT_CONFIG,
    }
    # s288b: el par de la lane hyq se ancla POR NOMBRE de fichero en el lado del
    # match (la constante vive en el propio módulo de la lane: compararla consigo
    # misma no probaría nada) y por CONSTANTE COMPARTIDA en el lado de la card.
    assert LANE_PAIRS[HYQ_LANE]["match"] == ROOT / "config/retrieval_facets_v4.yaml"
    assert LANE_PAIRS[HYQ_LANE]["card"] == POOL_COMPLEMENT_CONFIG


@pytest.mark.parametrize("lane", sorted(LANE_PAIRS))
def test_every_match_archetype_has_cards_in_the_same_lane(lane):
    """EL matador de la clase: un arquetipo que puntúa DEBE poder producir card.

    Dirección deliberadamente asimétrica (match ⊆ card): un card-config con
    arquetipos de más es inerte (nadie los puntúa en esa lane), mientras que un
    match-config con arquetipos de más es el fallo silencioso.
    """
    pair = LANE_PAIRS[lane]
    match_archetypes = _archetypes(pair["match"])
    card_archetypes = _archetypes(pair["card"])
    missing = sorted(set(match_archetypes) - set(card_archetypes))
    assert not missing, (
        f"lane {lane}: arquetipos que puntúan en "
        f"{pair['match'].relative_to(ROOT).as_posix()} pero NO fabrican card en "
        f"{pair['card'].relative_to(ROOT).as_posix()} => la lane seleccionaría y "
        f"_attest rechazaría por coverage_cards vacías: {missing}"
    )


@pytest.mark.parametrize("lane", sorted(LANE_PAIRS))
def test_no_match_archetype_is_card_starved(lane):
    """Paridad de CLAVE no basta: un arquetipo presente pero con lista de
    facetas vacía tendría exactamente el mismo síntoma."""
    pair = LANE_PAIRS[lane]
    card_archetypes = _archetypes(pair["card"])
    starved = sorted(
        archetype
        for archetype in _archetypes(pair["match"])
        if not card_archetypes.get(archetype)
    )
    assert not starved, f"lane {lane}: arquetipos sin facetas de card: {starved}"


def test_cross_lane_parity_is_deliberately_not_required():
    """Guardarraíl del alcance: este contrato NO es «una sola config global».

    Si alguien lo endurece a paridad entre lanes, esta aserción falla y obliga a
    releer el motivo — v5/cascade sirven un vocabulario distinto (intrinsic_safety,
    loop_eol_topology, compatibility, battery_sizing) que v2/v4 no tienen, y v4
    lleva ``query_alignment_min_terms`` que el selector de cards no puede honrar
    (no recibe la query en la lane structural).
    """
    structural = LANE_PAIRS["same_blob_structural_neighbor_coverage_v1"]
    pool = LANE_PAIRS["rerank_pool_coverage_v1"]
    assert set(_archetypes(pool["match"])) != set(_archetypes(structural["match"]))
    assert "query_alignment_min_terms" in yaml.safe_load(
        structural["match"].read_text(encoding="utf-8")
    )
    assert "query_alignment_min_terms" not in yaml.safe_load(
        structural["card"].read_text(encoding="utf-8")
    )


def test_pool_lane_reads_the_same_config_on_both_halves():
    """El par del pool se afirma por constante; esto lo ancla al código real."""
    source = Path(
        inspect.getsourcefile(rerank_pool_coverage)
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    used = {
        keyword.value.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"match_evidence_facets", "select_evidence_coverage_cards"}
        for keyword in node.keywords
        if keyword.arg == "config_path" and isinstance(keyword.value, ast.Name)
    }
    assert used == {"POOL_COMPLEMENT_CONFIG"}
