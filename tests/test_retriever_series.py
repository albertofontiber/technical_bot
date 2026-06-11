"""Tests de integración filtro+diversify con el registry de series (ciclo A s63).

Cubren los puntos del FINAL que el dúo r1/r2 marcó como obligatorios:
- d1: la query del base ya no arrastra hermanos (cat012) — filtro Y diversify
  (F1 r1: diversify re-introducía post-filtro).
- d2: el doc de serie entra por fetch dirigido (r2 R5/Z2).
- Comparativas multi-modelo intactas (r2 R4/Z1).
- Fail-open escalonado (F8/X1).
- Pre-filtro de missing_sources (r2 R6/Z3: hermanos no queman slots).
- Sin series activas → byte-a-byte el comportamiento histórico (G4).

Mismo estilo que test_retriever_diversification.py: chunks in-memory + helpers
DB parcheados.
"""
import pytest

from src.rag import retriever
from src.rag import series_registry as sr
from src.rag.retriever import _filter_to_query_models, _diversify_by_source_file


NOTIFIER_YAML = """\
manufacturer: Notifier
series:
  - name: AM-8200
    members: [AM-8200, AM-8200G, AM-8200N]
    evidence: "fixture (audit s62)"
"""

DETNOV_YAML = """\
manufacturer: Detnov
series:
  - name: Vesta
    members: [CAD-171, CAD-201, CAD-250]
    evidence: "fixture (DEC-032)"
    shared_docs:
      - source_file: "CAD-250-MC-380-es"
        evidence: "manual de configuración de la serie (fixture)"
"""


@pytest.fixture
def series_registry(tmp_path, monkeypatch):
    """Registry poblado con las dos series del ciclo (fixture, no producción)."""
    (tmp_path / "notifier.yaml").write_text(NOTIFIER_YAML, encoding="utf-8")
    (tmp_path / "detnov.yaml").write_text(DETNOV_YAML, encoding="utf-8")
    monkeypatch.setattr(sr, "_CONFIG_DIR", tmp_path)
    monkeypatch.delenv("SERIES_REGISTRY_ENABLED", raising=False)
    sr.reset_registry_cache()
    yield
    sr.reset_registry_cache()


@pytest.fixture
def empty_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "_CONFIG_DIR", tmp_path)
    monkeypatch.delenv("SERIES_REGISTRY_ENABLED", raising=False)
    sr.reset_registry_cache()
    yield
    sr.reset_registry_cache()


def _c(cid, pm, sf="doc", sim=0.8):
    return {"id": cid, "product_model": pm, "source_file": sf, "similarity": sim}


# ===========================================================================
# _filter_to_query_models — nivel 2
# ===========================================================================

def test_filtro_d1_veta_hermanos(series_registry):
    """cat012: query AM-8200 → chunks de 8200G/N (que pasan substring) fuera."""
    chunks = [
        _c("1", "AM-8200", "AM-8200 Manual Instalacion"),
        _c("2", "AM-8200G", "AM 8200G manual instalacion Rv 3"),
        _c("3", "AM-8200N", "AM 8200N-manual instalacion RV 4"),
        _c("4", "AM-8200", "AM-8200-manu-prog-spa"),
        _c("5", "AM-8200", "UCIP MODBUS AM8200 V5.1"),
    ]
    result = _filter_to_query_models(chunks, ["AM-8200"])
    assert [c["id"] for c in result] == ["1", "4", "5"]


def test_filtro_comparativa_multi_modelo(series_registry):
    """r2 R4/Z1: 'AM-8200 vs AM-8200G' — cada chunk pasa por SU modelo."""
    chunks = [
        _c("1", "AM-8200"),
        _c("2", "AM-8200G"),
        _c("3", "AM-8200N"),   # no pedido → fuera
        _c("4", "AM-8200"),
    ]
    result = _filter_to_query_models(chunks, ["AM-8200", "AM-8200G"])
    assert [c["id"] for c in result] == ["1", "2", "4"]


