"""Leyenda de referencias: convierte las citas ``[F<n>]`` en fuentes comprobables.

**El problema que resuelve** (lo cazó Alberto usando el bot, 2-ago): la respuesta cita
``[F10]`` pero la línea «Fuente:» final solo nombra el manual — la correspondencia
``[F<n>] → manual · sección · página`` **nunca se emite**, aunque el generador SÍ la
tiene (cada fragmento se le sirve con cabecera ``[Fragmento N | … | Manual: … ]``).
El técnico lee ``[F10]`` y no sabe a qué apunta: el dato existe y se tira.

Es presentación determinista y post-generación: **cero llamadas de modelo**, se calcula
de los mismos chunks servidos y del texto FINAL de la respuesta (después de guards y
apéndices, para que una cita borrada por el conflict-guard no aparezca en la leyenda).

Reusa `cited_fragments_ranked` — el MISMO parser de citas que ya alimenta el adjunto de
páginas — para que ambos vean idéntico conjunto de referencias.
"""

from __future__ import annotations

import logging
import os

from .visual_assets import cited_fragments_ranked

logger = logging.getLogger(__name__)

LEGEND_HEADER = "📄 Referencias citadas:"
# Cap declarado: una leyenda de 30 líneas es ruido. Si se recorta, se DICE (regla del
# proyecto: ningún cap silencioso).
MAX_ENTRIES = 12


def source_legend_enabled() -> bool:
    return os.getenv("SOURCE_LEGEND", "off").strip().lower() == "on"


def source_legend_links_enabled() -> bool:
    """s315/punto-6: URL pública del manual en la leyenda (documents.source_url).

    Flag SEPARADO de SOURCE_LEGEND a propósito: si la leyenda ya está ON en
    producción, encender links es una decisión aparte (añade una llamada
    PostgREST por turno) y OFF deja la leyenda byte-idéntica a hoy.
    """
    return os.getenv("SOURCE_LEGEND_LINKS", "off").strip().lower() == "on"


_URL_FETCH_TIMEOUT_S = 3.0


def _document_urls(chunks: list[dict], numeros: list[int]) -> dict[str, str]:
    """``document_id -> source_url`` para los fragmentos citados. Fail-open a {}.

    Una sola llamada PostgREST por turno (solo con el flag ON); un fallo de red
    degrada a leyenda-sin-links, nunca rompe la respuesta.
    """
    doc_ids = sorted({
        str(chunks[n - 1].get("document_id") or "")
        for n in numeros
        if 0 < n <= len(chunks) and chunks[n - 1].get("document_id")
    })
    if not doc_ids:
        return {}
    try:
        import httpx

        from ..config import SUPABASE_SERVICE_KEY, SUPABASE_URL

        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/documents",
            params={
                "id": f"in.({','.join(doc_ids)})",
                "select": "id,source_url",
            },
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            timeout=_URL_FETCH_TIMEOUT_S,
        )
        resp.raise_for_status()
        return {
            str(row.get("id")): str(row.get("source_url"))
            for row in resp.json()
            if isinstance(row, dict) and row.get("source_url")
        }
    except Exception:
        logger.warning("source legend links fail-open: leyenda sin URLs",
                       exc_info=True)
        return {}


def _manual_name(chunk: dict) -> str:
    source_file = str(chunk.get("source_file") or "")
    if not source_file:
        return "manual desconocido"
    return source_file.rsplit(".pdf", 1)[0]


def build_source_legend(
    answer: str,
    chunks: list[dict],
    *,
    max_entries: int = MAX_ENTRIES,
    doc_urls: dict[str, str] | None = None,
) -> str:
    """Devuelve el bloque de leyenda, o "" si no hay nada que mapear.

    Orden ASCENDENTE por número de fragmento: el lector busca «F10», no «la más
    citada» — al revés que el adjunto de páginas, que ordena por relevancia.

    ``doc_urls`` (s315): ``document_id -> URL pública del manual``. Sin él (o sin
    entrada para un doc) la línea queda EXACTAMENTE como hasta ahora — el link es
    aditivo, nunca condición. Con página, ancla ``#page=N`` (visor estándar).
    """
    numeros = sorted(
        {number for number, _citas, _pos in cited_fragments_ranked(answer, chunks)}
    )
    if not numeros:
        return ""

    lineas: list[str] = []
    for number in numeros[:max_entries]:
        chunk = chunks[number - 1]
        partes = [_manual_name(chunk)]
        seccion = str(chunk.get("section_title") or "").strip()
        if seccion:
            partes.append(seccion)
        pagina = chunk.get("page_number")
        if isinstance(pagina, int):
            partes.append(f"p. {pagina}")
        url = (doc_urls or {}).get(str(chunk.get("document_id") or ""))
        if url:
            partes.append(f"{url}#page={pagina}" if isinstance(pagina, int) else url)
        lineas.append(f"[F{number}] " + " · ".join(partes))

    if len(numeros) > max_entries:
        omitidas = len(numeros) - max_entries
        lineas.append(f"(+{omitidas} referencias más, no listadas)")

    return LEGEND_HEADER + "\n" + "\n".join(lineas)


def append_source_legend(result: dict, chunks: list[dict]) -> None:
    """Añade la leyenda al final de ``result['answer']`` (in-place). Fail-open.

    Se llama la ÚLTIMA, después del adjunto de páginas: la leyenda introduce más
    ocurrencias de ``[F<n>]`` y contarlas como citas del técnico falsearía el orden
    de relevancia de las imágenes.
    """
    try:
        answer = str(result.get("answer") or "")
        doc_urls: dict[str, str] | None = None
        if source_legend_links_enabled():
            numeros = sorted({
                number
                for number, _citas, _pos in cited_fragments_ranked(answer, chunks)
            })
            doc_urls = _document_urls(chunks, numeros)
        legend = build_source_legend(answer, chunks, doc_urls=doc_urls)
        if not legend:
            return
        result["answer"] = f"{answer}\n\n---\n{legend}"
    except Exception:
        logger.warning("source legend fail-open: respuesta sin leyenda", exc_info=True)
