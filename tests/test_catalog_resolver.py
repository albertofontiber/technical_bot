"""Tests de src/rag/catalog_resolver.py (s91 F2-S1, plan v2.2).

Pinean: detección-en-frase (multi-palabra, negativos digit-only, ZXe len-3 — la bomba r2),
resolución por la puerta (ZXe→variantes, RP1r→Supra prefer [hp011], APIC clarify sin expansión),
los dos brazos de política (add=hipótesis / replace=medido), fail-fast de flags legacy (v2.1a),
shadow no-muta, stamp del catálogo-commit (v2.1b), y el seam 2 (whitelist en
_filter_to_query_models con fail-open ≥3). Skip si data/catalog no está cargado (igual que
test_catalog_store)."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest

from src.rag import catalog_resolver as R

pytestmark = pytest.mark.skipif(
    not (Path(R.ROOT) / "data" / "catalog" / "products.jsonl").exists(),
    reason="catálogo no cargado")


# referencias a las implementaciones REALES, capturadas ANTES de que el fixture autouse las
# prohíba: los tests que ejercitan el fetch/fingerprint de verdad (con httpx mockeado) las
# re-inyectan a mano.
_fetch_real = R._fetch_corpus_pm_elements
_fingerprint_real = R._corpus_fingerprint


class _RedProhibida(BaseException):
    """Deriva de BaseException A PROPÓSITO: los fail-open del resolver capturan
    `Exception`, así que un test que se cuele a la DB debe REVENTAR, no degradar en
    silencio a 'presencia desconocida'."""


def _inject_presence(monkeypatch, elements, *, fp=("fixture", "fixture")):
    """(s287 P1) Inyecta la presencia de corpus SIN RED sembrando el cache de proceso del
    resolver. `elements=None` simula «DB no consultable» (fail-open a conservar)."""
    now = time.monotonic()
    monkeypatch.setattr(R, "_presence", {
        "elements": None if elements is None else frozenset(elements),
        "at": now, "fp": fp, "fp_at": now})


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for f in ("IDENTITY_RESOLVE", "IDENTITY_RESOLVE_POLICY", *R.LEGACY_FLAGS):
        monkeypatch.delenv(f, raising=False)
    # dúo build-S1 #4: los tests NO escriben en la tabla shadow REAL de Supabase — ensuciaría
    # el dataset que S2 lee como evidencia (FP-rate/demanda) + network-call en tests unitarios
    monkeypatch.setattr(R, "_shadow_log", lambda *a, **k: None)
    # s287 P1: la regla monótona-segura añade una dependencia DB al resolver. Default de los
    # tests = corpus SIN presencia (set VACÍO) ⇒ conducta EXACTA pre-P1, de modo que los
    # contratos s278 del drop siguen pinneando lo suyo (guard candidate-member + quarantine)
    # y no la etiqueta viva del corpus. Quien necesite presencia la INYECTA.
    _inject_presence(monkeypatch, ())

    def _prohibida(*a, **k):
        raise _RedProhibida("presencia de corpus: los tests la INYECTAN, no la consultan")
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements", _prohibida)
    monkeypatch.setattr(R, "_corpus_fingerprint", _prohibida)
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
    # s287 P1 (SUNSET del hotfix P0.5 CUMPLIDO — 'zxe' YA NO está en quarantine): lo que
    # conserva el token es la REGLA MONÓTONA-SEGURA CORPUS-AWARE — T3/s285 dejó el
    # tag-FAMILIA 'ZXe' vivo en el corpus (elemento 'zxe' presente, verificado: 11 filas
    # pm='ZXe' + composite 'ZXe/ZXSe') ⇒ el drop se SUPRIME. Observable IDÉNTICO al hotfix.
    # Pin s278 anterior (pre-P0.5): assert "ZXE" not in models.
    from src.rag.retriever import _filter_to_query_models
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, {"zxe"})
    res = R.resolve_query("central ZXe")
    models = R.apply_to_models(["ZXE"], res)
    assert "ZXE" in models
    chunks = [{"product_model": "ZX2e/ZX5e", "source_file": "MIE-MI-530", "content": "x"}] * 3
    out = _filter_to_query_models(chunks, models)
    assert len(out) == 3, "REPLACE no debe expulsar los docs family-level de hp009"


def test_zxe_replace_expulsa_legacy_zxae_zxee_y_conserva_familia(monkeypatch):
    # s287 P1 (mismo observable que el hotfix P0.5, ahora por la regla corpus-aware): con
    # 'zxe' conservado (drop suprimido), los legacy ZXAE/ZXEE se RE-ADMITEN por el substring
    # DEL FILTRO ('zxe' ⊂ 'zxee') — comportamiento-ADD medido (DEC-084: hp018 4/4). OJO: el
    # substring vive en `_filter_to_query_models`, NO en la regla de presencia (que es
    # exact-tag por elemento) → el riesgo DEC-091b (valor-coincidente) PERSISTE y se declara.
    # Pin s278 anterior: solo {"ZX2e/ZX5e"} / {"MIE-MI-530rv001"} sobrevivían.
    from src.rag.retriever import _filter_to_query_models

    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, {"zxe"})
    res = R.resolve_query("conectar una sirena convencional en Morley ZXe")
    models = R.apply_to_models(["ZXE"], res)
    chunks = (
        [_chunk("ZXAE/ZXEE", "MIE-MI-310")] * 3
        + [_chunk("ZX2e/ZX5e", "MIE-MI-530rv001")] * 3
    )

    out = _filter_to_query_models(
        chunks, models, identity_allowed=res["allowed_sources"]
    )

    assert {c["product_model"] for c in out} == {"ZXAE/ZXEE", "ZX2e/ZX5e"}
    assert {c["source_file"] for c in out} == {"MIE-MI-310", "MIE-MI-530rv001"}


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
    # s287 P0.5/P1: el ejemplar del brazo replace pasa de ZXe (conservado por la regla
    # corpus-aware) a ZXR — el CONTRATO del brazo (retirar el paraguas) queda intacto.
    # Presencia inyectada = el estado REAL del corpus para esta familia (tags 'ZXR50A/ZXR50P'
    # y 'ZXR5B/ZXR4B'; NO existe un pm 'ZXR' pelado) = estado SOLO-VARIANTES ⇒ el drop
    # procede, que es el punto: la regla no anestesia el brazo replace.
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, {"zxr50a", "zxr50p", "zxr4b", "zxr5b"})
    res = R.resolve_query("central ZXR")
    out = R.apply_to_models(["ZXR"], res)
    assert "ZXR" not in out and {"ZXR4B", "ZXR5B"} <= set(out)


# ─── s278 §1a: guard candidate-member + quarantine (drop gobernado bajo replace) ───
def test_resolve_expone_all_members_consumable():
    # contrato GUARD-IMPL: la expansión que FILTRA miembros lo declara. Tras la adjudicación
    # de Alberto (22-jul, s278) FAAST ya NO filtra (notifier:faast-8100e promovido a miembro
    # pleno) — las tres devuelven True. `exact` no lleva el campo (nunca drop-elegible;
    # shape pineado en test_catalog_store.py::test_resolve_exact).
    R._ensure()
    faast = R._cat.resolve("FAAST")
    assert faast["via"] == "paraguas" and faast["expand"] is True
    assert faast["all_members_consumable"] is True
    assert R._cat.resolve("ZXe")["all_members_consumable"] is True
    assert R._cat.resolve("RP1r")["all_members_consumable"] is True


def test_faast_dropea_bajo_replace_tras_adjudicacion(monkeypatch):
    # s278 adjudicado (Alberto 22-jul): notifier:faast-8100e candidate:false — TODOS los
    # miembros consumibles ⇒ el guard permite el drop y los docs de doc_map de los miembros
    # (incl. los 2 del 8100E) quedan en allowed_sources. NOTA medida: el 3er doc del census
    # (I56-3836-006_FAAST_XM_8100E_ML) pertenece en doc_map a systemsensor:8100e-faast
    # (duplicado candidate NO-miembro) y sigue FUERA de allowed_sources — residual declarado.
    # s287 P1: este test pinea las puertas 1-3 (via/guard/quarantine) con la presencia de
    # corpus inyectada VACÍA por el fixture. En el corpus REAL 'faast' ES elemento vivo ⇒ la
    # puerta 4 lo CONSERVA (ver test_efecto_corpus_wide_de_la_regla_no_es_solo_zxe).
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de FAAST")
    assert "faast" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["FAAST"], res)
    assert "FAAST" not in out and "FAAST 8100E" in out
    assert {"FAAST Area Coverage Planner_SP",
            "FAAST Understanding EN54-20_SP"} <= res["allowed_sources"]


def test_zxr_dropea_bajo_replace_y_mie_mi_430_alcanzable(monkeypatch):
    # s278 adjudicado (Alberto 22-jul): zxr4b/zxr5b son miembros de la umbrella ZXR —
    # el drop bajo replace es limpio y MIE-MI-430 (el doc que la quarantine protegía)
    # queda alcanzable vía los miembros nuevos.
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de ZXR")
    assert "zxr" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["ZXR"], res)
    assert "ZXR" not in out
    assert {"ZXR50A", "ZXR50P", "ZXR4B", "ZXR5B"} <= set(out)
    assert "MIE-MI-430" in res["allowed_sources"]


def test_g100r_resuelve_como_umbrella_y_dropea_bajo_replace(monkeypatch):
    # s278 adjudicado (gt Alberto): G-100-R = familia de tarjetas de relé COMPARTIDAS
    # G-100/G-500 → umbrella {r8, r16, r-12, r-24}; los aliases 'G-100-R'/'G-100-R-xx'
    # (→ solo r-12) se RETIRARON para que el término resuelva por umbrella (orden
    # homónimo→exact→alias→paraguas: un alias residual la taparía).
    R._ensure()
    rec = R._cat.resolve("G-100-R")
    assert rec["via"] == "paraguas" and rec["expand"] is True
    assert set(rec["ids"]) == {"notifier:g-100-r8", "notifier:g-100-r16",
                               "notifier:g-100-r-12", "notifier:g-100-r-24"}
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de G-100-R")
    assert "g100r" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    assert {"MNDT500", "MNDT503", "MNDT506"} <= res["allowed_sources"]


def test_g100_y_g500_expanden_a_sus_paneles():
    # s278 adjudicado (gt Alberto): MNDT503 = serie G-100 {G-100-4, G-100-8};
    # MNDT500 = serie G-500 {G-500-S-32, G-500-S-64}. Los aliases 'G-500'/'G-500-S'
    # (→ solo s-32, incompletos) se retiraron; 'G-500-B 32' (superficie específica) queda.
    R._ensure()
    g100 = R._cat.resolve("G-100")
    assert g100["via"] == "paraguas" and g100["expand"] is True
    assert set(g100["ids"]) == {"notifier:g-100-4", "notifier:g-100-8"}
    g500 = R._cat.resolve("G-500")
    assert g500["via"] == "paraguas" and g500["expand"] is True
    assert set(g500["ids"]) == {"notifier:g-500-s-32", "notifier:g-500-s-64"}
    res = R.resolve_query("manual de la central G-500")
    assert {"G-500-S-32", "G-500-S-64"} <= set(res["add_models"])
    assert "MNDT500" in res["allowed_sources"]


def test_zxe_no_dropea_por_la_regla_corpus_aware(monkeypatch):
    # s287 P1 (antes `test_zxe_umbrella_limpia_si_dropea_bajo_replace`): el drop queda
    # suprimido aunque el guard candidate-member (all_members_consumable) lo permitiría y
    # aunque la quarantine esté VACÍA — lo suprime la puerta 4 (core 'zxe' con presencia
    # exact-tag en el corpus). Pin s278 anterior: 'zxe' in drop_tokens y 'ZXE' expulsado.
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, {"zxe"})
    R._ensure()
    assert R._cat.resolve("ZXe")["all_members_consumable"] is True   # el guard NO es la causa
    assert R.catalog_store.norm_token("ZXe") not in R._quarantine_tokens()
    res = R.resolve_query("central ZXe")
    assert "zxe" not in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["ZXE"], res)
    assert "ZXE" in out


def test_homonimo_prefer_rp1r_sigue_dropeando_bajo_replace(monkeypatch):
    # el prefer adjudicado (hp011) queda intacto: su expansión = solo el id preferido
    # consumible → all_members_consumable=True → el guard no bloquea el drop
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("conectar el RP1r al software de gestión")
    assert "rp1r" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["RP1r"], res)
    assert "RP1r" not in out and "RP1r-Supra" in out


def test_quarantine_vacia_tras_el_sunset_de_zxe(monkeypatch):
    # 22-jul (s278): Alberto adjudicó las 4 filas (FAAST, ZXR, G-100-R, INSPIRE) → vacía.
    # s287 P0.5 metió 'zxe' con SUNSET explícito; s287 P1 lo CUMPLE (la causa la gobierna
    # ahora la regla corpus-aware, estructural) → el YAML real vuelve a `tokens: []` y la
    # quarantine recupera su semántica original (SOLO pendientes de adjudicación).
    monkeypatch.setattr(R, "_quarantine", None)      # fuerza re-lectura del YAML real
    assert R._quarantine_tokens() == frozenset()
    # y el drop de las unidades adjudicadas s278 sigue vivo cuando el corpus NO lleva el
    # tag-familia (presencia inyectada = solo-variantes, el estado real de ZXR)
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, {"zxr50a", "zxr50p", "zxr4b", "zxr5b"})
    res = R.resolve_query("manual de ZXR")
    assert "zxr" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}


def test_efecto_corpus_wide_de_la_regla_no_es_solo_zxe(monkeypatch):
    # F3 del spec (declaración honesta): P1 NO es un parche para hp018 — repara la clase
    # completa «token-paraguas con tag-FAMILIA vivo en el corpus». Verificado contra el
    # corpus REAL (661 pm distintos → 731 elementos): 'faast' e 'inspire' TAMBIÉN están como
    # elemento ⇒ en producción esos paraguas pasan de DROP (s278) a CONSERVARSE. Los tests
    # s278 de más arriba pinean el guard/quarantine con presencia inyectada VACÍA, no este
    # efecto; el gate del cambio es el probe de composición de pool, no un unit test.
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, {"faast", "inspire"})
    for q, tok in (("manual de FAAST", "faast"),
                   ("manual de la central INSPIRE", "inspire")):
        res = R.resolve_query(q)
        assert tok not in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}, q


# ─── s287 P1: regla monótona-segura corpus-aware (spec v3 FINAL — presencia INYECTADA) ───
def test_pm_elements_exact_tag_por_elemento_no_substring():
    # H3a (suffix-capture): 'cad150' NO es elemento de 'CAD-150-8' — si la presencia fuese
    # substring, el drop quedaría INERTE en cuanto el corpus se parta por variantes (D1).
    assert R._pm_elements("CAD-150-8") == {"cad1508"}
    assert "cad150" not in R._pm_elements("CAD-150-8")
    # H3b (composites reales del corpus): exact-crudo perdería el tag-familia dentro del
    # compuesto; por ELEMENTO sí lo ve. (Sol-2) entra ADEMÁS la forma pm-completa
    # normalizada — es la que un core multi-palabra necesita (ver
    # test_multipalabra_forma_pm_completa_es_presencia); en los composites con '/' es
    # inofensiva (ningún core de token la produce).
    assert R._pm_elements("ZXe/ZXSe") == {"zxe", "zxse", "zxe/zxse"}
    assert R._pm_elements("ZX2e/ZX5e") == {"zx2e", "zx5e", "zx2e/zx5e"}
    assert R._pm_elements("ZXR5B/ZXR4B") == {"zxr5b", "zxr4b", "zxr5b/zxr4b"}
    # separadores: '/', '+', espacio; y la normalización del filtro (quita '-', lowercase)
    assert R._pm_elements("AM2020 y AFP1010") == {"am2020", "y", "afp1010",
                                                  "am2020yafp1010"}
    assert R._pm_elements("MS-1/MS-2/MS-4") == {"ms1", "ms2", "ms4", "ms1/ms2/ms4"}
    assert R._pm_elements(None) == set() and R._pm_elements("  ") == set()


def test_multipalabra_forma_pm_completa_es_presencia(monkeypatch):
    # (Sol-2, review 30-jul) el core de un token multi-palabra ('FAAST LT-200' →
    # 'faastlt200') debe encontrar presencia cuando el corpus lleva el tag EXACTO
    # (backfill s80: pm 'FAAST LT-200'): los elementos PARTIDOS solos {'faast','lt200'}
    # no lo contienen y el drop procedería contra una etiqueta VIVA.
    assert R._pm_elements("FAAST LT-200") == {"faast", "lt200", "faastlt200"}
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, R._pm_elements("FAAST LT-200"))
    res = R.resolve_query("sensibilidad del FAAST LT-200")
    tok = next(t for t in res["detected"] if "faast" in t)
    assert R._series.normalize_model(tok) == "faastlt200"      # el core multi-palabra
    assert R.catalog_store.norm_token(tok) not in {
        R.catalog_store.norm_token(t) for t in res["drop_tokens"]}   # presencia → CONSERVA
    # sin presencia → drop (el estado actual: el corpus no conserva nada)
    _inject_presence(monkeypatch, set())
    res2 = R.resolve_query("sensibilidad del FAAST LT-200")
    assert R.catalog_store.norm_token(tok) in {
        R.catalog_store.norm_token(t) for t in res2["drop_tokens"]}


@pytest.mark.parametrize("estado,presencia,dropea", [
    ("solo-familia", {"zxe"}, False),                       # el tag vivo es el paraguas
    ("solo-variantes", {"zx1e", "zx2e", "zx5e"}, True),      # split D1 hecho → drop limpio
    ("mixto", {"zxe", "zx2e", "zx5e"}, False),               # coexistencia → CONSERVAR
    ("ninguno", set(), True),                                # el corpus no opina → drop
])
def test_los_4_estados_de_presencia(monkeypatch, estado, presencia, dropea):
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, presencia)
    res = R.resolve_query("central ZXe")
    dropped = "zxe" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    assert dropped is dropea, estado
    out = R.apply_to_models(["ZXE"], res)
    assert ("ZXE" in out) is (not dropea), estado


def test_presencia_no_es_substring_zxe_en_zxee(monkeypatch):
    # el legacy 'ZXAE/ZXEE' contiene 'zxe' como SUBSTRING ('zxe' ⊂ 'zxee') pero NO como
    # elemento → NO cuenta como presencia de la familia (si contase, ningún paraguas
    # dropearía nunca y la regla dejaría de ser una regla).
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, R._pm_elements("ZXAE/ZXEE"))
    res = R.resolve_query("central ZXe")
    assert "zxe" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    # y el composite REAL del corpus sí lo conserva
    _inject_presence(monkeypatch, R._pm_elements("ZXe/ZXSe"))
    res2 = R.resolve_query("central ZXe")
    assert "zxe" not in {R.catalog_store.norm_token(t) for t in res2["drop_tokens"]}


def test_fail_open_db_conserva_y_es_igual_a_add(monkeypatch):
    # (i) del spec: dependencia DB nueva ⇒ error/indisponibilidad = CONSERVAR el token.
    # El observable debe ser EL DEL BRAZO ADD (nunca peor que add).
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "add")
    esperado_add = R.apply_to_models(["ZXE"], R.resolve_query("central ZXe"))
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, None)                     # DB no consultable
    res = R.resolve_query("central ZXe")
    assert res["drop_tokens"] == []
    assert R.apply_to_models(["ZXE"], res) == esperado_add


def test_fail_open_db_real_httpx_cae_a_conservar(monkeypatch):
    # el fail-open no es solo del cache: el fetch REAL que revienta (timeout/500/red) debe
    # acabar en presencia=None → conservar. Sin red: httpx.Client explota al construirse.
    import httpx

    class _Boom:
        def __init__(self, *a, **k):
            raise httpx.ConnectError("sin red (test)")

    monkeypatch.setattr(httpx, "Client", _Boom)
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements", _fetch_real)
    monkeypatch.setattr(R, "_corpus_fingerprint", _fingerprint_real)
    monkeypatch.setattr(R, "_presence", None)               # obliga a ir al fetch
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    assert R.corpus_pm_elements() is None
    res = R.resolve_query("central ZXe")
    assert res["drop_tokens"] == [] and "ZXE" in R.apply_to_models(["ZXE"], res)


def test_homonimo_nunca_consulta_el_corpus(monkeypatch):
    # SCOPING (H2): con presencia de 'rp1r' inyectada (el corpus REAL la tiene, vía
    # 'RP1r-Supra'), si la regla alcanzase a los homónimos el drop desaparecería y hp011
    # perdería el prefer MEDIDO. Además NO debe consultarse el corpus para un homónimo.
    llamadas = []
    monkeypatch.setattr(R, "corpus_pm_elements",
                        lambda: llamadas.append(1) or frozenset({"rp1r"}))
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("conectar el RP1r al software de gestión")
    assert "rp1r" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    assert llamadas == [], "el homónimo NO debe consultar la presencia de corpus"
    out = R.apply_to_models(["RP1r"], res)
    assert "RP1r" not in out and "RP1r-Supra" in out


def test_brazo_add_no_consulta_el_corpus(monkeypatch):
    # bajo add el campo drop_tokens es inerte (apply_to_models lo ignora) → no se paga la
    # consulta ni se altera la semántica histórica del campo (artefactos/shadow estables).
    llamadas = []
    monkeypatch.setattr(R, "corpus_pm_elements",
                        lambda: llamadas.append(1) or frozenset())
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "add")
    res = R.resolve_query("central ZXe")
    assert "zxe" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    assert llamadas == []
    assert "ZXE" in R.apply_to_models(["ZXE"], res)         # el brazo add, intacto


def test_presencia_cachea_dentro_del_ttl_y_no_repega(monkeypatch):
    fetches, fps = [], []
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements",
                        lambda: fetches.append(1) or frozenset({"zxe"}))
    monkeypatch.setattr(R, "_corpus_fingerprint", lambda: fps.append(1) or ("1", "t0"))
    monkeypatch.setattr(R, "_presence", None)
    assert R.corpus_pm_elements() == frozenset({"zxe"})
    assert R.corpus_pm_elements() == frozenset({"zxe"})
    # (Sol-4a) el load frío toma el fingerprint ANTES y AL ACABAR el scan (honesto) = 2;
    # la 2ª llamada la absorbe el cache sin tocar la red.
    assert len(fetches) == 1 and len(fps) == 2, "el cache de proceso debe absorber la 2ª"


def test_fingerprint_torn_scan_descarta_y_reintenta_una_vez(monkeypatch):
    # (Sol-4a, review 30-jul) el fingerprint se RE-CHEQUEA al acabar el scan (~3-5s): si el
    # corpus se movió DURANTE, el set torn se DESCARTA y se reintenta 1 vez; si vuelve a
    # moverse → None = fail-open a conservar.
    fetches = []
    fps = iter([("1", "t0"), ("2", "t1"), ("2", "t1")])
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements",
                        lambda: fetches.append(1) or frozenset({"zxe"}))
    monkeypatch.setattr(R, "_corpus_fingerprint", lambda: next(fps))
    monkeypatch.setattr(R, "_presence", None)
    assert R.corpus_pm_elements() == frozenset({"zxe"})     # el reintento valida ("2","t1")
    assert len(fetches) == 2, "el 1er set (torn) debe descartarse y re-escanearse"
    assert R._presence["fp"] == ("2", "t1")
    # inestable TAMBIÉN en el reintento → None (y el cooldown corto gobierna el cache)
    fps2 = iter([("1", "t0"), ("2", "t1"), ("3", "t2"), ("4", "t3")])
    monkeypatch.setattr(R, "_corpus_fingerprint", lambda: next(fps2))
    monkeypatch.setattr(R, "_presence", None)
    assert R.corpus_pm_elements() is None
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("central ZXe")
    assert res["drop_tokens"] == [], "fingerprint inestable ⇒ CONSERVAR (nunca peor que add)"


def test_stampede_frio_un_solo_scan(monkeypatch):
    # (Sol-5, review 30-jul) N queries concurrentes en frío = UN solo scan: el lock
    # serializa y el double-check hace que quien esperó lea el cache recién poblado.
    import threading as _th
    fetches = []
    primera_dentro = _th.Event()

    def _fetch_lento():
        fetches.append(1)
        primera_dentro.set()
        time.sleep(0.15)
        return frozenset({"zxe"})

    monkeypatch.setattr(R, "_fetch_corpus_pm_elements", _fetch_lento)
    monkeypatch.setattr(R, "_corpus_fingerprint", lambda: ("1", "t0"))
    monkeypatch.setattr(R, "_presence", None)
    resultados = []
    t1 = _th.Thread(target=lambda: resultados.append(R.corpus_pm_elements()))
    t2 = _th.Thread(target=lambda: resultados.append(R.corpus_pm_elements()))
    t1.start()
    assert primera_dentro.wait(2.0)          # t2 entra mientras t1 escanea
    t2.start()
    t1.join(5.0)
    t2.join(5.0)
    assert resultados == [frozenset({"zxe"})] * 2
    assert len(fetches) == 1, "el lock anti-stampede debe absorber el scan duplicado"


def test_presencia_se_invalida_por_fingerprint_no_por_catalogo(monkeypatch):
    # F6: la invalidación es por FINGERPRINT DE CORPUS (o TTL) — nunca por catálogo-commit.
    fetches = []
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements",
                        lambda: fetches.append(1) or frozenset({"zxe"}))
    monkeypatch.setattr(R, "_corpus_fingerprint", lambda: ("2", "t1"))
    now = time.monotonic()
    monkeypatch.setattr(R, "_presence", {"elements": frozenset({"viejo"}), "at": now,
                                         "fp": ("1", "t0"),
                                         "fp_at": now - R._PRESENCE_FP_RECHECK_S - 1})
    assert R.corpus_pm_elements() == frozenset({"zxe"})     # fingerprint distinto → recarga
    assert len(fetches) == 1
    src = (Path(R.ROOT) / "src" / "rag" / "catalog_resolver.py").read_text(encoding="utf-8")
    i_cache = src.index("def corpus_pm_elements")
    cuerpo = src[i_cache:src.index("\ndef ", i_cache + 1)]      # solo esa función
    assert "catalog_commit" not in cuerpo, \
        "el cache de presencia NO puede ir keyed por catálogo-commit (F6)"


def test_presencia_paginacion_todo_o_nada(monkeypatch):
    # nunca un set PARCIAL: un truncado inventaría ausencias y dropearía de más → LANZA
    # (y el llamante fail-open a conservar).
    import httpx

    class _R:
        status_code = 200
        def json(self):
            return [{"product_model": "ZXe"}] * R._PRESENCE_PAGE     # nunca converge

    class _Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, headers=None, params=None): return _R()

    monkeypatch.setattr(httpx, "Client", _Client)
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements", _fetch_real)
    monkeypatch.setattr(R, "_PRESENCE_MAX_PAGES", 3)
    with pytest.raises(RuntimeError, match="PARCIAL"):
        R._fetch_corpus_pm_elements()


def test_presencia_lee_solo_filas_servibles_y_pagina(monkeypatch):
    # invariante T0 (parent_id is.null: los surrogates no definen identidad) + orden total
    # estable + paginación por offset hasta la página corta. (Sol-3) el scan pre-consulta
    # los documents NO-activos con el criterio EXACTO del retriever.
    import httpx
    vistos_docs, vistos_chunks = [], []

    class _R:
        def __init__(self, rows): self._rows = rows
        status_code = 200
        def json(self): return self._rows

    class _Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, headers=None, params=None):
            if "/documents" in url:
                vistos_docs.append(params)
                return _R([])                            # ningún doc no-activo
            vistos_chunks.append(params)
            if len(vistos_chunks) == 1:
                return _R([{"product_model": "ZXe", "document_id": "d1"}]
                          * R._PRESENCE_PAGE)
            return _R([{"product_model": "ZXAE/ZXEE", "document_id": "d1"},
                       {"product_model": None, "document_id": None}])

    monkeypatch.setattr(httpx, "Client", _Client)
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements", _fetch_real)
    assert R._fetch_corpus_pm_elements() == frozenset(
        {"zxe", "zxae", "zxee", "zxae/zxee"})
    assert [p["offset"] for p in vistos_chunks] == ["0", str(R._PRESENCE_PAGE)]
    assert all(p["parent_id"] == "is.null" for p in vistos_chunks)
    assert all(p["order"] == "product_model.asc,id.asc" for p in vistos_chunks)
    assert all(p["select"] == "product_model,document_id" for p in vistos_chunks)
    # espejo del predicado del retriever: NOT(status='active'), NULL incluido
    assert vistos_docs and all(p["or"] == "(status.neq.active,status.is.null)"
                               for p in vistos_docs)


def test_presencia_excluye_tags_de_docs_no_activos(monkeypatch):
    # (Sol-3, review 30-jul) un tag vivo SOLO en un doc retirado NO es presencia: el
    # retriever jamás serviría esos chunks (_filter_by_document_status dropea
    # status != 'active') → el drop del paraguas SIGUE. Legacy (document_id NULL) y
    # doc-activo SÍ cuentan, como en el retriever.
    import httpx

    class _R:
        def __init__(self, rows): self._rows = rows
        status_code = 200
        def json(self): return self._rows

    class _Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, headers=None, params=None):
            if "/documents" in url:
                return _R([{"id": "doc-retirado"}])      # el único NO-activo
            return _R([
                {"product_model": "ZXe", "document_id": "doc-retirado"},   # excluido
                {"product_model": "CAD-150-8", "document_id": "doc-activo"},
                {"product_model": "ZXR4B", "document_id": None},           # legacy: cuenta
            ])

    monkeypatch.setattr(httpx, "Client", _Client)
    monkeypatch.setattr(R, "_fetch_corpus_pm_elements", _fetch_real)
    presencia = R._fetch_corpus_pm_elements()
    assert presencia == frozenset({"cad1508", "zxr4b"})      # 'zxe' AUSENTE
    # y con esa presencia el drop de ZXe bajo replace SIGUE (ausente ⇒ el corpus no
    # conserva nada — el estado pre-P1 para esta familia)
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    _inject_presence(monkeypatch, presencia)
    res = R.resolve_query("central ZXe")
    assert "zxe" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}


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
    # s285: se excluyen de la muestra los canonicals con caracteres FUERA de la
    # clase de separadores del detector ("(", ")", "*") — 5 fichas en todo el
    # catalogo (3 pre-existentes + 2 wildcard W*A/W*L compensados por sus SKU
    # concretas). Latente destapado por corrimiento de zancada [::40] tras el
    # merge s285 (ficha byte-identica antes/despues). Raiz -> TECH_DEBT #56.
    import json
    rows = [json.loads(l) for l in
            (Path(R.ROOT) / "data" / "catalog" / "products.jsonl").open(encoding="utf-8")]
    consum = [r for r in rows if r.get("estado") == "activo" and not r.get("candidate") and not re.search(r"[()*]", r.get("canonical_model") or "")][::40]
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


INSPIRE_FIRMWARE_DOC = "Actualizacion del firmware de INSPIRE a R1.35"


def test_inspire_dropea_bajo_replace_adjudicada(monkeypatch):
    # s278 adjudicado (Alberto 22-jul): la fila INSPIRE salió de la quarantine — con la
    # config REAL (vacía) el guard GUARD-IMPL gobierna: miembros consumibles ⇒ drop bajo
    # replace, y el doc de cat017 sigue en allowed_sources.
    # s287 P1: presencia inyectada VACÍA (fixture) — en el corpus REAL 'inspire' ES elemento
    # vivo y la puerta 4 lo conserva (test_efecto_corpus_wide_de_la_regla_no_es_solo_zxe).
    R._ensure()
    assert R._cat.resolve("INSPIRE")["all_members_consumable"] is True
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de la central INSPIRE")
    assert "inspire" in {R.catalog_store.norm_token(t) for t in res["drop_tokens"]}
    out = R.apply_to_models(["INSPIRE"], res)
    assert "INSPIRE" not in out and {"INSPIRE E10", "INSPIRE E15"} <= set(out)
    assert CAT017_SOURCE in res["allowed_sources"]


def test_inspire_firmware_doc_alcanzable_via_e10_e15(monkeypatch):
    # s278 adjudicado (Alberto 22-jul): el doc de firmware recibe entries secondary/doc
    # para e10 y e15 — alcanzable bajo replace SIN fila de quarantine (era el doc que la
    # fila protegía); notifier:inspire (candidate) queda como está (duplicado sin efecto).
    R._ensure()
    for pid in ("notifier:inspire-e10", "notifier:inspire-e15"):
        assert INSPIRE_FIRMWARE_DOC in R._docs_by_id.get(pid, frozenset()), pid
    monkeypatch.setenv("IDENTITY_RESOLVE_POLICY", "replace")
    res = R.resolve_query("manual de la central INSPIRE")
    docs_miembros = (R._docs_by_id.get("notifier:inspire-e10", frozenset())
                     | R._docs_by_id.get("notifier:inspire-e15", frozenset()))
    assert docs_miembros and docs_miembros <= res["allowed_sources"]
    assert INSPIRE_FIRMWARE_DOC in res["allowed_sources"]
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