def test_filtro_d2_shared_abre(series_registry):
    """DEC-032: query CAD-201 ve el MC-380 (pm=CAD-250, shared declarado) pero
    NO el resto de docs del 250."""
    chunks = [
        _c("1", "CAD-201", "Manual_CAD-201-MI-715-es"),
        _c("2", "CAD-250", "CAD-250-MC-380-es"),
        _c("3", "CAD-250", "Manual instalacion CAD-250 (MI_372_es_2024 e)"),
        _c("4", "CAD-201", "Manual_CAD-201-MI-715-es"),
        _c("5", "CAD-201", "Manual_CAD-201-MI-715-es"),
    ]
    result = _filter_to_query_models(chunks, ["CAD-201"])
    assert [c["id"] for c in result] == ["1", "2", "4", "5"]


def test_filtro_fail_open_escalonado(series_registry):
    """Nivel 2 deja <3 → escalón a nivel 1 (substring, hermanos incluidos) —
    nunca peor que el comportamiento histórico."""
    chunks = [
        _c("1", "AM-8200"),
        _c("2", "AM-8200G"),
        _c("3", "AM-8200G"),
        _c("4", "AM-8200N"),
        _c("5", "NFS-320"),    # ni substring
    ]
    # Nivel 2 dejaría solo ["1"] (<3) → nivel 1: substring deja 1-4; NFS fuera.
    result = _filter_to_query_models(chunks, ["AM-8200"])
    assert [c["id"] for c in result] == ["1", "2", "3", "4"]


def test_filtro_fail_open_final_originals(series_registry):
    """Nivel 2 <3 Y nivel 1 <3 → originals completos (comportamiento histórico)."""
    chunks = [
        _c("1", "AM-8200"),
        _c("2", "NFS-320"),
        _c("3", "ID3000"),
    ]
    result = _filter_to_query_models(chunks, ["AM-8200"])
    assert [c["id"] for c in result] == ["1", "2", "3"]


def test_filtro_nivel1_intacto_para_modelos_sin_serie(series_registry):
    """hp003/#11e (G4): CAD-150 no tiene serie → comportamiento histórico
    EXACTO aunque el registry esté cargado (espejo del test canónico)."""
    chunks = [
        _c("1", "CAD-150-8"),
        _c("2", "CAD-250"),
        _c("3", "CAD-150-8"),
        _c("4", "CAD-150-8"),
    ]
    result = _filter_to_query_models(chunks, ["CAD-150"])
    assert [c["id"] for c in result] == ["1", "3", "4"]


def test_filtro_flag_off_byte_a_byte(series_registry, monkeypatch):
    """Kill-switch: con SERIES_REGISTRY_ENABLED=false los hermanos vuelven a
    pasar (= bot actual). Es el brazo control del A/B."""
    monkeypatch.setenv("SERIES_REGISTRY_ENABLED", "false")
    sr.reset_registry_cache()
    chunks = [
        _c("1", "AM-8200"),
        _c("2", "AM-8200G"),
        _c("3", "AM-8200N"),
        _c("4", "AM-8200"),
    ]
    result = _filter_to_query_models(chunks, ["AM-8200"])
    assert [c["id"] for c in result] == ["1", "2", "3", "4"]


# ===========================================================================
# _diversify_by_source_file — discovery + pre-filtro + cinturón
# ===========================================================================

