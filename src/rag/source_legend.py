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


def _manual_name(chunk: dict) -> str:
    source_file = str(chunk.get("source_file") or "")
    if not source_file:
        return "manual desconocido"
    return source_file.rsplit(".pdf", 1)[0]


def build_source_legend(
    answer: str, chunks: list[dict], *, max_entries: int = MAX_ENTRIES
) -> str:
    """Devuelve el bloque de leyenda, o "" si no hay nada que mapear.

    Orden ASCENDENTE por número de fragmento: el lector busca «F10», no «la más
    citada» — al revés que el adjunto de páginas, que ordena por relevancia.
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
        legend = build_source_legend(answer, chunks)
        if not legend:
            return
        result["answer"] = f"{answer}\n\n---\n{legend}"
    except Exception:
        logger.warning("source legend fail-open: respuesta sin leyenda", exc_info=True)
