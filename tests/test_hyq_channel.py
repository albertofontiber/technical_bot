"""Tests del canal question-side hyq (s102 ship, D2/DEC-095) — mecánica v2 gateada.

Cubre los mecanismos nuevos post-gate (fix X5 cross-model r2 + fixes #1/#2 sub-agente r2):
`_hyq_family_rows` (family-parity a NIVEL FILA, antes del colapso keep-max) y el carve-out
del diversify por-fichero en retrieve_chunks (la cuota hyq no se re-litiga aguas abajo,
sin ventana de id duplicado).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

from src.rag import retriever as rt  # noqa: E402


# ---------------------------------------------------------------------------
# _hyq_family_rows — matcher de familia sobre el TEXTO de cada pregunta (nivel FILA)
# ---------------------------------------------------------------------------
def _row(pid, sim, q):
    return {"chunk_id": pid, "similarity": sim, "question": q}


def test_family_rows_cad150_matches_variant_not_cad250():
    """CAD-150 debe capturar la variante CAD-150-8 (sufijo no-dígito tras separador) y
    NO a la CAD-250 (producto distinto). El caso medido del gate: la pregunta ganadora
    de cat016 menciona 'CAD-150-8'."""
    rows = [
        _row("win", 0.47, "¿Cómo hago la autobúsqueda del lazo en la CAD-150-8?"),
        _row("c250", 0.51, "¿Cómo compruebo el cableado del lazo de la Detnov CAD-250?"),
        _row("zx", 0.53, "¿Cómo hago para que el panel ZX2e/ZX5e reconozca los detectores?"),
    ]
    out = rt._hyq_family_rows(rows, ["CAD-150"])
    assert [r["chunk_id"] for r in out] == ["win"]


def test_family_rows_zx2e_matches_slash_family_not_zxce():
    """ZX2e (post-resolver) captura 'ZX2e/ZX5e' y NO 'ZXCE' (central distinta)."""
    rows = [
        _row("win", 0.46, "¿Qué resistencia de final de línea hay en las sirenas de la ZX2e/ZX5e?"),
        _row("zxce", 0.52, "¿En qué terminales se conectan las sirenas en la central ZXCE?"),
    ]
    out = rt._hyq_family_rows(rows, ["ZX2e"])
    assert [r["chunk_id"] for r in out] == ["win"]


def test_family_rows_no_digit_extension():
    """El (?!\\d) evita que ID-200 capture ID2000 (mismo contrato que model_to_imatch_pattern)."""
    rows = [
        _row("id2000", 0.5, "¿Cómo se programa la Notifier ID2000 en modo día?"),
        _row("id200", 0.48, "¿Cómo se programa la ID-200 en modo noche?"),
    ]
    out = rt._hyq_family_rows(rows, ["ID-200"])
    assert [r["chunk_id"] for r in out] == ["id200"]


def test_family_rows_fallback_zero_matches_returns_global():
    """Sin filas de familia → filas globales SIN cambios (fallback declarado no-peor)."""
    rows = [_row("a", 0.5, "¿Cómo se cambia la batería del panel X99?"),
            _row("b", 0.49, "¿Qué fusible lleva la fuente FA-200?")]
    assert rt._hyq_family_rows(rows, ["CAD-150"]) == rows


def test_family_rows_no_models_noop():
    """Queries sin modelo → passthrough exacto (la mecánica medida en piloto/neg-control)."""
    rows = [_row("a", 0.5, "pregunta cualquiera")]
    assert rt._hyq_family_rows(rows, None) == rows
    assert rt._hyq_family_rows(rows, []) == rows


def test_family_rows_single_casual_match_narrows_declared():
    """(X3 cross-model r2, DECLARADO) ≥1 match estrecha la cuota a la familia: con modelos
    detectados los padres globales mueren downstream igual (_filter_to_query_models drop-duro)
    — el estrechamiento no es peor, salvo la ventana series/shared-docs (TECH_DEBT #45)."""
    rows = [
        _row("fam", 0.46, "¿Cómo se resetea la CAD-150 tras una alarma?"),
        _row("glob", 0.60, "¿Cómo se resetea un panel genérico tras alarma?"),
    ]
    out = rt._hyq_family_rows(rows, ["CAD-150"])
    assert [r["chunk_id"] for r in out] == ["fam"]


def test_family_rows_before_collapse_rescues_parent_with_unanchored_winner():
    """(fix #2 dúo r2) El anclaje a producto de las hyq es CONDICIONAL: si el padre tiene
    como pregunta GANADORA (mejor cos) una sin modelo y otra fila anclada de familia, el
    filtro nivel-FILA conserva la anclada — colapsar primero habría excluido al padre
    entero. Simula el colapso keep-max de _hyq_table_hits sobre las filas filtradas."""
    rows = [
        _row("p1", 0.55, "¿Cómo se rearma el panel tras una alarma de zona?"),      # ganadora SIN ancla
        _row("p1", 0.47, "¿Cómo se rearma la CAD-150 tras una alarma de zona?"),    # anclada, cos menor
        _row("p2", 0.52, "¿Cómo se rearma un equipo convencional cualquiera?"),
    ]
    fam = rt._hyq_family_rows(rows, ["CAD-150"])
    assert [r["chunk_id"] for r in fam] == ["p1"]
    # colapso keep-max post-filtro: p1 sobrevive con su pregunta ANCLADA
    by_parent = {}
    for r in fam:
        if r["chunk_id"] not in by_parent or r["similarity"] > by_parent[r["chunk_id"]][0]:
            by_parent[r["chunk_id"]] = (r["similarity"], r["question"])
    assert "p1" in by_parent and "CAD-150" in by_parent["p1"][1]


# ---------------------------------------------------------------------------
# Carve-out del diversify — la cuota hyq no se re-litiga por el interleave
# ---------------------------------------------------------------------------
def _chunk(cid, src, sim, hyq=False, boosted=False):
    c = {"id": cid, "source_file": src, "similarity": sim, "content": f"c-{cid}",
         "product_model": "CAD-150"}
    if hyq:
        c["_hyq_surrogate"] = True
        c["_hyq_question"] = "q"
    if boosted:
        c["_hyq_boosted"] = True
    return c


def _patch_pipeline(monkeypatch, vector_rows, diversify=None):
    monkeypatch.setattr(rt, "HYDE_ENABLED", False)
    monkeypatch.setattr(rt, "extract_product_models", lambda q: ["CAD-150"])
    monkeypatch.setattr(rt, "vector_search", lambda *a, **k: list(vector_rows))
    monkeypatch.setattr(rt, "keyword_search", lambda *a, **k: [])
    monkeypatch.setattr(rt, "content_search", lambda *a, **k: [])
    monkeypatch.setattr(rt, "typed_search", lambda *a, **k: [])
    monkeypatch.setattr(rt, "diagram_search", lambda *a, **k: [])
    monkeypatch.setattr(rt, "embed_query", lambda q: [0.0] * 4)
    monkeypatch.setattr(rt, "_diversify_by_source_file",
                        diversify or (lambda chunks, k, *a, **kw: chunks))
    monkeypatch.setattr(rt, "_filter_to_query_models", lambda chunks, models, **kw: chunks)
    monkeypatch.setattr(rt, "_filter_by_document_status", lambda chunks: chunks)
    monkeypatch.setattr(rt, "_filter_by_language", lambda chunks: chunks)
    monkeypatch.setattr(rt, "_expand_neighbors", lambda chunks, w, models=None: chunks)


def test_carveout_surrogate_survives_diversify_and_final_cap(monkeypatch):
    """(s103b v3.1) El surrogate sobrevive al diversify y al corte [:top_k] final — ahora como
    EXTENSIÓN ACOTADA post-corte (sin reserva de slots). Contrato de tamaño COMPUESTO:
    pool ≤ top_k + n_aside; los chunks reales del top_k NO pierden slots por el aside."""
    top_k = 5
    real = [_chunk(f"r{i}", "DOC-A", 0.9 - i * 0.01) for i in range(10)]
    surrogate = _chunk("hyq1", "DOC-A", 0.46, hyq=True)
    _patch_pipeline(monkeypatch, real + [surrogate])

    out = rt.retrieve_chunks("¿Cómo se resetea la CAD-150?", top_k=top_k)
    ids = [c["id"] for c in out]
    assert "hyq1" in ids, "el surrogate debe sobrevivir end-to-end (presupuesto del canal)"
    assert len(out) <= top_k + 1, "extensión acotada: pool ≤ top_k + n_aside"
    assert [i for i in ids if i != "hyq1"] == [f"r{i}" for i in range(top_k)], \
        "los top_k reales quedan INTACTOS (la extensión no desplaza a nadie)"
    assert ids[-1] == "hyq1", "el aside viaja al final (el reranker decide)"


def test_extension_aside_language_strict(monkeypatch):
    """(s103b v3.1, F5 dúo) El aside post-corte esquiva el Step 5c → cinturón de idioma
    ESTRICTO inline: un surrogate FR se cae; ES/EN/sin-language pasan (mismo cinturón que
    el identity-fetch — el fail-open de _filter_by_language sobre lista corta se invertiría)."""
    top_k = 4
    real = [_chunk(f"r{i}", "DOC-A", 0.9 - i * 0.01) for i in range(2)]
    s_fr = _chunk("hyqFR", "DOC-B", 0.50, hyq=True)
    s_fr["language"] = "fr"
    s_es = _chunk("hyqES", "DOC-B", 0.48, hyq=True)
    s_es["language"] = "es"
    s_nil = _chunk("hyqNIL", "DOC-C", 0.46, hyq=True)
    _patch_pipeline(monkeypatch, real + [s_fr, s_es, s_nil])

    out = rt.retrieve_chunks("¿Cómo se resetea la CAD-150?", top_k=top_k)
    ids = [c["id"] for c in out]
    assert "hyqES" in ids and "hyqNIL" in ids, "ES y sin-language pasan el cinturón"
    assert "hyqFR" not in ids, "idioma fuera de servicio NO entra vía extensión"
    assert len(out) <= top_k + 3


def test_carveout_no_duplicate_when_supplement_refetches_parent(monkeypatch):
    """(fix #1 dúo r2) Si el diversify (fetch suplementario) re-trae EL MISMO chunk-padre
    que estaba apartado como surrogate, el re-adjunte NO puede duplicar el id en el pool
    — el aside gana (conserva los stamps)."""
    top_k = 5
    real = [_chunk(f"r{i}", "DOC-A", 0.9 - i * 0.01) for i in range(3)]
    surrogate = _chunk("hyq1", "DOC-B", 0.46, hyq=True)

    def diversify_refetches_parent(chunks, k, *a, **kw):
        # simula _fetch_top_chunks_by_source_file trayendo el MISMO chunk sin stamps
        return chunks[:k] + [_chunk("hyq1", "DOC-B", 0.72)]

    _patch_pipeline(monkeypatch, real + [surrogate], diversify=diversify_refetches_parent)

    out = rt.retrieve_chunks("¿Cómo se resetea la CAD-150?", top_k=top_k)
    ids = [c["id"] for c in out]
    assert ids.count("hyq1") == 1, "id duplicado en el pool (ventana fix #1)"
    kept = next(c for c in out if c["id"] == "hyq1")
    assert kept.get("_hyq_surrogate"), "debe sobrevivir la copia CON stamps (traceability)"
    assert len(out) <= top_k + 1   # (s103b F7) bound compuesto: top_k + n_aside


def test_extension_no_model_query_no_aside(monkeypatch):
    """(s103b F8a) Rama SIN modelo: no hay carve-out ni extensión — los surrogates compiten
    en el flujo normal (mecánica medida en piloto+negcontrol) y el pool respeta top_k."""
    top_k = 4
    real = [_chunk(f"r{i}", "DOC-A", 0.9 - i * 0.01) for i in range(6)]
    surrogate = _chunk("hyq1", "DOC-B", 0.95, hyq=True)   # sim alta: sobrevive por ranking
    _patch_pipeline(monkeypatch, real + [surrogate])
    monkeypatch.setattr(rt, "extract_product_models", lambda q: [])
    monkeypatch.setattr(rt, "_diversify_by_manufacturer",
                        lambda chunks, k, *a, **kw: chunks[:k])

    out = rt.retrieve_chunks("¿Cómo se resetea un panel tras alarma?", top_k=top_k)
    assert len(out) <= top_k, "sin modelo NO hay extensión: el pool respeta top_k"
    assert "hyq1" in [c["id"] for c in out], "el surrogate compite por ranking normal"


def test_extension_identity_fetch_sees_aside_ids(monkeypatch):
    """(s103b F8b) El aside se adjunta ANTES del bloque identity-fetch → su `have` ve los
    ids del aside y un fetch que re-trae el MISMO chunk no lo duplica."""
    top_k = 4
    real = [_chunk(f"r{i}", "DOC-A", 0.9 - i * 0.01) for i in range(2)]
    surrogate = _chunk("hyq1", "DOC-B", 0.46, hyq=True)
    _patch_pipeline(monkeypatch, real + [surrogate])
    from src.rag import catalog_resolver as _cr   # import local en retrieve_chunks
    monkeypatch.setattr(_cr, "fetch_enabled", lambda: True)
    monkeypatch.setattr(_cr, "fetch_missing_doc_chunks",
                        lambda q, res, base: [_chunk("hyq1", "DOC-B", 0.72)])

    out = rt.retrieve_chunks("¿Cómo se resetea la CAD-150?", top_k=top_k)
    ids = [c["id"] for c in out]
    if "hyq1" in ids:   # el fetch requiere _identity_res truthy; si no corre, el aside manda
        assert ids.count("hyq1") == 1, "el have del fetch debe ver los ids del aside"


def test_carveout_full_budget_extension_not_boosted(monkeypatch):
    """(s103b v3.1) El diversify recibe top_k COMPLETO (la reserva era el doble descuento
    medido en DEC-100); el aside sigue FUERA del interleave (consenso s59) y los _hyq_boosted
    (hits reales) dentro, compitiendo como siempre."""
    seen = {}

    def spy_diversify(chunks, k, *a, **kw):
        seen["k"] = k
        seen["ids"] = {c["id"] for c in chunks}
        return chunks[:k]

    real = [_chunk(f"r{i}", "DOC-A", 0.9 - i * 0.01) for i in range(6)]
    surrogate = _chunk("hyq1", "DOC-B", 0.46, hyq=True)
    boosted = _chunk("boost1", "DOC-A", 0.88, boosted=True)
    _patch_pipeline(monkeypatch, real + [surrogate, boosted], diversify=spy_diversify)

    top_k = 5
    out = rt.retrieve_chunks("¿Cómo se resetea la CAD-150?", top_k=top_k)
    ids = [c["id"] for c in out]
    assert seen["k"] == top_k, "el diversify corre a top_k COMPLETO (sin doble descuento)"
    assert "hyq1" not in seen["ids"], "el surrogate NO entra al interleave"
    assert "boost1" in seen["ids"], "el boosted (hit real) SÍ compite en el diversify"
    assert "hyq1" in ids and len(out) <= top_k + 1
