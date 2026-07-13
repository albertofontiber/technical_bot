from copy import deepcopy

from src.rag.structural_neighbor_coverage import (
    LANE,
    select_structural_neighbors,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def _row(row_id, index, content, *, document="doc-a", sha=HASH_A, language="es"):
    return {
        "id": row_id,
        "document_id": document,
        "extraction_sha256": sha,
        "chunk_index": index,
        "content": content,
        "section_title": "",
        "product_model": "ID2000",
        "language": language,
    }


def test_selects_query_aligned_same_blob_structured_limit_without_runtime_attestation():
    query = "¿Cómo se conecta un módulo aislador en el lazo ID2000?"
    seeds = [_row("seed", 20, "Conexión del módulo aislador al lazo.")]
    candidates = [
        _row(
            "target",
            26,
            "La pantalla debe mantener continuidad. La resistencia máxima del "
            "lazo no debe superar los 35 ohmios. Compruebe la instalación.",
        ),
        _row("noise", 22, "Programación de fecha y hora."),
    ]

    selected, trace = select_structural_neighbors(query, seeds, candidates)

    assert [row["id"] for row in selected] == ["target"]
    assert selected[0]["retrieval_lane"] == LANE
    assert selected[0]["structured_priority_claims"][0]["value"] == "35"
    assert selected[0]["coverage_cards"][0]["quote"].endswith("35 ohmios")
    assert selected[0]["coverage_cards"][0]["facet"] == (
        "structured_numeric:loop_resistance"
    )
    assert selected[0]["coverage_cards"][0]["exact_source_span_validated"] is True
    assert selected[0]["local_semantic_validated"] is True
    assert "coverage_validated" not in selected[0]
    assert trace["reason"] == "selected"


def test_rejects_cross_document_cross_blob_far_and_seed_rows():
    query = "¿Cómo conectar el cableado y comprobar la resistencia del lazo?"
    seed = _row("seed", 10, "Cableado del lazo")
    candidates = [
        deepcopy(seed),
        _row("cross-doc", 11, "Conexión y resistencia del lazo", document="doc-b"),
        _row("cross-blob", 11, "Conexión y resistencia del lazo", sha=HASH_B),
        _row("far", 19, "Conexión y resistencia del lazo"),
    ]

    selected, trace = select_structural_neighbors(query, [seed], candidates)

    assert selected == []
    assert trace["same_blob_candidates"] == 0


def test_rejects_invalid_hash_index_language_and_missing_identity():
    query = "¿Cómo conectar el cableado y comprobar la resistencia del lazo?"
    seed = _row("seed", 10, "Cableado del lazo")
    candidates = [
        _row("bad-hash", 11, "Conexión resistencia lazo", sha="legacy"),
        _row("bad-index", True, "Conexión resistencia lazo"),
        _row("bad-language", 11, "Connexion resistance boucle", language="fr"),
        {"id": "missing", "chunk_index": 11, "content": "Conexión resistencia lazo"},
    ]

    selected, trace = select_structural_neighbors(query, [seed], candidates)

    assert selected == []
    assert trace["same_blob_candidates"] == 0


def test_requires_positive_query_score_and_source_facet():
    seed = _row("seed", 10, "Manual técnico")
    no_query_overlap = _row(
        "no-query", 11, "Pantalla tierra continuidad resistencia del lazo"
    )
    no_facet = _row("no-facet", 12, "Conectar el aislador ahora")

    selected, trace = select_structural_neighbors(
        "¿Cómo programar la fecha del panel?", seed and [seed], [no_query_overlap, no_facet]
    )

    assert selected == []
    assert trace["reason"] == "no_query_aligned_facet_candidate"


def test_programming_route_does_not_prioritize_unrelated_numeric_claim():
    query = "¿Cómo se programa el retardo de salida de alarma?"
    seeds = [_row("seed", 50, "Retardo de salida", document="doc-p")]
    procedural = _row(
        "procedure",
        51,
        "La programación causa-efecto usa reglas con instrucciones de entrada "
        "y salida y una acción de retardo.",
        document="doc-p",
    )
    numeric = _row(
        "numeric",
        52,
        "Una condición de entrada crea una regla de salida con retardo máximo "
        "de 30 minutos.",
        document="doc-p",
    )

    selected, _ = select_structural_neighbors(query, seeds, [numeric, procedural])

    assert selected[0]["id"] == "procedure"
    assert selected[0]["structured_priority_claims"] == []
    assert selected[0]["coverage_cards"]
    assert all(
        card["exact_source_span_validated"] is True
        for card in selected[0]["coverage_cards"]
    )


def test_fault_recovery_can_prioritize_bound_duration_without_injected_value():
    query = "Tras la extinción no vuelve a normal después de rearmar, ¿qué comprobar?"
    seeds = [_row("seed", 70, "Fin de activación de la extinción", document="doc-r")]
    duration = _row(
        "duration",
        77,
        "Tiempo de activación de la extinción variable de 05 a 295 segundos; "
        "después del periodo se permite el rearme.",
        document="doc-r",
    )
    blocker = _row(
        "blocker",
        71,
        "Compruebe la condición activa y el bloqueo antes del rearme.",
        document="doc-r",
    )

    selected, _ = select_structural_neighbors(query, seeds, [blocker, duration])

    assert selected[0]["id"] == "duration"
    claim = selected[0]["structured_priority_claims"][0]
    assert (claim["lower_value"], claim["upper_value"], claim["unit"]) == (
        "5",
        "295",
        "second",
    )


def test_rejects_table_of_contents_even_when_it_contains_all_facet_terms():
    query = "¿Cómo se programa una regla de causa efecto con entrada y salida?"
    seeds = [_row("seed", 10, "Programación causa efecto", document="doc-t")]
    toc = _row(
        "toc",
        11,
        "# Índice\n"
        "1 Programación 5\n2 Regla causa efecto 10\n3 Condición entrada 15\n"
        "4 Acción salida 20\n5 Retardo salida 25\n6 Edición regla 30\n"
        "7 Matriz 35\n8 Menú 40\n",
        document="doc-t",
    )

    selected, trace = select_structural_neighbors(query, seeds, [toc])

    assert selected == []
    assert trace["toc_rejected_ids"] == ["toc"]
