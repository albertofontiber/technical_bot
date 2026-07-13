from src.rag.evidence_window import best_evidence_window, build_rerank_preview


def test_navigation_hint_selects_exact_late_source_substring():
    content = (
        "Introduccion sobre instalacion del panel. " * 30
        + "\n\nLa resistencia maxima del lazo no debe superar los 35 ohmios. "
        + "Se mide entre A+ y A-."
    )
    result = best_evidence_window(
        "como conectar el modulo aislador",
        content,
        navigation_hint="La resistencia maxima del lazo es 35 ohmios",
        max_chars=160,
    )

    assert "35 ohmios" in result["text"]
    assert result["text"] in content
    assert len(result["text"]) <= 160
    assert result["start"] > 160


def test_without_hint_query_terms_choose_relevant_paragraph():
    content = "Bateria y alimentacion.\n\nTerminales de conexion del lazo y polaridad."
    result = best_evidence_window("terminales polaridad del lazo", content, max_chars=80)

    assert result["text"] == "Terminales de conexion del lazo y polaridad."
    assert result["used_navigation_hint"] is False


def test_rerank_preview_preserves_head_and_adds_late_source_span():
    content = "cabecera util " * 80 + "\n\nLa resistencia maxima es 35 ohmios."
    result = build_rerank_preview(
        "conexion del lazo",
        content,
        navigation_hint="resistencia maxima 35 ohmios",
        head_chars=120,
        evidence_chars=80,
    )

    assert result["text"].startswith(content[:120])
    assert "35 ohmios" in result["text"]
    assert result["evidence_appended"] is True


def test_rerank_preview_does_not_duplicate_evidence_already_in_head():
    content = "35 ohmios en el lazo.\n\nOtro contenido posterior."
    result = build_rerank_preview(
        "35 ohmios",
        content,
        navigation_hint="35 ohmios",
        head_chars=40,
        evidence_chars=30,
    )

    assert result["evidence_appended"] is False
    assert result["text"] == content[:40]
