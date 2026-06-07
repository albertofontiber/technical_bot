"""Tests del esquema del ruler (scripts/gold_store.py) — añadidos en s49 (Track B backbone).

Cubre lo NUEVO: campos `split` (embargo dev/held-out) y `estrato` (multi-tag controlado), la
validación tiered de ambos, y el EMBARGO en la puerta (`verified()` excluye held-out por
defecto — bite crítico del dúo s49, DEC-023). No existía test de gold_store antes
(test_validator.py es del validador anti-alucinación, no del ruler).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store as gs  # noqa: E402


def _base(**kw) -> dict:
    g = {
        "qid": "t1", "question": "q", "conducta_esperada": "answer", "split": "dev",
        "_provenance": {"estado": "verificado", "localizacion": {"t": 1}},
        "atomic_facts": [{"texto": "t", "tipo": "core", "estado": "presente"}],
    }
    g.update(kw)
    return g


def _errs(g: dict) -> list:
    return [i for i in gs.validate_entry(g) if i.severity == "error"]


# --- split -----------------------------------------------------------------
def test_split_valido():
    assert not _errs(_base(split="dev"))
    assert not _errs(_base(split="held-out"))


def test_split_invalido_error():
    assert any("split" in i.msg for i in _errs(_base(split="train")))


def test_verificado_sin_split_error():
    g = _base()
    del g["split"]
    assert any("sin 'split'" in i.msg for i in _errs(g))


def test_no_verificado_sin_split_tolerado():
    g = _base(_provenance={"estado": "pendiente"})
    del g["split"]
    assert not any("split" in i.msg for i in _errs(g))


def test_split_default_dev():
    assert gs._split({}) == "dev"
    assert gs._split({"split": "held-out"}) == "held-out"


# --- estrato ---------------------------------------------------------------
def test_estrato_valido():
    assert not _errs(_base(estrato=["multi-doc", "es-en"]))


def test_estrato_vacio_permitido():
    assert not _errs(_base(estrato=[]))


def test_estrato_ausente_permitido():
    g = _base()
    assert "estrato" not in g
    assert not _errs(g)


def test_estrato_tag_desconocido_error():
    # typo: "multidoc" no está en el vocabulario controlado.
    assert any("estrato" in i.msg for i in _errs(_base(estrato=["multidoc"])))


def test_estrato_no_lista_error():
    assert any("lista" in i.msg for i in _errs(_base(estrato="multi-doc")))


def test_control_pass_no_es_estrato():
    # control-pass se sacó del vocabulario (bite del dúo: estado histórico, no contenido).
    assert "control-pass" not in gs.ESTRATOS
    assert any("estrato" in i.msg for i in _errs(_base(estrato=["control-pass"])))


# --- embargo del held-out (en la PUERTA) -----------------------------------
def _tmp(tmp_path, golds) -> Path:
    p = tmp_path / "g.yaml"
    gs.write(golds, p)
    return p


def test_verified_excluye_heldout_por_defecto(tmp_path):
    p = _tmp(tmp_path, [_base(qid="d1", split="dev"), _base(qid="h1", split="held-out")])
    assert {g["qid"] for g in gs.verified(p)} == {"d1"}


def test_verified_include_heldout_los_incluye(tmp_path):
    p = _tmp(tmp_path, [_base(qid="d1", split="dev"), _base(qid="h1", split="held-out")])
    assert {g["qid"] for g in gs.verified(p, include_heldout=True)} == {"d1", "h1"}


def test_dev_y_heldout_helpers(tmp_path):
    p = _tmp(tmp_path, [_base(qid="d1", split="dev"), _base(qid="h1", split="held-out")])
    assert {g["qid"] for g in gs.dev(p)} == {"d1"}
    assert {g["qid"] for g in gs.heldout(p)} == {"h1"}


# --- invariante del pipeline de autoría (rebanada vertical s49) -------------
def test_upsert_preserva_split_estrato(tmp_path):
    # author_atomic_facts hace get()→muta-un-campo→upsert. Re-autorar NO debe borrar
    # split/estrato. Esto es lo que la rebanada vertical s49 valida del pipeline (DEC-023).
    p = _tmp(tmp_path, [_base(qid="g1", split="held-out", estrato=["multi-doc"])])
    g = gs.get("g1", p)
    g["gold_answer"] = "reescrito"  # simula re-autoría de un campo
    gs.upsert(g, p)
    out = gs.get("g1", p)
    assert out["split"] == "held-out"
    assert out["estrato"] == ["multi-doc"]
    assert out["gold_answer"] == "reescrito"


# --- guarda de regresión sobre el archivo REAL -----------------------------
def test_archivo_real_valida_limpio():
    errs = [i for i in gs.validate() if i.severity == "error"]
    assert not errs, "errores en gold_answers_v1.yaml:\n" + "\n".join(map(str, errs))
