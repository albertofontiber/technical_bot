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

**Links (s315/punto-6, flag `SOURCE_LEGEND_LINKS`)**: cada entrada puede llevar la URL
pública del manual con ancla ``#page=N``. La URL viene del chunk ENRIQUECIDO
(``document_source_url``, estampado por el fetch batched de documents que el retriever
ya hace — hallazgo #1 del dúo s315: cero round-trips nuevos, cero bloqueo del event
loop). Los chunks apendizados por lanes de coverage no pasan por ese fetch y quedan
sin link — gap declarado, no silencioso. `SOURCE_LEGEND_LINKS=on` es NO-OP si
`SOURCE_LEGEND` está off (la leyenda entera lo es).
"""

from __future__ import annotations

import logging
import os

from ..config import _strict_on_off
from .visual_assets import cited_fragments_ranked

logger = logging.getLogger(__name__)

LEGEND_HEADER = "📄 Referencias citadas:"
# Cap declarado: una leyenda de 30 líneas es ruido. Si se recorta, se DICE (regla del
# proyecto: ningún cap silencioso).
MAX_ENTRIES = 12
_URL_MAX_CHARS = 300


def source_legend_enabled() -> bool:
    return os.getenv("SOURCE_LEGEND", "off").strip().lower() == "on"


def source_legend_links_enabled() -> bool:
    """s315/punto-6: URL pública del manual en la leyenda.

    Flag SEPARADO de SOURCE_LEGEND: si la leyenda ya está ON en producción,
    encender links es una decisión aparte y OFF la deja byte-idéntica a hoy.
    Lectura fail-fast (`_strict_on_off`, convención del repo): un valor no
    reconocido revienta ANTES del fail-open de la leyenda, no se traga en
    silencio (hallazgo #9 del dúo s315). Se lee en runtime → flip de Railway
    sin reinicio.
    """
    return _strict_on_off("SOURCE_LEGEND_LINKS", "off")


def _manual_name(chunk: dict) -> str:
    source_file = str(chunk.get("source_file") or "")
    if not source_file:
        return "manual desconocido"
    return source_file.rsplit(".pdf", 1)[0]


def _chunk_url(chunk: dict) -> str | None:
    """URL pública del doc del chunk, validada. None = sin link (línea intacta).

    Único dato de DB que cruza al mensaje del técnico: allowlist de forma
    (esquema http/https, sin saltos de línea, cap de longitud) — hallazgo #11.
    """
    url = chunk.get("document_source_url")
    if not isinstance(url, str):
        return None
    url = url.strip()
    if (
        not url.startswith(("https://", "http://"))
        or "\n" in url
        or " " in url
        or len(url) > _URL_MAX_CHARS
    ):
        return None
    return url


def build_source_legend(
    answer: str,
    chunks: list[dict],
    *,
    max_entries: int = MAX_ENTRIES,
    links: bool = False,
) -> str:
    """Devuelve el bloque de leyenda, o "" si no hay nada que mapear.

    Orden ASCENDENTE por número de fragmento: el lector busca «F10», no «la más
    citada» — al revés que el adjunto de páginas, que ordena por relevancia.

    ``links=True`` añade la URL del manual (``document_source_url`` del chunk)
    con ancla ``#page=N``. Sin URL válida la línea queda EXACTAMENTE como hasta
    ahora — el link es aditivo, nunca condición.
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
        if links:
            url = _chunk_url(chunk)
            if url:
                partes.append(
                    f"{url}#page={pagina}" if isinstance(pagina, int) else url
                )
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

    El flag de links se lee FUERA del try: un valor malconfigurado debe reventar
    ruidosamente (convención `_strict_on_off`), no tragarse la leyenda entera.
    """
    links = source_legend_links_enabled()
    try:
        answer = str(result.get("answer") or "")
        legend = build_source_legend(answer, chunks, links=links)
        if not legend:
            return
        result["answer"] = f"{answer}\n\n---\n{legend}"
    except Exception:
        logger.warning("source legend fail-open: respuesta sin leyenda", exc_info=True)
