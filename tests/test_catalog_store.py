"""Tests de catalog_store (la puerta del catálogo canónico — contrato F0/DEC-079).

Cubre las reglas DURAS del contrato: namespace/unicidad/inmutabilidad-por-redirect,
refs sin huérfanos, redirects acíclicos, candidate-gating por blast-radius, y la
cascada de resolución con check-homónimo PRIMERO (la clase hp011: un token homónimo
JAMÁS cae a exact-match aunque coincida con un canonical_model).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import catalog_store as cs  # noqa: E402


def _write(dirp: Path, name: str, rows: list[dict]) -> None:
    (dirp / cs.FILES[name]).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8")


@pytest.fixture()
def cat_dir(tmp_path: Path) -> Path:
    """Catálogo mínimo VÁLIDO estilo slice-Morley (incl. el homónimo RP1r y el paraguas ZXe)."""
    d = tmp_path / "catalog"
    d.mkdir()
    _write(d, "products", [
        {"id": "morley:zx2e", "canonical_model": "ZX2e", "vendido_bajo": ["Morley-IAS"],
         "estado": "activo", "provenance": "s83", "added_by": "test"},
        {"id": "morley:zx5e", "canonical_model": "ZX5e", "vendido_bajo": ["Morley-IAS"],
         "estado": "activo", "provenance": "s83", "added_by": "test"},
        {"id": "notifier:rp1r-supra", "canonical_model": "RP1r-Supra",
         "vendido_bajo": ["Notifier"], "estado": "activo", "provenance": "s78-gt", "added_by": "test"},
        {"id": "morley:rp1r-ext", "canonical_model": "RP1r",
         "vendido_bajo": ["Morley-IAS"], "estado": "activo", "provenance": "s86-gt", "added_by": "test"},
        # redirect: id viejo que se fusionó (merge) en zx2e
        {"id": "morley:zx-2e-old", "canonical_model": "ZX-2E (legacy)", "vendido_bajo": ["Morley-IAS"],
         "estado": "redirect", "redirect_to": "morley:zx2e", "provenance": "merge-test", "added_by": "test"},
        # producto candidate: NO debe indexarse para exact
        {"id": "morley:maybe-x", "canonical_model": "MAYBE-X", "vendido_bajo": ["Morley-IAS"],
         "estado": "activo", "candidate": True, "provenance": "s83", "added_by": "test"},
    ])
    _write(d, "aliases", [
        {"alias": "ZX-2e panel", "id": "morley:zx2e", "tipo": "nombre-largo",
         "provenance": "s83", "added_by": "test"},
    ])
    _write(d, "umbrellas", [
        {"termino": "ZXe", "ids": ["morley:zx2e", "morley:zx5e"], "tipo": "serie",
         "divergent": True, "candidate": False, "provenance": "gt-s78", "added_by": "test"},
        {"termino": "ZXSe", "ids": ["morley:zx2e"], "tipo": "serie",
         "divergent": "unknown", "candidate": True, "provenance": "s83", "added_by": "test"},
    ])
    _write(d, "homonyms", [
        {"termino": "RP1r", "ids": ["notifier:rp1r-supra", "morley:rp1r-ext"],
         "politica": "prefer:notifier:rp1r-supra", "candidate": False,
         "provenance": "gt-s86-hp011", "added_by": "test"},
    ])
    _write(d, "relations", [
        {"origen": "notifier:rp1r-supra", "destino": "morley:rp1r-ext",
         "tipo": "rebrand-of", "provenance": "gt-s78"},
    ])
    _write(d, "doc_map", [
        {"document_id": "doc-123", "source_file": "MIE-MI-530", "entries": [
            {"id": "morley:zx2e", "role": "primary", "scope": "doc", "provenance": "s83"}]},
    ])
    _write(d, "docrel", [])
    return d


# ───────────────────────────── validate ─────────────────────────────
def test_valid_catalog_passes(cat_dir):
    assert cs.validate(cat_dir) == []


def test_id_sin_namespace_falla(cat_dir):
    rows = [json.loads(l) for l in (cat_dir / "products.jsonl").read_text(encoding="utf-8").splitlines()]
    rows.append({"id": "sin-namespace", "canonical_model": "X", "vendido_bajo": ["m"],
                 "estado": "activo", "provenance": "t", "added_by": "t"})
    _write(cat_dir, "products", rows)
    assert any("namespace" in e for e in cs.validate(cat_dir))


def test_id_duplicado_falla(cat_dir):
    rows = [json.loads(l) for l in (cat_dir / "products.jsonl").read_text(encoding="utf-8").splitlines()]
    rows.append(dict(rows[0]))
    _write(cat_dir, "products", rows)
    assert any("DUPLICADO" in e for e in cs.validate(cat_dir))


def test_redirect_ciclo_falla(cat_dir):
    rows = [json.loads(l) for l in (cat_dir / "products.jsonl").read_text(encoding="utf-8").splitlines()]
    rows += [
        {"id": "m:a", "canonical_model": "A", "vendido_bajo": ["m"], "estado": "redirect",
         "redirect_to": "m:b", "provenance": "t", "added_by": "t"},
        {"id": "m:b", "canonical_model": "B", "vendido_bajo": ["m"], "estado": "redirect",
         "redirect_to": "m:a", "provenance": "t", "added_by": "t"},
    ]
    _write(cat_dir, "products", rows)
    assert any("CICLO" in e for e in cs.validate(cat_dir))


def test_alias_huerfano_falla(cat_dir):
    _write(cat_dir, "aliases", [{"alias": "X9", "id": "morley:no-existe",
                                 "tipo": "codigo-comercial", "provenance": "t", "added_by": "t"}])
    assert any("inexistente" in e for e in cs.validate(cat_dir))


def test_umbrella_sin_candidate_falla(cat_dir):
    _write(cat_dir, "umbrellas", [{"termino": "Z", "ids": ["morley:zx2e"], "tipo": "serie",
                                   "divergent": True, "provenance": "t", "added_by": "t"}])
    assert any("candidate obligatorio" in e for e in cs.validate(cat_dir))


def test_homonimo_un_solo_id_falla(cat_dir):
    _write(cat_dir, "homonyms", [{"termino": "Q", "ids": ["morley:zx2e"], "politica": "clarify",
                                  "candidate": False, "provenance": "t", "added_by": "t"}])
    assert any("≥2 ids" in e or ">=2" in e for e in cs.validate(cat_dir))


def test_provenance_obligatorio(cat_dir):
    rows = [json.loads(l) for l in (cat_dir / "products.jsonl").read_text(encoding="utf-8").splitlines()]
    rows.append({"id": "m:c", "canonical_model": "C", "vendido_bajo": ["m"], "estado": "activo"})
    _write(cat_dir, "products", rows)
    assert any("provenance" in e for e in cs.validate(cat_dir))


def test_docmap_paginas_sin_lista_falla(cat_dir):
    _write(cat_dir, "doc_map", [{"document_id": "d1", "source_file": "f", "entries": [
        {"id": "morley:zx2e", "role": "primary", "scope": "paginas", "provenance": "t"}]}])
    assert any("scope=paginas" in e for e in cs.validate(cat_dir))


# ───────────────────────────── resolve ─────────────────────────────
def test_resolve_exact(cat_dir):
    cat = cs.load(cat_dir)
    r = cat.resolve("ZX2e")
    assert r == {"ids": ["morley:zx2e"], "via": "exact", "expand": True}


def test_resolve_normalizacion_tipografica(cat_dir):
    cat = cs.load(cat_dir)
    assert cat.resolve("zx-2E")["ids"] == ["morley:zx2e"]     # guiones/mayúsculas
    assert cat.resolve("ZX 2e")["ids"] == ["morley:zx2e"]     # espacios


def test_resolve_alias(cat_dir):
    cat = cs.load(cat_dir)
    r = cat.resolve("ZX-2e panel")
    assert r["via"] == "alias" and r["ids"] == ["morley:zx2e"]


def test_resolve_paraguas_expande_con_divergent(cat_dir):
    cat = cs.load(cat_dir)
    r = cat.resolve("ZXe")
    assert r["via"] == "paraguas"
    assert set(r["ids"]) == {"morley:zx2e", "morley:zx5e"}
    assert r["divergent"] is True


def test_resolve_homonimo_prefer_gana_a_exact(cat_dir):
    """La clase hp011: 'RP1r' coincide con canonical_model del producto extinción,
    pero el check-homónimo va PRIMERO → resuelve por política prefer al Supra."""
    cat = cs.load(cat_dir)
    r = cat.resolve("RP1r")
    assert r["via"] == "homonimo"
    assert r["ids"] == ["notifier:rp1r-supra"]


def test_resolve_umbrella_candidate_no_se_consume(cat_dir):
    cat = cs.load(cat_dir)
    assert cat.resolve("ZXSe") is None     # candidate → fail-open (como si no existiera)


def test_resolve_product_candidate_no_exact(cat_dir):
    cat = cs.load(cat_dir)
    assert cat.resolve("MAYBE-X") is None


def test_resolve_homonimo_candidate_bloquea_exact(cat_dir):
    """Un homónimo AUNQUE candidate bloquea el exact del token (mejor fail-open que
    resolver mal); su política no aplica hasta QA."""
    rows = [{"termino": "ZX2e", "ids": ["morley:zx2e", "morley:zx5e"], "politica": "clarify",
             "candidate": True, "provenance": "t", "added_by": "t"},
            {"termino": "RP1r", "ids": ["notifier:rp1r-supra", "morley:rp1r-ext"],
             "politica": "prefer:notifier:rp1r-supra", "candidate": False,
             "provenance": "gt", "added_by": "t"}]
    _write(cat_dir, "homonyms", rows)
    cat = cs.load(cat_dir)
    r = cat.resolve("ZX2e")
    assert r["via"] == "homonimo-candidate" and r["ids"] == []


def test_resolve_redirect_sigue_al_superviviente(cat_dir):
    cat = cs.load(cat_dir)
    r = cat.resolve("ZX-2E (legacy)")
    # el canonical del redirect NO se indexa como activo... el redirect no es 'activo'
    # → exact no lo encuentra; pero un alias/umbrella que apunte al id viejo resuelve al nuevo.
    assert r is None or r["ids"] == ["morley:zx2e"]
    assert cat.follow_redirect("morley:zx-2e-old") == "morley:zx2e"


def test_resolve_fail_open(cat_dir):
    cat = cs.load(cat_dir)
    assert cat.resolve("PRODUCTO-INEXISTENTE-999") is None


def test_alias_colision_con_canonical_de_otro_producto_falla(cat_dir):
    """La clase ZXr-A (cazada por el smoke F1a): un alias cuyo token normalizado coincide
    con el canonical de OTRO producto → exact pisaría el alias → la puerta lo rechaza."""
    rows = [json.loads(l) for l in (cat_dir / "products.jsonl").read_text(encoding="utf-8").splitlines()]
    rows.append({"id": "morley:zxr-a", "canonical_model": "ZXr-A", "vendido_bajo": ["m"],
                 "estado": "activo", "provenance": "t", "added_by": "t"})
    _write(cat_dir, "products", rows)
    _write(cat_dir, "aliases", [{"alias": "ZXr-A", "id": "morley:zx2e",
                                 "tipo": "variante-tipografica", "provenance": "t", "added_by": "t"}])
    assert any("COLISIONA" in e for e in cs.validate(cat_dir))


def test_resolve_expand_contract(cat_dir):
    """El contrato `expand` para el consumidor (fix dúo s90): clarify y unknown NO expanden."""
    cat = cs.load(cat_dir)
    assert cat.resolve("ZX2e")["expand"] is True            # exact
    assert cat.resolve("ZX-2e panel")["expand"] is True     # alias
    assert cat.resolve("ZXe")["expand"] is True             # paraguas divergent=True (retrieval expande)
    assert cat.resolve("RP1r")["expand"] is True            # homónimo prefer (1 id)
    # homónimo clarify: ids = OPCIONES del clarify, expand=False (no contaminar pool)
    rows = [{"termino": "RP1r", "ids": ["notifier:rp1r-supra", "morley:rp1r-ext"],
             "politica": "clarify", "candidate": False, "provenance": "t", "added_by": "t"}]
    _write(cat_dir, "homonyms", rows)
    cat = cs.load(cat_dir)
    r = cat.resolve("RP1r")
    assert r["expand"] is False and len(r["ids"]) == 2


def test_resolve_paraguas_unknown_fail_open(cat_dir):
    """divergent='unknown' NO-candidate → fail-open SIN expansión (letra del contrato §5.1)."""
    rows = [{"termino": "ZXQ", "ids": ["morley:zx2e", "morley:zx5e"], "tipo": "serie",
             "divergent": "unknown", "candidate": False, "provenance": "t", "added_by": "t"}]
    _write(cat_dir, "umbrellas", rows)
    cat = cs.load(cat_dir)
    r = cat.resolve("ZXQ")
    assert r["via"] == "paraguas-unknown" and r["ids"] == [] and r["expand"] is False


def test_write_jsonl_valida_y_aborta(cat_dir):
    """write_jsonl con validate_after (default) aborta si el catálogo queda inválido."""
    import pytest as _pt
    bad = [{"alias": "X", "id": "morley:no-existe", "tipo": "codigo-comercial",
            "provenance": "t", "added_by": "t"}]
    with _pt.raises(ValueError, match="INVÁLIDO"):
        cs.write_jsonl("aliases", bad, catalog_dir=cat_dir)


def test_provenance_obligatorio_en_umbrellas(cat_dir):
    _write(cat_dir, "umbrellas", [{"termino": "Z2", "ids": ["morley:zx2e"], "tipo": "serie",
                                   "divergent": True, "candidate": False}])
    assert any("provenance" in e and "umbrellas" in e for e in cs.validate(cat_dir))
