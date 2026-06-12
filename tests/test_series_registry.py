"""Tests del registry de series (ciclo A s63 — diseño FINAL post-dúo r1+r2).

Cubren el contrato del FINAL §1b/1d:
- owners() por CONJUNTO con maximal-munch (anidamiento + docs conjuntos, r2 R3)
- passes_nivel2(): unión por modelo (comparativas, r2 R4/Z1), apertura shared (d2),
  veto de hermanos (d1), nivel-1 para modelos sin serie
- loader fail-open: yaml roto, entradas malformadas, colisiones (descartan ambas),
  flag off, fingerprint estable
- VALIDACIÓN DURA de la población real (cuando exista): evidence presente +
  resolución de shared_docs contra el corpus (integración, requiere DB).
"""
import logging
import os

import pytest

from src.rag import series_registry as sr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOTIFIER_YAML = """\
manufacturer: Notifier
series:
  - name: AM-8200
    members: [AM-8200, AM-8200G, AM-8200N]
    evidence: "audit s62: 3 manuales de instalación independientes"
    shared_docs:
      - source_file: "UCIP MODBUS AM8200 V5.1"
        evidence: "protocolo de integración de familia (test fixture)"
"""

DETNOV_YAML = """\
manufacturer: Detnov
series:
  - name: Vesta
    members: [CAD-171, CAD-201, CAD-250]
    evidence: "DEC-032 + inventario s63"
    shared_docs:
      - source_file: "CAD-250-MC-380-es"
        evidence: "manual de configuración de la serie (test fixture)"
"""


@pytest.fixture
def registry_dir(tmp_path, monkeypatch):
    """Apunta el registry a un dir temporal y resetea la cache antes/después."""
    monkeypatch.setattr(sr, "_CONFIG_DIR", tmp_path)
    monkeypatch.delenv("SERIES_REGISTRY_ENABLED", raising=False)
    sr.reset_registry_cache()
    yield tmp_path
    sr.reset_registry_cache()


