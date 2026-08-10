# -*- coding: utf-8 -*-
"""s316 — contratos de los fixes del dúo sobre la fase de derivados (#68).

Nacen de una crítica JUSTA del sub-agente: la ronda de fixes anterior no traía ni un
test, y tres de ellos eran CRÍTICOS que escriben en producción. Aquí se fija lo que se
puede verificar sin claves ni red:

  · `_verificar_biyeccion` caza la fuga `source_file` (chunks de documentos AJENOS que
    entrarían al lote) y NO da falso positivo cuando dos docs del lote comparten nombre;
  · `_source_files_de_doc` devuelve TODOS los source_file del documento (la v1 tomaba
    `limit=1` sin `order`: entrada parcial y no determinista);
  · el dedup del pipeline hyq sigue siendo el ORIGINAL cross-vintage — guarda de
    regresión contra el no-op que el dúo tumbó (DEC-196);
  · los scripts del camino declaran la convención de encoding del repo (sin ella, en
    Windows con salida capturada un print con → ≈ ✅ ❌ aborta el run a media carga);
  · los CLIs exponen los flags nuevos del congelado de selección.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


class _Resp:
    def __init__(self, total=0, filas=None):
        self.headers = {"content-range": f"0-0/{total}"}
        self._filas = filas if filas is not None else []

    def raise_for_status(self):
        return None

    def json(self):
        return self._filas


class _ClientFalso:
    """httpx.Client de mentira: responde por (document_id, source_file) del params."""

    def __init__(self, chunks_por_doc, total_por_sf):
        self.chunks_por_doc = chunks_por_doc      # doc_id -> [source_file, ...]
        self.total_por_sf = total_por_sf          # source_file -> nº corpus-wide
        self.llamadas = 0

    def get(self, url, headers=None, params=None):
        self.llamadas += 1
        params = params or {}
        doc = (params.get("document_id") or "").replace("eq.", "")
        sf = (params.get("source_file") or "").replace("eq.", "")
        if params.get("select") == "source_file":          # _source_files_de_doc
            return _Resp(filas=[{"source_file": s} for s in self.chunks_por_doc[doc]])
        if doc and sf:                                     # recuento dentro del lote
            return _Resp(total=sum(1 for s in self.chunks_por_doc[doc] if s == sf))
        return _Resp(total=self.total_por_sf.get(sf, 0))   # recuento corpus-wide


def test_source_files_de_doc_devuelve_todos_no_el_primero():
    import derive_channels_lote as drv

    cli = _ClientFalso({"d1": ["a.pdf", "a.pdf", "b.pdf"]}, {})
    vistos, total = drv._source_files_de_doc(cli, "d1")
    assert vistos == {"a.pdf", "b.pdf"}, "la v1 se quedaba con UNO solo (limit=1)"
    assert total == 3


def test_biyeccion_limpia_no_reporta_fuga():
    import derive_channels_lote as drv

    # 2 docs del lote comparten 'comun.pdf'; corpus-wide no hay más → NO es fuga
    cli = _ClientFalso({"d1": ["comun.pdf"], "d2": ["comun.pdf", "solo2.pdf"]},
                       {"comun.pdf": 2, "solo2.pdf": 1})
    lote = [{"document_id": "d1", "source_files": ["comun.pdf"], "chunks": 1},
            {"document_id": "d2", "source_files": ["comun.pdf", "solo2.pdf"],
             "chunks": 2}]
    assert drv._verificar_biyeccion(cli, lote) == []


def test_biyeccion_caza_chunks_de_documento_ajeno():
    import derive_channels_lote as drv

    # 'x.pdf' tiene 5 chunks corpus-wide pero solo 2 son del lote → 3 son AJENOS:
    # los generadores, que consultan por source_file, los arrastrarían.
    cli = _ClientFalso({"d1": ["x.pdf", "x.pdf"]}, {"x.pdf": 5})
    lote = [{"document_id": "d1", "source_files": ["x.pdf"], "chunks": 2}]
    fugas = drv._verificar_biyeccion(cli, lote)
    assert len(fugas) == 1
    assert "x.pdf" in fugas[0] and "AJENOS" in fugas[0]


def test_dedup_hyq_sigue_siendo_el_original_cross_vintage():
    """Guarda de regresión (DEC-196): el dedup por documento era un NO-OP porque
    `parse_questions` ya deduplica global por texto; su umbral era código muerto."""
    src = (ROOT / "scripts" / "hyq_lote_pipeline.py").read_text(encoding="utf-8")
    assert "UMBRAL_DEDUP" not in src, "el umbral muerto volvió"
    assert "dup_cross" in src, "se perdió el contador de descarte cross-vintage"
    assert "textos_ajenos" in src, "se perdió el dedup cross-vintage original"


def test_universo_vacio_no_puede_declararse_completo():
    src = (ROOT / "scripts" / "hyq_lote_pipeline.py").read_text(encoding="utf-8")
    assert "bool(universo)" in src, (
        "ok_count debe exigir universo>0: si no, 0 filas cargadas = COMPLETO, y hoy "
        "solo lo impide que embed_questions([]) reviente por accidente")


def test_scripts_del_camino_declaran_encoding_utf8():
    """En Windows con salida capturada, cp1252 no puede con → ≈ ─ ✅ ❌ ⚠."""
    for nombre in ("derive_channels_lote", "hyq_lote_pipeline", "enunciados_pass",
                   "s315_upload_manuales_storage"):
        src = (ROOT / "scripts" / f"{nombre}.py").read_text(encoding="utf-8")
        assert "stdout.reconfigure" in src, f"{nombre} no declara encoding utf-8"


def test_upload_storage_pagina_de_verdad():
    """PostgREST capa a 1000 filas: `limit=10000` devolvía 1.000 de 1.243 y la guarda
    (1.000 >= 10.000 == False) no disparaba → 243 documentos invisibles."""
    src = (ROOT / "scripts" / "s315_upload_manuales_storage.py").read_text(
        encoding="utf-8")
    assert 'headers={"Range"' in src or '"Range":' in src, "no pagina por Range"
    assert "offset += 1000" in src, "no avanza la paginación"


def test_cli_expone_los_flags_del_congelado():
    out = subprocess.run([sys.executable, "scripts/derive_channels_lote.py", "--help"],
                         cwd=str(ROOT), capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[:300]
    for flag in ("--hasta", "--refrescar-seleccion"):
        assert flag in out.stdout, f"falta {flag}"
