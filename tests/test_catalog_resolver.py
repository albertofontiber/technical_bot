"""Tests de src/rag/catalog_resolver.py (s91 F2-S1, plan v2.2).

Pinean: detección-en-frase (multi-palabra, negativos digit-only, ZXe len-3 — la bomba r2),
resolución por la puerta (ZXe→variantes, RP1r→Supra prefer [hp011], APIC clarify sin expansión),
los dos brazos de política (add=hipótesis / replace=medido), fail-fast de flags legacy (v2.1a),
shadow no-muta, stamp del catálogo-commit (v2.1b), y el seam 2 (whitelist en
_filter_to_query_models con fail-open ≥3). Skip si data/catalog no está cargado (igual que
test_catalog_store)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.rag import catalog_resolver as R

pytestmark = pytest.mark.skipif(
    not (Path(R.ROOT) / "data" / "catalog" / "products.jsonl").exists(),
    reason="catálogo no cargado")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for f in ("IDENTITY_RESOLVE", "IDENTITY_RESOLVE_POLICY", *R.LEGACY_FLAGS):
        monkeypatch.delenv(f, raising=False)
    # dúo build-S1 #4: los tests NO escriben en la tabla shadow REAL de Supabase — ensuciaría
    # el dataset que S2 lee como evidencia (FP-rate/demanda) + network-call en tests unitarios
    monkeypatch.setattr(R, "_shadow_log", lambda *a, **k: None)
    yield


# ─── flag / fail-fast (v2.1a) ───
def test_mode_default_off():
    assert R.mode() == "off"


def test_mode_invalido(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "yes")
    with pytest.raises(RuntimeError, match="inválido"):
        R.mode()


@pytest.mark.parametrize("legacy", R.LEGACY_FLAGS)
def test_fail_fast_contra_cada_flag_legacy(monkeypatch, legacy):
    monkeypatch.setenv("IDENTITY_RESOLVE", "shadow")
    monkeypatch.setenv(legacy, "1")
    with pytest.raises(RuntimeError, match="EXCLUYENTE"):
        R.mode()


def test_legacy_on_con_resolve_off_no_falla(monkeypatch):
    # el mundo actual (LEVER2 en evals viejos) sigue funcionando con el resolver apagado
    monkeypatch.setenv("LEVER2_IDENTITY", "1")
    assert R.mode() == "off"


def test_lista_de_flags_legacy_cubre_el_codigo():
    # v2.1a (afilado dúo #6): ESCANEO dinámico — cualquier os.getenv de identidad en el código
    # de retrieval debe estar en LEGACY_FLAGS o ser el flag nuevo; un flag nuevo no escapa
    import re
    known = set(R.LEGACY_FLAGS) | {"IDENTITY_RESOLVE", "IDENTITY_RESOLVE_POLICY",
                                   "IDENTITY_FETCH"}
    for fname in ("src/rag/retriever.py", "src/rag/catalog_resolver.py"):
        src = (Path(R.ROOT) / fname).read_text(encoding="utf-8")
        for var in re.findall(r'os\.getenv\(\s*"([A-Z0-9_]+)"', src):
            if "IDENTITY" in var or "LEVER2" in var:
                assert var in known, f"flag de identidad NO registrado en LEGACY_FLAGS: {var} ({fname})"


# ─── detección (regex generada del catálogo) ───
def test_detecta_zxe_en_frase():
    # la bomba r2: norm('ZXe')='zxe' (3 chars) DEBE detectarse
    assert "zxe" in [t.replace(" ", "") for t in R.detect("avería en la central Morley ZXe de 2 lazos")]


def test_detecta_multi_palabra():
    assert any("faast" in t for t in R.detect("sensibilidad del FAAST LT-200"))


def test_no_detecta_digit_only():
    assert R.detect("el código de error 808 en pantalla") == []
    assert R.detect("revisa el 816 y el 777163") == []


def test_no_detecta_en_query_generica():
    assert R.detect("cuántos detectores soporta un lazo estándar de la central") == []


def test_no_detecta_dimensiones_como_paraguas_dimension():
    # dúo build-S1 #2 (reproducido): sin boundary trasero, 'dimensiones' disparaba el
    # paraguas 'Dimension' — y 'dimensiones' es palabra de spec_keywords (query MUY común)
    assert R.detect("cuáles son las dimensiones del panel") == []


def test_hp009_premisa_add_conserva_match_family_level(monkeypatch):
    # hp009 (family-genérico → answer): bajo el brazo ADD, los docs tagueados combinado
    # ('ZX2e/ZX5e', la clase MIE-MI-530) deben seguir pasando el filtro de modelos.
    from src.rag.retriever import _filter_to_query_models

    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "add")
    res = R.resolve_query("central ZXe")
    models = R.apply_to_models(["ZXE"], res)
    chunks = [{"product_model": "ZX2e/ZX5e", "source_file": "MIE-MI-530", "content": "x"}] * 3
    out = _filter_to_query_models(chunks, models)
    assert len(out) == 3, "la expansión ADD no debe expulsar los docs family-level de hp009"


def test_hp009_replace_conserva_match_family_level(monkeypatch):
    # hp009 (family-genérico → answer): retirar el paraguas no debe expulsar los
    # documentos combinados ('ZX2e/ZX5e', la clase MIE-MI-530), porque las
    # variantes canónicas siguen siendo cores válidos del tag compuesto.
    from src.rag.retriever import _filter_to_query_models
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("central ZXe")
    models = R.apply_to_models(["ZXE"], res)
    assert "ZXE" not in models
    chunks = [{"product_model": "ZX2e/ZX5e", "source_file": "MIE-MI-530", "content": "x"}] * 3
    out = _filter_to_query_models(chunks, models)
    assert len(out) == 3, "REPLACE no debe expulsar los docs family-level de hp009"


def test_zxe_replace_expulsa_legacy_zxae_zxee_y_conserva_familia(monkeypatch):
    from src.rag.retriever import _filter_to_query_models

    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("conectar una sirena convencional en Morley ZXe")
    models = R.apply_to_models(["ZXE"], res)
    chunks = (
        [_chunk("ZXAE/ZXEE", "MIE-MI-310")] * 3
        + [_chunk("ZX2e/ZX5e", "MIE-MI-530rv001")] * 3
    )

    out = _filter_to_query_models(
        chunks, models, identity_allowed=res["allowed_sources"]
    )

    assert {c["product_model"] for c in out} == {"ZX2e/ZX5e"}
    assert {c["source_file"] for c in out} == {"MIE-MI-530rv001"}


# ─── resolución por la puerta (contrato expand) ───
def test_zxe_expande_a_variantes():
    res = R.resolve_query("central ZXe")
    rec = next(r for r in res["records"] if "zx" in r["token"])
    assert rec["via"] == "paraguas" and rec["expand"] is True
    assert set(rec["ids"]) == {"morley:zx1e", "morley:zx2e", "morley:zx5e"}
    assert set(res["add_models"]) == {"ZX1e", "ZX2e", "ZX5e"}


def test_hp011_rp1r_prefer_supra():
    res = R.resolve_query("conectar el RP1r al software de gestión")
    rec = next(r for r in res["records"] if r["token"] == "rp1r")
    assert rec["via"] == "homonimo" and rec["politica"] == "prefer:notifier:rp1r-supra"
    assert rec["ids"] == ["notifier:rp1r-supra"] and rec["expand"] is True


def test_hp011_rp1r_resolves_governed_document_scope():
    res = R.resolve_query("conectar el RP1r al software de gestión")

    assert {
        "document_id": "494e71be-873b-48c1-adb3-a21a122da111",
        "source_file": "HLSI-MN-103_RP1r-Supra_lr",
    } in res["resolved_documents"]
    assert all(
        set(document) == {"document_id", "source_file"}
        and document["document_id"]
        and document["source_file"]
        for document in res["resolved_documents"]
    )


def test_apic_clarify_no_expande():
    res = R.resolve_query("tarjeta APIC compatible")
    rec = next(r for r in res["records"] if r["token"] == "apic")
    assert rec["expand"] is False
    assert res["add_models"] == [] and res["allowed_sources"] == frozenset()
    assert res["source_groups"] == []


def test_cross_product_resolution_keeps_document_scopes_separate():
    res = R.resolve_query(
        "central Detnov CAD-150 con detector Notifier SDX-751"
    )
    groups = {
        row["token"].casefold(): set(row["sources"])
        for row in res["source_groups"]
    }
    assert len(groups) == 2
    assert "MIDT190" in groups["sdx-751"]
    assert any("CAD-150-8" in source for source in groups["cad-150"])


def test_zxse_expande_y_permite_mie_mi_600():
    # la clase pm=unknown: el doc de la familia ZXSe debe estar en allowed_sources
    res = R.resolve_query("central ZXSe instalación")
    assert res["add_models"], "ZXSe debe expandir a variantes"
    assert any("MIE-MI-600" in s for s in res["allowed_sources"])


# ─── seam 1: brazos add / replace ───
def test_brazo_add_conserva_el_token(monkeypatch):
    res = R.resolve_query("central ZXe")
    out = R.apply_to_models(["ZXE"], res)
    assert out[0] == "ZXE" and {"ZX1e", "ZX2e", "ZX5e"} <= set(out)


def test_brazo_replace_retira_el_paraguas(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("central ZXe")
    out = R.apply_to_models(["ZXE"], res)
    assert "ZXE" not in out and {"ZX1e", "ZX2e", "ZX5e"} == set(out)


# ─── s278 §1a: guard candidate-member + quarantine (drop gobernado bajo replace) ───
def test_resolve_expone_all_members_consumable():
    # contrato GUARD-IMPL: la expansión que FILTRÓ miembros lo declara (FAAST filtra a
    # notifier:faast-8100e, candidate); la limpia (ZXe) y el prefer adjudicado (RP1r —
    # la expansión es SOLO el id preferido) devuelven True. `exact` no lleva el campo
    # (nunca drop-elegible; shape pineado en test_catalog_store.py::test_resolve_exact).
    R._ensure()
    faast = R._cat.resolve("FAAST")
    assert faast["via"] == "paraguas" and faast["expand"] is True
    assert faast["all_members_consumable"] is False
    assert R._cat.resolve("ZXe")["all_members_consumable"] is True
    assert R._cat.resolve("RP1r")["all_members_consumable"] is True


def test_faast_no_dropea_bajo_replace_por_guard_candidate_member(monkeypatch):
    # census s278 umbrella:FAAST: la expansión filtra notifier:faast-8100e (candidate) —
    # dropear el token perdería los docs solo alcanzables vía 'FAAST' (I56-3836-006 8100E,
    # Area Coverage Planner_SP, Understanding EN54-20_SP). La quarantine se vacía aquí
    # para aislar el GUARD (FAAST está en ambos mecanismos a propósito).
    monkeypatch.setattr(R, "_quarantine", frozenset())
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de FAAST")
    assert res["drop_tokens"] == []
    out = R.apply_to_models(["FAAST"], res)
    assert "FAAST" in out and len(out) > 1    # token conservado + expansión añadida (== add)


def test_zxr_y_g100r_no_dropean_bajo_replace_por_quarantine(monkeypatch):
    # census s278: el guard NO cubre estas unidades (ZXR: miembros consumibles pero
    # MIE-MI-430 es de zxr4b/5b no-miembros; G-100-R: vía alias a destino consumible) —
    # sin quarantine habría pérdida real de docs bajo replace.
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de ZXR")
    assert res["drop_tokens"] == []
    out = R.apply_to_models(["ZXR"], res)
    assert "ZXR" in out and {"ZXR50A", "ZXR50P"} <= set(out)
    res_g = R.resolve_query("manual de G-100-R")
    assert res_g["drop_tokens"] == []
    out_g = R.apply_to_models(["G-100-R"], res_g)
    assert "G-100-R" in out_g and "G-100-R-12" in out_g


def test_zxe_umbrella_limpia_si_dropea_bajo_replace(monkeypatch):
    # el guard NO interfiere con el caso medido (hp018): TODOS los miembros de ZXe son
    # consumibles y no está en quarantine → el drop del paraguas sigue vivo
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("central ZXe")
    assert "zxe" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["ZXE"], res)
    assert "ZXE" not in out


def test_homonimo_prefer_rp1r_sigue_dropeando_bajo_replace(monkeypatch):
    # el prefer adjudicado (hp011) queda intacto: su expansión = solo el id preferido
    # consumible → all_members_consumable=True → el guard no bloquea el drop
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("conectar el RP1r al software de gestión")
    assert "rp1r" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["RP1r"], res)
    assert "RP1r" not in out and "RP1r-Supra" in out


def test_quarantine_vacia_solo_el_guard_decide(monkeypatch):
    # con la quarantine vacía (Alberto adjudicó todo) el drop lo gobierna SOLO el guard:
    # ZXR (miembros consumibles) vuelve a dropear; FAAST sigue protegida (miembro candidate)
    monkeypatch.setattr(R, "_quarantine", frozenset())
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res_zxr = R.resolve_query("manual de ZXR")
    assert "zxr" in {R.catalog_store.norm_token(t) for t in res_zxr["drop_tokens"]}
    res_faast = R.resolve_query("manual de FAAST")
    assert res_faast["drop_tokens"] == []


def test_quarantine_malformada_fail_fast(monkeypatch, tmp_path):
    # el diseño exige fail-fast: una quarantine rota que fallara en silencio desactivaría
    # la protección justo bajo replace
    bad = tmp_path / "identity_quarantine_v1.yaml"
    bad.write_text("tokens:\n  - token: ''\n    motivo: x\n    fecha: '2026-07-22'\n",
                   encoding="utf-8")
    monkeypatch.setattr(R, "_QUARANTINE_PATH", bad)
    monkeypatch.setattr(R, "_quarantine", None)
    with pytest.raises(RuntimeError, match="quarantine"):
        R._quarantine_tokens()
    monkeypatch.setattr(R, "_QUARANTINE_PATH", tmp_path / "no-existe.yaml")
    with pytest.raises(RuntimeError, match="AUSENTE"):
        R._quarantine_tokens()


# ─── entrada única del retriever ───
def test_off_passthrough_exacto():
    models, res = R.resolve_for_retrieval("central ZXe", ["ZXE"])
    assert models == ["ZXE"] and res is None


def test_shadow_no_muta(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "shadow")
    models, res = R.resolve_for_retrieval("central ZXe", ["ZXE"])
    assert models == ["ZXE"] and res is None


def test_on_aplica_seam1_y_devuelve_allowed(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    models, res = R.resolve_for_retrieval("central ZXe", ["ZXE"])
    assert {"ZX1e", "ZX2e", "ZX5e"} <= set(models)
    assert res is not None and len(res["allowed_sources"]) > 0


def test_on_sin_tokens_passthrough(monkeypatch):
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    models, res = R.resolve_for_retrieval("cuántos detectores soporta un lazo", ["X999"])
    assert models == ["X999"] and res is None


# ─── seam 2: whitelist en _filter_to_query_models ───
def _chunk(pm, src):
    return {"product_model": pm, "source_file": src, "content": "x"}


def test_seam2_union_protectora_reincorpora_pm_unknown():
    # dúo build-S1 #1: el filtro medido corre INTACTO y los chunks de docs adjudicados se
    # RE-INCORPORAN si el veto los tiró — no reemplaza al filtro
    from src.rag.retriever import _filter_to_query_models
    allowed = frozenset({"MIE-MI-600"})
    chunks = ([_chunk("ZX2Se", "doc-x")] * 3
              + [_chunk("unknown", "MIE-MI-600")] * 3
              + [_chunk("ZXAE", "MIE-MI-310")])
    out = _filter_to_query_models(chunks, ["ZX2Se"], identity_allowed=allowed)
    assert sum(1 for c in out if c["product_model"] == "ZX2Se") == 3      # el filtro medido, intacto
    assert sum(1 for c in out if c["source_file"] == "MIE-MI-600") == 3   # protegidos re-incorporados
    assert not any(c["product_model"] == "ZXAE" for c in out)             # el veto a hermanos sigue


def test_seam2_no_estrecha_el_pool_de_otros_modelos():
    # el replace antiguo vetaba chunks legítimos de docs SIN entrada en doc_map (861/1014);
    # la unión nunca deja el resultado más estrecho que el filtro medido
    from src.rag.retriever import _filter_to_query_models
    allowed = frozenset({"MIE-MI-600"})
    chunks = [_chunk("unknown", "MIE-MI-600")] * 2 + [_chunk("CAD-150-8", "55315013")] * 3
    out = _filter_to_query_models(chunks, ["CAD-150"], identity_allowed=allowed)
    base = _filter_to_query_models(chunks, ["CAD-150"])
    assert {id(c) for c in base} <= {id(c) for c in out}
    assert sum(1 for c in out if c["product_model"] == "CAD-150-8") == 3


def test_seam2_none_es_el_comportamiento_actual():
    from src.rag.retriever import _filter_to_query_models
    chunks = [_chunk("CAD-150-8", "55315013")] * 3 + [_chunk("CAD-250", "otros")]
    a = _filter_to_query_models(chunks, ["CAD-150"])
    b = _filter_to_query_models(chunks, ["CAD-150"], identity_allowed=None)
    assert a == b and all(c["product_model"] == "CAD-150-8" for c in a)


# ─── stamp (v2.1b) ───
def test_catalog_commit_stamp():
    st = R.catalog_commit()
    assert st and st != "unknown"


# ─── round-trip muestreado (H8: negativos > tautología) ───
def test_roundtrip_muestra_de_canonicals():
    import json
    rows = [json.loads(l) for l in
            (Path(R.ROOT) / "data" / "catalog" / "products.jsonl").open(encoding="utf-8")]
    consum = [r for r in rows if r.get("estado") == "activo" and not r.get("candidate")][::40]
    fallos = []
    for p in consum:
        cm = p["canonical_model"]
        segs = "".join(__import__("re").findall(r"[a-z]+|\d+", cm.lower()))
        if not segs or segs.isdigit():
            continue                      # digit-only: excluido del detector a propósito
        if not R.detect(f"manual del {cm} por favor"):
            fallos.append(cm)
    assert not fallos, f"canonicals no detectados: {fallos[:10]}"


# ─── s92: la clase FP 'palabra-común-como-alias' (1er replay sobre golds la cazó) ───
def test_no_detecta_palabras_comunes_de_alias_nombre_largo():
    # 'Solo' (detectortesters), colores, descripciones — alias nombre-largo SIN dígito
    # NO entran al detector (hp005 tenía 'solo' adverbio → expandía a test-equipment)
    assert R.detect("solo quiero saber el consumo del detector") == []
    assert R.detect("el cable verde y el amarillo van al positivo") == []
    assert R.detect("qué dimensión tiene la central") == []


def test_nombre_largo_con_digito_si_detecta():
    # la regla es por FORMA (dígito), no por tipo: 'ASD535' es nombre-largo pero model-shaped
    assert R.detect("avería en el ASD535 por flujo bajo") != []


def test_stopwords_explicitos():
    for w in R.DETECT_STOPWORDS:
        assert R.detect(f"pregunta sobre {w} en la instalación") == []


# ─── s93: fetch acotado (escalera v2.1d) ───
def test_fetch_off_por_defecto():
    assert R.fetch_enabled() is False


def test_fetch_requiere_resolve_on(monkeypatch):
    monkeypatch.setenv("IDENTITY_FETCH", "on")
    with pytest.raises(RuntimeError, match="requiere IDENTITY_RESOLVE=on"):
        R.fetch_enabled()
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    assert R.fetch_enabled() is True


def test_fetch_append_puro_no_desplaza(monkeypatch):
    # si todos los docs adjudicados YA están en el pool → no trae nada (y nunca quita)
    res = {"allowed_sources": frozenset({"MIE-MI-600"})}
    pool = [{"id": "x", "source_file": "MIE-MI-600"}]
    assert R.fetch_missing_doc_chunks("central ZXSe", res, pool) == []


def test_fetch_marca_los_chunks(monkeypatch):
    # doc ausente → fetch por REST (mockeado) con marcador identity_fetch
    calls = {}
    class _R:
        status_code = 200
        def json(self):
            return [{"id": f"c{i}", "content": f"la central ZXSe seccion {i}",
                     "source_file": "MIE-MI-600", "product_model": "unknown"} for i in range(6)]
    class _Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, headers=None, params=None):
            calls["params"] = params
            return _R()
    import httpx
    monkeypatch.setattr(httpx, "Client", _Client)
    res = {"allowed_sources": frozenset({"MIE-MI-600"})}
    out = R.fetch_missing_doc_chunks("instalación de la central ZXSe", res, [])
    assert len(out) == R.FETCH_PER_DOC and all(c["identity_fetch"] for c in out)
    assert calls["params"]["source_file"] == "eq.MIE-MI-600"
    assert calls["params"]["order"] == "id.asc"        # F3: determinismo del fetch


def test_fetch_cap_max_docs(monkeypatch):
    # F7: >FETCH_MAX_DOCS docs ausentes → solo los 4 primeros (orden alfabético estable)
    seen = []
    class _R:
        status_code = 200
        def json(self): return []
    class _Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, headers=None, params=None):
            seen.append(params["source_file"])
            return _R()
    import httpx
    monkeypatch.setattr(httpx, "Client", _Client)
    res = {"allowed_sources": frozenset({f"DOC-{i}" for i in range(7)})}
    R.fetch_missing_doc_chunks("query de prueba tecnica", res, [])
    assert len(seen) == R.FETCH_MAX_DOCS
    assert seen == sorted(seen)


def test_invariante_colocacion_fetch_tras_el_corte():
    # F1/F7 dúo s93: el hook DEBE vivir tras merged[:top_k] — antes, el append moría
    # truncado (no-op silencioso) o desplazaba vía diversify (la clase DEC-069).
    # Guard textual: quien reordene los steps rompe este test, no la medición.
    src = (Path(R.ROOT) / "src" / "rag" / "retriever.py").read_text(encoding="utf-8")
    i_cut = src.index("base = merged[:top_k]")
    i_hook = src.index("fetch_missing_doc_chunks(query, _identity_res, base)")
    i_div = src.index("Step 5a: Multi-doc diversity")
    assert i_div < i_cut < i_hook, "el fetch debe ir DESPUÉS del corte [:top_k] y del diversify"


def test_score_chunk_word_boundary_y_stopwords():
    assert R._score_chunk("modulo con protocolo CLIP integrado", ["clip"]) == 1
    assert R._score_chunk("un eclipse total", ["clip"]) == 0            # F6: boundary
    assert "para" in R._QSTOP and "central" in R._QSTOP


# ---------- s95 piloto D: parser 3-estados + brazo llm ----------

def test_fetch_mode_3_estados(monkeypatch):
    """(s95 [D-cross-1 CRÍTICO]) 'llm' NO puede ser NO-OP silencioso."""
    from src.rag import catalog_resolver as cr
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    for raw, esperado in [("", "off"), ("off", "off"), ("on", "on"), ("llm", "llm")]:
        monkeypatch.setenv("IDENTITY_FETCH", raw)
        assert cr.fetch_mode() == esperado, raw
    monkeypatch.setenv("IDENTITY_FETCH", "lllm")   # typo → error, no silencio
    import pytest as _pt
    with _pt.raises(RuntimeError):
        cr.fetch_mode()


def test_fetch_llm_exige_resolve_on(monkeypatch):
    from src.rag import catalog_resolver as cr
    monkeypatch.setenv("IDENTITY_FETCH", "llm")
    monkeypatch.setenv("IDENTITY_RESOLVE", "off")
    import pytest as _pt
    with _pt.raises(RuntimeError):
        cr.fetch_enabled()


def test_fetch_llm_activa_deep_lookup(monkeypatch):
    """flag=llm → el seam llama a deep_lookup (NO al score léxico)."""
    from src.rag import catalog_resolver as cr
    monkeypatch.setenv("IDENTITY_FETCH", "llm")
    monkeypatch.setenv("IDENTITY_RESOLVE", "on")
    llamadas = []
    import src.rag.deep_lookup as dl
    monkeypatch.setattr(dl, "deep_lookup",
                        lambda q, src: llamadas.append(src) or [{"id": f"x-{src}",
                                                                 "identity_fetch": "llm"}])
    res = {"allowed_sources": ["DOC-A", "DOC-B"]}
    out = cr.fetch_missing_doc_chunks("¿spec?", res, pool=[])
    assert llamadas == ["DOC-A", "DOC-B"]
    assert [c["id"] for c in out] == ["x-DOC-A", "x-DOC-B"]


# ─── s278 §2a: INSPIRE gobernado (cat017) — diseño evals/s278_vnext_design_v2.md §2 ───
CAT017_QUERY = ("¿Cómo genero el fichero de licencia .bin para una central "
                "INSPIRE E10 con CLSS?")
CAT017_SOURCE = "HOP-138-8ES  issue 6_01-2026_Co"     # doble espacio REAL (handoff §8.2)


def test_cat017_inspire_e10_detecta_y_resuelve():
    # antes de s278 §2a: detect(...) == [] (censo: cat017 DOCUMENTED_UNGOVERNED).
    # Gobernada: exact 'INSPIRE E10' → notifier:inspire-e10 con expand y el doc de cat017
    # (chunk b7633e98 / document 80e1b7d2) alcanzable vía allowed_sources.
    assert R.detect(CAT017_QUERY) != []
    res = R.resolve_query(CAT017_QUERY)
    rec = next(r for r in res["records"] if r["token"] == "inspire e10")
    assert rec["via"] == "exact" and rec["expand"] is True
    assert rec["ids"] == ["notifier:inspire-e10"]
    assert CAT017_SOURCE in res["allowed_sources"]
    assert "INSPIRE E10" in res["add_models"]


def test_inspire_umbrella_expande_a_e10_y_e15():
    res = R.resolve_query("manual de la central INSPIRE")
    rec = next(r for r in res["records"] if r["token"] == "inspire")
    assert rec["via"] == "paraguas" and rec["expand"] is True
    assert set(rec["ids"]) == {"notifier:inspire-e10", "notifier:inspire-e15"}
    assert {"INSPIRE E10", "INSPIRE E15"} <= set(res["add_models"])


def test_formas_prefijadas_notifier_inspire_via_alias():
    # tipo variante-tipografica ∈ DETECT_ALIAS_TIPOS ⇒ el detector las indexa
    for m, pid in (("E10", "notifier:inspire-e10"), ("E15", "notifier:inspire-e15")):
        res = R.resolve_query(f"consumo de la Notifier INSPIRE {m}")
        rec = next(r for r in res["records"] if r["token"] == f"notifier inspire {m.lower()}")
        assert rec["via"] == "alias" and rec["expand"] is True and rec["ids"] == [pid]


def test_e10_e15_bare_no_expanden_fail_open():
    # hallazgo E10-BARE (dúo r1): 'E10'/'E15' a pelo colisionan con códigos de error de
    # panel → homonym-candidate fail-open: se DETECTA (bloquea el exact) pero NO expande,
    # NO clarify, NO aporta allowed_sources — conducta actual conservada.
    for tok in ("E10", "E15"):
        res = R.resolve_query(f"el panel muestra el código {tok} en pantalla")
        rec = next(r for r in res["records"] if r["token"] == tok.lower())
        assert rec["via"] == "homonimo-candidate" and rec["expand"] is False
        assert rec["politica"] == "fail-open" and rec["ids"] == []
        assert res["add_models"] == [] and res["drop_tokens"] == []
        assert res["allowed_sources"] == frozenset()


def test_inspire_quarantine_vigente_no_dropea_bajo_replace(monkeypatch):
    # INSPIRE está en config/identity_quarantine_v1.yaml (census post-§2a: el doc de
    # firmware de notifier:inspire, candidate NO-miembro, se perdería bajo replace) ⇒
    # fail-open-a-add hasta que Alberto adjudique, AUNQUE el guard permitiría el drop.
    assert R._cat.resolve("INSPIRE")["all_members_consumable"] is True
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de la central INSPIRE")
    assert "inspire" not in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["INSPIRE"], res)
    assert "INSPIRE" in out and {"INSPIRE E10", "INSPIRE E15"} <= set(out)
    assert CAT017_SOURCE in res["allowed_sources"]


def test_inspire_droppable_bajo_replace_con_quarantine_adjudicada(monkeypatch):
    # con la fila INSPIRE adjudicada (quarantine vacía), el guard GUARD-IMPL gobierna:
    # miembros consumibles ⇒ droppable. Census-safe: los doc_map de AMBOS miembros
    # quedan en allowed_sources (unión protectora seam-2), incluido el doc de cat017.
    monkeypatch.setattr(R, "_quarantine", frozenset())
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de la central INSPIRE")
    assert "inspire" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["INSPIRE"], res)
    assert "INSPIRE" not in out and {"INSPIRE E10", "INSPIRE E15"} <= set(out)
    docs_miembros = (R._docs_by_id.get("notifier:inspire-e10", frozenset())
                     | R._docs_by_id.get("notifier:inspire-e15", frozenset()))
    assert docs_miembros and docs_miembros <= res["allowed_sources"]
    assert CAT017_SOURCE in res["allowed_sources"]


def test_deep_lookup_seleccion_pagina_exacta_primero(monkeypatch):
    """[D4] página exacta primero, ±1 después, orden chunk_index, cap 6, sin re-corte léxico."""
    import src.rag.deep_lookup as dl

    class _R:
        status_code = 200
        def __init__(self, rows): self._rows = rows
        def json(self): return self._rows

    class _C:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, headers=None, params=None):
            pages = params["page_number"]          # "in.(31)" luego "in.(30,32)"
            if pages == "in.(31)":
                return _R([{"id": "a", "page_number": 31, "chunk_index": 2},
                           {"id": "b", "page_number": 31, "chunk_index": 5}])
            return _R([{"id": "c", "page_number": 30, "chunk_index": 1},
                       {"id": "d", "page_number": 32, "chunk_index": 9}])

    monkeypatch.setattr(dl.httpx, "Client", _C)
    out = dl.fetch_pages_chunks("DOC", [31])
    assert [c["id"] for c in out] == ["a", "b", "c", "d"]       # exacta primero
    assert all(c["identity_fetch"] == "llm" for c in out)