def _write(registry_dir, name: str, content: str) -> None:
    (registry_dir / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# normalize_model — LA normalización canónica (paridad con el filtro histórico)
# ---------------------------------------------------------------------------

def test_normalize_model_paridad_con_filtro():
    """Idéntica a la histórica de _filter_to_query_models: quita '-'/espacio, lower."""
    assert sr.normalize_model("AM-8200G") == "am8200g"
    assert sr.normalize_model("AM 8200 G") == "am8200g"
    assert sr.normalize_model("AM2020/AFP1010") == "am2020/afp1010"  # '/' se CONSERVA
    assert sr.normalize_model("") == ""
    assert sr.normalize_model(None) == ""


# ---------------------------------------------------------------------------
# owners() — maximal-munch por ocurrencia (r2 R3)
# ---------------------------------------------------------------------------

@pytest.fixture
def am8200(registry_dir):
    _write(registry_dir, "notifier.yaml", NOTIFIER_YAML)
    sr.reset_registry_cache()
    return sr.series_for("AM-8200")


def test_owners_anidamiento(am8200):
    """pm del hermano G pertenece a G, NO al base (el core más largo tapa)."""
    assert am8200.owners("am8200g") == {"am8200g"}
    assert am8200.owners("am8200") == {"am8200"}
    assert am8200.owners("am8200n") == {"am8200n"}


def test_owners_variante_no_declarada_del_hermano(am8200):
    """pm 'AM-8200G-XYZ' (variante de empaque del G no declarada) → owner G:
    vetada para la query del base, correcto."""
    assert am8200.owners("am8200gxyz") == {"am8200g"}


def test_owners_pm_ajeno(am8200):
    """pm de otro producto: la serie no opina (conjunto vacío → sin veto)."""
    assert am8200.owners("nfs320") == set()
    assert am8200.owners("") == set()


def test_owners_doc_conjunto_de_dos_members(registry_dir):
    """pm compuesto con DOS members → owners ambos (r2 R3: el doc conjunto pasa
    para la query de cualquiera de los dos)."""
    _write(registry_dir, "morley.yaml", """\
manufacturer: Morley
series:
  - name: M700K
    members: [M700KAC, M700KACI]
    evidence: "fixture r2 R3"
""")
    sr.reset_registry_cache()
    s = sr.series_for("M700KAC")
    assert s is not None
    # normalize conserva '+': "M700KAC + M700KACI" → "m700kac+m700kaci"
    assert s.owners("m700kac+m700kaci") == {"m700kac", "m700kaci"}


# ---------------------------------------------------------------------------
# passes_nivel2 — el predicado único (filtro Y diversify)
# ---------------------------------------------------------------------------

@pytest.fixture
def full_registry(registry_dir):
    _write(registry_dir, "notifier.yaml", NOTIFIER_YAML)
    _write(registry_dir, "detnov.yaml", DETNOV_YAML)
    sr.reset_registry_cache()
    return registry_dir


def _chunk(pm: str, sf: str = "doc-generico") -> dict:
    return {"product_model": pm, "source_file": sf, "content": "x"}


def test_nivel2_d1_veta_hermanos(full_registry):
    """Query del base: chunks de G/N (que HOY pasan por substring) quedan vetados."""
    assert sr.passes_nivel2(_chunk("AM-8200"), ["AM-8200"]) is True
    assert sr.passes_nivel2(_chunk("AM-8200G"), ["AM-8200"]) is False
    assert sr.passes_nivel2(_chunk("AM-8200N"), ["AM-8200"]) is False


def test_nivel2_direccion_inversa_tambien(full_registry):
    """Query del hermano G: el base no le contamina (hoy ya no pasaba por
    substring; con serie sigue fuera)."""
    assert sr.passes_nivel2(_chunk("AM-8200"), ["AM-8200G"]) is False
    assert sr.passes_nivel2(_chunk("AM-8200G"), ["AM-8200G"]) is True


def test_nivel2_union_comparativas(full_registry):
    """Query multi-modelo 'AM-8200 vs AM-8200G': el chunk del G pasa por SU
    modelo (r2 R4/Z1 — el bug de polaridad de v2 muere aquí)."""
    models = ["AM-8200", "AM-8200G"]
    assert sr.passes_nivel2(_chunk("AM-8200"), models) is True
    assert sr.passes_nivel2(_chunk("AM-8200G"), models) is True
    assert sr.passes_nivel2(_chunk("AM-8200N"), models) is False


def test_nivel2_shared_abre_d2(full_registry):
    """d2: el doc de serie (pm=CAD-250) es visible para la query CAD-201 SOLO
    vía shared_doc declarado; el resto de docs del 250 siguen fuera."""
    mc380 = _chunk("CAD-250", "CAD-250-MC-380-es")
    mi372 = _chunk("CAD-250", "Manual instalacion CAD-250 (MI_372_es_2024 e)")
    assert sr.passes_nivel2(mc380, ["CAD-201"]) is True
    assert sr.passes_nivel2(mi372, ["CAD-201"]) is False
    assert sr.passes_nivel2(_chunk("CAD-201", "Manual_CAD-201-MI-715-es"), ["CAD-201"]) is True


def test_nivel2_shared_case_insensitive(full_registry):
    assert sr.passes_nivel2(_chunk("CAD-250", "cad-250-mc-380-ES"), ["CAD-201"]) is True


def test_nivel2_shared_abre_tambien_para_member_propio(full_registry):
    """La query CAD-250 sigue viendo su MC-380 (owner=query, y además shared)."""
    assert sr.passes_nivel2(_chunk("CAD-250", "CAD-250-MC-380-es"), ["CAD-250"]) is True


def test_nivel2_modelo_sin_serie_es_substring_puro(full_registry):
    """Espejo del test canónico del filtro: CAD-150 no tiene serie → substring
    direccional histórico (familia→variante pasa; producto distinto no)."""
    assert sr.passes_nivel2(_chunk("CAD-150-8"), ["CAD-150"]) is True
    assert sr.passes_nivel2(_chunk("CAD-250"), ["CAD-150"]) is False
    assert sr.series_for("CAD-150") is None


def test_any_series_y_shared_sources(full_registry):
    assert sr.any_series(["AM-8200"]) is True
    assert sr.any_series(["CAD-150", "NFS-320"]) is False
    assert sr.any_series([]) is False
    assert sr.shared_sources_for(["CAD-201"]) == ["CAD-250-MC-380-es"]
    assert sr.shared_sources_for(["CAD-150"]) == []
    # dedupe estable con dos members de la misma serie
    assert sr.shared_sources_for(["CAD-201", "CAD-250"]) == ["CAD-250-MC-380-es"]


# ---------------------------------------------------------------------------
# Loader — fail-open en runtime
# ---------------------------------------------------------------------------

def test_loader_yaml_roto_fail_open(registry_dir, caplog):
    _write(registry_dir, "roto.yaml", "series:\n  - name: [esto no es\n  yaml válido")
    _write(registry_dir, "detnov.yaml", DETNOV_YAML)
    sr.reset_registry_cache()
    with caplog.at_level(logging.WARNING):
        assert sr.series_for("CAD-201") is not None      # el sano carga
    assert sr.registry_stats()[0] == 1                   # el roto se ignora


def test_loader_entradas_malformadas(registry_dir, caplog):
    _write(registry_dir, "raro.yaml", """\
manufacturer: X
series:
  - name: SinMembers
    evidence: "x"
  - "no soy un dict"
  - name: UnMemberSinShared
    members: [SOLO-1]
    evidence: "no hace nada -> anti-degeneración"
  - name: Valida
    members: [AAA-1, AAA-2]
    evidence: "ok"
    shared_docs:
      - evidence: "sin source_file -> se ignora el item"
""")
    sr.reset_registry_cache()
    with caplog.at_level(logging.WARNING):
        n_series, n_members, n_shared = sr.registry_stats()
    assert (n_series, n_members, n_shared) == (1, 2, 0)
    assert sr.series_for("AAA-1") is not None
    assert sr.series_for("SOLO-1") is None


def test_loader_colision_descarta_ambas(registry_dir, caplog):
    _write(registry_dir, "a.yaml", """\
manufacturer: A
series:
  - name: SerieA
    members: [DUP-1, A-2]
    evidence: "x"
""")
    _write(registry_dir, "b.yaml", """\
manufacturer: B
series:
  - name: SerieB
    members: [DUP-1, B-2]
    evidence: "x"
""")
    _write(registry_dir, "c.yaml", DETNOV_YAML)
    sr.reset_registry_cache()
    with caplog.at_level(logging.WARNING):
        assert sr.series_for("DUP-1") is None
    assert sr.series_for("A-2") is None        # la serie entera cae
    assert sr.series_for("B-2") is None
    assert sr.series_for("CAD-201") is not None  # la ajena sobrevive
    assert any("descartadas" in r.message for r in caplog.records)


def test_flag_off_registry_vacio(registry_dir, monkeypatch):
    _write(registry_dir, "detnov.yaml", DETNOV_YAML)
    monkeypatch.setenv("SERIES_REGISTRY_ENABLED", "false")
    sr.reset_registry_cache()
    assert sr.any_series(["CAD-201"]) is False
    assert sr.registry_fingerprint() == "disabled"
    assert sr.registry_stats() == (0, 0, 0)
    # passes_nivel2 sin serie = substring puro (no debería llamarse en nivel 2,
    # pero si se llama no rompe nada)
    assert sr.passes_nivel2(_chunk("CAD-250"), ["CAD-201"]) is False


def test_fingerprint_estable_y_sensible(registry_dir):
    _write(registry_dir, "detnov.yaml", DETNOV_YAML)
    sr.reset_registry_cache()
    fp1 = sr.registry_fingerprint()
    sr.reset_registry_cache()
    fp2 = sr.registry_fingerprint()
    assert fp1 == fp2 and fp1 not in ("empty", "disabled")
    _write(registry_dir, "notifier.yaml", NOTIFIER_YAML)
    sr.reset_registry_cache()
    assert sr.registry_fingerprint() != fp1


def test_registry_vacio_sin_config(registry_dir):
    sr.reset_registry_cache()
    assert sr.registry_fingerprint() == "empty"
    assert sr.any_series(["AM-8200"]) is False


# ---------------------------------------------------------------------------
# Validación DURA de la población REAL (FINAL §1d) — se activa cuando los yaml
# de producción declaren series. Hoy pasa vacía (población pendiente de curación).
# ---------------------------------------------------------------------------

def test_poblacion_real_evidence_obligatorio():
    """Toda serie y shared_doc REAL lleva evidence (la puerta dura que el runtime
    fail-open no impone). Corre contra config/manufacturers de verdad."""
    import yaml as _yaml
    from pathlib import Path
    cfg = Path(sr.__file__).resolve().parent.parent.parent / "config" / "manufacturers"
    problemas: list[str] = []
    for path in sorted(cfg.glob("*.yaml")):
        data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for raw in (data.get("series") or []):
            if not isinstance(raw, dict):
                problemas.append(f"{path.name}: entrada no-dict")
                continue
            if not raw.get("evidence"):
                problemas.append(f"{path.name}: serie {raw.get('name')} sin evidence")
            for item in raw.get("shared_docs") or []:
                if not isinstance(item, dict) or not item.get("source_file"):
                    problemas.append(f"{path.name}: shared_doc inválido en {raw.get('name')}")
                elif not item.get("evidence"):
                    problemas.append(
                        f"{path.name}: shared_doc {item['source_file']} sin evidence")
    assert not problemas, "\n".join(problemas)


@pytest.mark.skipif(not os.getenv("SUPABASE_URL"), reason="integración: requiere DB")
def test_poblacion_real_shared_docs_resuelven_en_corpus(monkeypatch):
    """FINAL §1d (anti-secuestro): cada shared_doc de la población REAL existe en
    chunks_v2 (≥1 chunk) y TODOS sus chunks llevan product_model de la propia
    serie. Caza typos de source_file y aperturas cross-marca. Re-correr tras
    cada ingesta que renombre docs (contrato del workflow de ingesta)."""
    import httpx
    monkeypatch.delenv("SERIES_REGISTRY_ENABLED", raising=False)
    sr.reset_registry_cache()      # fuerza la población real (config/manufacturers)
    try:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        h = {"apikey": key, "Authorization": f"Bearer {key}"}
        problemas: list[str] = []
        for serie in sr._get().series:
            for sf in serie.shared_sources:
                # La población de series es del corpus v2 (DEC-043) — tabla explícita.
                r = httpx.get(
                    f"{url}/rest/v1/chunks_v2", headers=h, timeout=15.0,
                    params={"source_file": f"eq.{sf}",
                            "select": "product_model", "limit": "500"},
                )
                r.raise_for_status()
                rows = r.json()
                if not rows:
                    problemas.append(f"{serie.name}: '{sf}' NO resuelve en chunks_v2")
                    continue
                pms = {x.get("product_model") or "" for x in rows}
                ajenos = {pm for pm in pms
                          if not serie.owners(sr.normalize_model(pm))}
                if ajenos:
                    problemas.append(
                        f"{serie.name}: '{sf}' tiene chunks con pm fuera de la serie: "
                        f"{sorted(ajenos)}")
        assert not problemas, "\n".join(problemas)
    finally:
        sr.reset_registry_cache()