@pytest.fixture
def diversify_mocks(monkeypatch):
    """Helpers DB parcheados con un mini-corpus AM-8200 + Vesta."""
    sources_by_model = {
        "AM-8200": [
            "AM-8200N manual de usuario y programacion rev 3 30-10-2024",  # hermano (120ch)
            "AM-8200-manu-prog-spa",                                        # base
            "AM-8200 Manual Instalacion",                                   # base
            "UCIP MODBUS AM8200 V5.1",                                      # base
            "AM 8200G manual instalacion Rv 3",                             # hermano
            "AM 8200N-manual instalacion RV 4 30-01-2025",                  # hermano
            "AM-LCD manual de instalacion y usuario RV 0",                  # pm=AM-8200N
            "HONEYWELL-H-GTW-ESP-2.26 Integracion",                         # base
        ],
        "CAD-201": ["Manual_CAD-201-MI-715-es"],
    }
    pm_by_source = {
        "AM-8200N manual de usuario y programacion rev 3 30-10-2024": "AM-8200N",
        "AM-8200-manu-prog-spa": "AM-8200",
        "AM-8200 Manual Instalacion": "AM-8200",
        "UCIP MODBUS AM8200 V5.1": "AM-8200",
        "AM 8200G manual instalacion Rv 3": "AM-8200G",
        "AM 8200N-manual instalacion RV 4 30-01-2025": "AM-8200N",
        "AM-LCD manual de instalacion y usuario RV 0": "AM-8200N",
        "HONEYWELL-H-GTW-ESP-2.26 Integracion": "AM-8200",
        "Manual_CAD-201-MI-715-es": "CAD-201",
        "CAD-250-MC-380-es": "CAD-250",
    }
    fetched: list[str] = []

    def fake_sources(model):
        return list(sources_by_model.get(model, []))

    def fake_pm_for_sources(sfs):
        return {sf: pm_by_source[sf] for sf in sfs if sf in pm_by_source}

    def fake_fetch(source_file, query, limit=2):
        fetched.append(source_file)
        pm = pm_by_source.get(source_file, "X")
        return [{"id": f"extra-{source_file[:18]}-{i}", "product_model": pm,
                 "source_file": source_file, "content": "x"} for i in range(limit)]

    monkeypatch.setattr(retriever, "_get_source_files_for_model", fake_sources)
    monkeypatch.setattr(retriever, "_get_pm_for_sources", fake_pm_for_sources)
    monkeypatch.setattr(retriever, "_fetch_top_chunks_by_source_file", fake_fetch)
    return fetched


def test_diversify_no_reintroduce_hermanos(series_registry, diversify_mocks):
    """F1 r1 (crítico): tras el veto del filtro, diversify NO re-fetchea los
    docs de los hermanos — y los slots liberados van a docs legítimos del base
    (r2 R6/Z3: HONEYWELL ya no se queda fuera)."""
    pool = [
        _c("1", "AM-8200", "AM-8200 Manual Instalacion", 0.9),
        _c("2", "AM-8200", "AM-8200 Manual Instalacion", 0.85),
        _c("3", "AM-8200", "AM-8200 Manual Instalacion", 0.8),
    ]
    result = _diversify_by_source_file(pool, top_k=10, models=["AM-8200"],
                                       original_query="consumo baterías AM-8200")
    fetched = diversify_mocks
    assert "AM 8200G manual instalacion Rv 3" not in fetched
    assert "AM-8200N manual de usuario y programacion rev 3 30-10-2024" not in fetched
    # Los 3 docs legítimos ausentes caben en los 4 slots (sin pre-filtro, los
    # hermanos habrían quemado 3 de 4 y HONEYWELL no se intentaba):
    assert "AM-8200-manu-prog-spa" in fetched
    assert "UCIP MODBUS AM8200 V5.1" in fetched
    assert "HONEYWELL-H-GTW-ESP-2.26 Integracion" in fetched
    assert all(c["product_model"] == "AM-8200" for c in result)


def test_diversify_fetch_dirigido_shared_d2(series_registry, diversify_mocks):
    """r2 R5/Z2: el shared MC-380 entra al descubrimiento para CAD-201 y se
    fetchea aunque ningún chunk suyo viniera en el pool."""
    pool = [
        _c("1", "CAD-201", "Manual_CAD-201-MI-715-es", 0.9),
        _c("2", "CAD-201", "Manual_CAD-201-MI-715-es", 0.85),
        _c("3", "CAD-201", "Manual_CAD-201-MI-715-es", 0.8),
    ]
    result = _diversify_by_source_file(pool, top_k=10, models=["CAD-201"],
                                       original_query="CAD-201 candado menú avanzado")
    assert "CAD-250-MC-380-es" in diversify_mocks
    assert any(c["source_file"] == "CAD-250-MC-380-es" for c in result)


