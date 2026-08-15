# -*- coding: utf-8 -*-
"""s323 fase B — la resolución de documento distingue los cuatro casos que antes
colapsaban en `None`, y el writer NO puede borrar sin document_id.

Contexto (TECH_DEBT #80/#81, dúo r32): `resolve_document_id` devolvía `None` para
documento nuevo, solo-filas-no-activas, ambigüedad y error de red por igual. El
llamador no podía distinguirlos, así que indexaba: o creaba chunks huérfanos, o los
ligaba a un documento retirado que el retrieval descarta. Y como `index_chunks`
BORRA antes de insertar, seguir adelante destruía además las filas buenas.
"""
import pytest

from src.reingest.index import (EstadoResolucion, index_chunks,
                                resolver_documento, resolve_document_id)


class _SB:
    """Doble de SupabaseHTTP: devuelve filas por (tabla, filtro) y cuenta borrados."""
    def __init__(self, por_filtro=None, excepcion=None):
        self.por_filtro = por_filtro or {}
        self.excepcion = excepcion
        self.borrados = []

    def fetch_rows(self, tabla, select=None, filters=None, limit=None):
        """Respeta status y manufacturer: desde r33 se filtran EN SERVIDOR — un
        doble que los ignore probaría un contrato que ya no existe."""
        if self.excepcion:
            raise self.excepcion
        filtros = dict(filters or {})
        estado = filtros.pop("status", None)
        marca = filtros.pop("manufacturer", None)
        campo = next(iter(filtros), None)
        filas = list(self.por_filtro.get(campo, []))
        if estado == "eq.active":
            filas = [f for f in filas if f.get("status") == "active"]
        if marca:
            filas = [f for f in filas
                     if f.get("manufacturer") in (None, marca.split("eq.")[-1])]
        return filas[:limit or 5]

    def delete_rows(self, tabla, filtros):
        self.borrados.append((tabla, filtros))

    def insert_rows(self, *a, **k):
        return None


def test_una_fila_activa_es_enlazable():
    sb = _SB({"source_pdf_sha256": [{"id": "doc-1", "status": "active"}]})
    r = resolver_documento(sb, "sha", "f.pdf")
    assert r.estado is EstadoResolucion.ACTIVO and r.document_id == "doc-1"
    assert r.enlazable
    assert resolve_document_id(sb, "sha", "f.pdf") == "doc-1"   # compat


def test_solo_filas_no_activas_NO_se_enlaza():
    """La clase que creó #80: enlazar a una fila retirada hace que el retrieval
    DESCARTE esos chunks — peor que no enlazar."""
    sb = _SB({"source_pdf_sha256": [{"id": "doc-viejo", "status": "retired"}]})
    r = resolver_documento(sb, "sha", "f.pdf")
    assert r.estado is EstadoResolucion.SOLO_NO_ACTIVO
    assert r.document_id is None and not r.enlazable
    assert "retired" in r.detalle


def test_ambiguedad_no_se_resuelve_a_ojo():
    sb = _SB({"source_pdf_sha256": [{"id": "a", "status": "active"},
                                    {"id": "b", "status": "active"}]})
    r = resolver_documento(sb, "sha", "f.pdf")
    assert r.estado is EstadoResolucion.AMBIGUO and not r.enlazable


def test_sin_match_es_documento_nuevo_no_error():
    """Distinguirlo importa: el alta previa en `documents` es el camino legítimo
    (scripts/ingest_new.py), no un fallo."""
    r = resolver_documento(_SB(), "sha", "f.pdf")
    assert r.estado is EstadoResolucion.SIN_MATCH


def test_error_de_infraestructura_NO_se_traga():
    """Antes un timeout se veía igual que 'no hay match' y el pipeline indexaba
    huérfanos creyendo que el documento no existía."""
    r = resolver_documento(_SB(excepcion=RuntimeError("timeout")), "sha", "f.pdf")
    assert r.estado is EstadoResolucion.ERROR and "timeout" in r.detalle


def test_el_hash_manda_sobre_el_nombre():
    sb = _SB({"source_pdf_sha256": [{"id": "por-hash", "status": "active"}],
              "source_pdf_filename": [{"id": "por-nombre", "status": "active"}]})
    assert resolver_documento(sb, "sha", "f.pdf").document_id == "por-hash"


def test_el_writer_NO_borra_sin_document_id():
    """La guarda vive en el writer, no solo en el llamador: index_chunks BORRA
    antes de insertar, así que un fallo aquí destruye las filas buenas."""
    sb = _SB()
    with pytest.raises(ValueError, match="document_id obligatorio"):
        index_chunks([object()], extraction_sha256="sha", document_id=None,
                     supabase=sb)
    assert sb.borrados == []           # lo que importa: NO llegó a borrar


def test_sin_chunks_TAMBIEN_exige_document_id():
    """RE-CONTRATO (dúo r33, Sol): la excepción para `chunks=[]` era insegura —
    el DELETE se ejecutaba igual, así que un vacío accidental de otro llamador
    borraba filas buenas sin que nadie hubiera resuelto la identidad."""
    sb = _SB()
    with pytest.raises(ValueError, match="document_id obligatorio"):
        index_chunks([], extraction_sha256="sha", document_id=None, supabase=sb)
    assert sb.borrados == []


def test_el_nombre_NO_se_usa_sin_marca():
    """(r33, crítico) El nombre es un fallback peligroso: un PDF re-exportado
    cambia de hash y los nombres de manual se repiten entre fabricantes. Sin
    marca conocida no se consulta por nombre."""
    sb = _SB({"source_pdf_filename": [{"id": "otra-marca", "status": "active"}]})
    assert resolver_documento(sb, "sha", "manual.pdf").estado is EstadoResolucion.SIN_MATCH
    con_marca = resolver_documento(sb, "sha", "manual.pdf", manufacturer="Detnov")
    assert con_marca.document_id == "otra-marca"


def test_segunda_activa_no_queda_oculta():
    """(r33, crítico) Antes el `status` se filtraba en CLIENTE sobre un `limit`:
    una segunda fila activa podía quedar fuera de la ventana y devolver ACTIVO
    donde había AMBIGUO."""
    sb = _SB({"source_pdf_sha256": [{"id": "a", "status": "active"},
                                    {"id": "b", "status": "active"},
                                    {"id": "c", "status": "retired"}]})
    assert resolver_documento(sb, "sha", "f.pdf").estado is EstadoResolucion.AMBIGUO
