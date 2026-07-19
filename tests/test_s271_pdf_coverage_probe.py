"""S271 — probe de cobertura de PDFs: matching por nombre + BIND por sha256.

Contrato verificado aquí (sin red: funciones puras + ficheros temporales):
    * normalización de nombres (con/sin .pdf, separadores, variante laxa);
    * agregación por documento con los filtros de consumo del bridge S190;
    * localización: sha-verificado > name-only-mismatch > not_found;
    * extraction_sha256 ambiguo (>1 por doc) se declara, no se adivina;
    * --hash-all caza PDFs renombrados por sha.
"""

import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "s271_pdf_coverage_probe", ROOT / "scripts" / "s271_pdf_coverage_probe.py"
)
probe = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("s271_pdf_coverage_probe", probe)
_spec.loader.exec_module(probe)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Normalización de nombres
# ---------------------------------------------------------------------------

def test_normalize_name_variantes():
    assert probe.normalize_name("Manual CAD-150.pdf") == probe.normalize_name(
        "manual_cad-150"
    )
    assert probe.normalize_name("A  B__C.PDF") == "a_b_c"
    # La laxa ignora todo separador (caza renombrados con guiones/espacios).
    assert probe.loose_name("HLSI-MI-580I.pdf") == probe.loose_name("HLSI MI 580I")


# ---------------------------------------------------------------------------
# Agregación por documento
# ---------------------------------------------------------------------------

def _chunk(doc, page, source="man_a.pdf", sha="e" * 64, manufacturer="Detnov"):
    return {
        "document_id": doc,
        "page_number": page,
        "source_file": source,
        "manufacturer": manufacturer,
        "extraction_sha256": sha,
    }


def test_build_documents_paginas_cubiertas_y_sin_asset():
    chunks = [
        _chunk("d1", 1),
        _chunk("d1", 1),  # otro chunk de la misma página: no duplica
        _chunk("d1", 2),
        _chunk("d1", 3),
        _chunk("d2", 5, source="man_b.pdf", sha="f" * 64),
        # filas inválidas (filtros de consumo del bridge): fuera
        _chunk("", 9),
        _chunk("d3", None),
        _chunk("d4", 4, source=""),
    ]
    assets = [{"document_id": "d1", "page_index": 2}]
    documents, totals = probe.build_documents(chunks, assets)
    assert totals == {
        "document_pages": 4,
        "pages_with_asset": 1,
        "pages_without_asset": 3,
    }
    d1 = next(d for d in documents if d["document_id"] == "d1")
    assert d1["uncovered_pages"] == [1, 3]
    assert d1["extraction_sha256"] == "e" * 64


def test_build_documents_extraction_ambigua_queda_sin_sha():
    chunks = [_chunk("d1", 1, sha="a" * 64), _chunk("d1", 2, sha="b" * 64)]
    documents, _ = probe.build_documents(chunks, [])
    assert documents[0]["extraction_sha256"] is None
    assert documents[0]["extraction_sha256_distinct"] == 2


# ---------------------------------------------------------------------------
# Localización con BIND sha256
# ---------------------------------------------------------------------------

def _doc(source_file, sha, uncovered=(1,)):
    return {
        "document_id": "d1",
        "source_file": source_file,
        "manufacturer": "Detnov",
        "extraction_sha256": sha,
        "pages_uncovered": len(uncovered),
        "uncovered_pages": list(uncovered),
    }


def test_locate_sha_verificado_gana_a_candidato_con_otro_sha(tmp_path):
    good = tmp_path / "Manual X.pdf"
    good.write_bytes(b"BINARIO-BUENO")
    doc = _doc("manual_x.pdf", _sha(b"BINARIO-BUENO"))
    cache = probe.HashCache(tmp_path / "cache.json")
    probe.locate_documents([doc], [good], cache, hash_all=False)
    assert doc["status"] == "located_sha_verified"
    assert doc["pdf_path"] == str(good)


def test_locate_name_only_cuando_el_sha_no_cuadra(tmp_path):
    other = tmp_path / "manual_x.pdf"
    other.write_bytes(b"OTRA-REVISION")
    doc = _doc("Manual X.pdf", _sha(b"BINARIO-BUENO"))
    cache = probe.HashCache(tmp_path / "cache.json")
    probe.locate_documents([doc], [other], cache, hash_all=False)
    assert doc["status"] == "name_only_sha_mismatch"
    assert doc["candidates"][0]["sha256"] == _sha(b"OTRA-REVISION")


def test_locate_hash_all_caza_renombrados_y_not_found(tmp_path):
    renamed = tmp_path / "nombre_totalmente_distinto.pdf"
    renamed.write_bytes(b"BINARIO-BUENO")
    found = _doc("Manual X.pdf", _sha(b"BINARIO-BUENO"))
    missing = _doc("Manual Y.pdf", _sha(b"NO-EXISTE"))
    cache = probe.HashCache(tmp_path / "cache.json")
    probe.locate_documents([found, missing], [renamed], cache, hash_all=True)
    assert found["status"] == "located_sha_verified"
    assert found["pdf_path"] == str(renamed)
    assert missing["status"] == "not_found"


def test_locate_extraction_ambigua_se_declara(tmp_path):
    doc = _doc("Manual X.pdf", None)
    probe.locate_documents([doc], [], probe.HashCache(tmp_path / "c.json"), False)
    assert doc["status"] == "ambiguous_extraction"


def test_hash_cache_reutiliza_por_size_y_mtime(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"DATA")
    cache = probe.HashCache(tmp_path / "cache.json")
    first = cache.sha256(pdf)
    cache.save()
    reloaded = probe.HashCache(tmp_path / "cache.json")
    assert reloaded.sha256(pdf) == first == _sha(b"DATA")
    assert reloaded.dirty is False  # vino del cache, no re-hasheó