def test_diversify_cinturon_post_fetch(series_registry, diversify_mocks, monkeypatch):
    """Aunque un doc hermano llegara al fetch (p.ej. pm desconocido en el
    pre-filtro), el cinturón post-fetch lo deja fuera con el MISMO predicado."""
    # pm desconocido en pre-filtro (fail-open deja pasar el source al fetch)...
    monkeypatch.setattr(retriever, "_get_pm_for_sources", lambda sfs: {})
    pool = [
        _c("1", "AM-8200", "AM-8200 Manual Instalacion", 0.9),
        _c("2", "AM-8200", "AM-8200 Manual Instalacion", 0.85),
        _c("3", "AM-8200", "AM-8200 Manual Instalacion", 0.8),
    ]
    result = _diversify_by_source_file(pool, top_k=10, models=["AM-8200"],
                                       original_query="q")
    # ...pero los chunks que devuelve (pm=AM-8200N/G reales) no entran al pool.
    assert all(c["product_model"] == "AM-8200" for c in result)


def test_diversify_sin_series_comportamiento_historico(empty_registry, diversify_mocks,
                                                       monkeypatch):
    """G4: sin entrada de registry, diversify es EXACTAMENTE el de hoy — los
    hermanos se fetchean (vía imatch) y _get_pm_for_sources ni se llama."""
    called = []
    real = retriever._get_pm_for_sources
    monkeypatch.setattr(retriever, "_get_pm_for_sources",
                        lambda sfs: called.append(1) or real(sfs))
    pool = [
        _c("1", "AM-8200", "AM-8200 Manual Instalacion", 0.9),
        _c("2", "AM-8200", "AM-8200 Manual Instalacion", 0.85),
        _c("3", "AM-8200", "AM-8200 Manual Instalacion", 0.8),
    ]
    result = _diversify_by_source_file(pool, top_k=10, models=["AM-8200"],
                                       original_query="q")
    fetched = diversify_mocks
    assert not called                       # pre-filtro de series NO corre
    # el comportamiento actual: el doc del hermano (más chunks) SÍ se fetchea
    assert "AM-8200N manual de usuario y programacion rev 3 30-10-2024" in fetched
    assert any(c["product_model"] == "AM-8200N" for c in result)


def test_diversify_invariancia_cad250(series_registry, diversify_mocks):
    """G5/cat019: la query CAD-250 (owner = ella misma; shared ya es suyo) no
    pierde nada con el registry activo."""
    sources_cad250 = [
        "CAD-250-MC-380-es", "CAD-250-MS-416-es",
        "Manual instalacion CAD-250 (MI_372_es_2024 e)",
    ]
    import src.rag.retriever as r
    orig = r._get_source_files_for_model

    def with_cad250(model):
        if model == "CAD-250":
            return list(sources_cad250)
        return orig(model)

    # reusar el mock base para el resto
    pool = [
        _c("1", "CAD-250", "CAD-250-MC-380-es", 0.9),
        _c("2", "CAD-250", "CAD-250-MC-380-es", 0.85),
        _c("3", "CAD-250", "CAD-250-MS-416-es", 0.8),
    ]
    import pytest as _pytest  # noqa
    import unittest.mock as um
    with um.patch.object(r, "_get_source_files_for_model", with_cad250):
        result = _diversify_by_source_file(pool, top_k=10, models=["CAD-250"],
                                           original_query="q")
    assert "Manual instalacion CAD-250 (MI_372_es_2024 e)" in diversify_mocks
    assert {c["product_model"] for c in result} == {"CAD-250"}
