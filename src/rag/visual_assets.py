"""Registro de activos visuales por revisión documental (S269, contrato S190).

Lectura GET-only de la tabla ``document_visual_assets`` (migración 014) para
adjuntar a la respuesta los renders de página clasificados como
``technical_utility='useful'`` cuya página pertenece a un fragmento CITADO como
evidencia. Todo el módulo vive detrás del flag ``VISUAL_ASSETS_REGISTRY``
(default off, patrón ``_strict_on_off``): con el flag off el generador no toca
este módulo y no hay ni una llamada extra.

Contrato de servicio (evals/s190_visual_asset_contract_design_v1.md; cap
ampliado 2→4 en S271 por decisión de Alberto):
    * SOLO ``useful`` se sirve. ``uncertain`` (default de carga) y
      ``not_useful`` JAMÁS — el filtro va en la query REST y se re-verifica
      en cliente (cinturón y tirantes).
    * Máximo ``MAX_ASSETS_PER_ANSWER`` (4) activos por respuesta, con orden de
      relevancia PRE-DECLARADO (S271): páginas de los fragmentos MÁS citados
      primero (nº de refs ``[F<n>]`` por página); empate → orden de primera
      cita en la respuesta.
    * Solo páginas de fragmentos citados en la respuesta (mecanismo existente
      de citas: refs ``[F<n>]`` del planner o la línea obligatoria
      "Fuentes: <manual>" del SYSTEM_PROMPT).
    * Falla abierta: cualquier excepción → respuesta de texto intacta, sin
      diagramas, warning en log.
"""

from __future__ import annotations

import logging
import re

import httpx

from ..config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger(__name__)

VISUAL_ASSETS_TABLE = "document_visual_assets"
MAX_ASSETS_PER_ANSWER = 4
_LOOKUP_TIMEOUT_S = 3.0
# Regla de vocabulario del contrato S190 (§visual_role, gate v4): solo los
# roles TÉCNICOS se sirven. cover/marketing/product_photo/other jamás llegan
# al técnico aunque estén etiquetados useful.
SERVABLE_VISUAL_ROLES = ("wiring", "table", "procedure", "ui")


def _is_servable(row: dict) -> bool:
    return (
        row.get("technical_utility") == "useful"
        and row.get("visual_role") in SERVABLE_VISUAL_ROLES
    )

# Refs de fragmento del mecanismo de citas del planner ("... [F3]").
_FRAGMENT_REF = re.compile(r"\[F(\d+)\]")


def lookup_visual_assets(document_id: str, page_number: int) -> list[dict]:
    """Activos ``useful`` de una página documental exacta, vía REST GET.

    Devuelve las filas de ``document_visual_assets`` para
    ``(document_id, page_index=page_number)`` con ``technical_utility=useful``
    Y ``visual_role`` técnico-servible, en orden determinista. Lanza la
    excepción HTTP al caller (el caller decide fallar abierto).
    """
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    params = {
        "select": (
            "document_id,page_index,page_label,storage_url,media_type,"
            "asset_scope,visual_role,technical_utility"
        ),
        "document_id": f"eq.{document_id}",
        "page_index": f"eq.{page_number}",
        "technical_utility": "eq.useful",
        "visual_role": f"in.({','.join(SERVABLE_VISUAL_ROLES)})",
        "order": "asset_scope.asc,asset_sha256.asc",
    }
    with httpx.Client(timeout=_LOOKUP_TIMEOUT_S) as client:
        response = client.get(
            f"{SUPABASE_URL}/rest/v1/{VISUAL_ASSETS_TABLE}",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
    rows = response.json()
    # Re-verificación en cliente: 'uncertain'/'not_useful' y los roles no
    # técnicos (cover/marketing/product_photo/other) no se sirven NUNCA,
    # aunque la API (o un mock/misconfig) devolviera otra cosa.
    return [row for row in rows if _is_servable(row)]


def cited_fragments_ranked(
    answer: str, chunks: list[dict]
) -> list[tuple[int, int, int]]:
    """Fragmentos citados con su relevancia: ``(número, citas, primera_pos)``.

    Orden PRE-DECLARADO del cap S271: más citas ``[F<n>]`` primero; empate →
    orden de primera cita en la respuesta (posición del match). Vía primaria:
    refs ``[F<n>]`` (mecanismo de citas del answer-planner). Fallback: la
    línea obligatoria de fuentes del SYSTEM_PROMPT ("Fuentes: manual A
    (rev. 2); manual B") — cada manual citado cuenta como UNA cita y su
    posición es la primera aparición del nombre en la respuesta.
    Sin cita detectable → lista vacía (la falta de adjunto es preferible a un
    adjunto incorrecto).
    """
    occurrences: dict[int, list[int]] = {}
    for match in _FRAGMENT_REF.finditer(answer or ""):
        number = int(match.group(1))
        if 1 <= number <= len(chunks):
            occurrences.setdefault(number, []).append(match.start())
    if occurrences:
        ranked = [
            (number, len(positions), positions[0])
            for number, positions in occurrences.items()
        ]
    else:
        lowered = (answer or "").casefold()
        ranked = []
        for number, chunk in enumerate(chunks, 1):
            source_file = str(chunk.get("source_file") or "")
            manual_name = source_file.rsplit(".pdf", 1)[0].strip()
            if not manual_name:
                continue
            position = lowered.find(manual_name.casefold())
            if position >= 0:
                ranked.append((number, 1, position))
    ranked.sort(key=lambda item: (-item[1], item[2], item[0]))
    return ranked


def cited_fragment_numbers(answer: str, chunks: list[dict]) -> list[int]:
    """Números de fragmento (1-based) citados como evidencia en la respuesta.

    Conjunto de citas de ``cited_fragments_ranked`` en orden numérico (API
    estable para consumidores que no necesitan la relevancia).
    """
    return sorted(number for number, _, _ in cited_fragments_ranked(answer, chunks))


def _cited_pages_by_relevance(
    answer: str, chunks: list[dict]
) -> list[tuple[tuple[str, int], dict]]:
    """Páginas citadas ordenadas por relevancia pre-declarada (S271).

    Agrega las citas por página (varios fragmentos pueden compartir página):
    citas de la página = suma de citas de sus fragmentos; posición = la
    primera cita de cualquiera de ellos. Orden: más citas primero; empate →
    primera cita en la respuesta.
    """
    pages: dict[tuple[str, int], dict] = {}
    for number, citations, first_position in cited_fragments_ranked(answer, chunks):
        chunk = chunks[number - 1]
        document_id = str(chunk.get("document_id") or "")
        page_number = chunk.get("page_number")
        if not document_id or not isinstance(page_number, int):
            continue
        page_key = (document_id, page_number)
        entry = pages.setdefault(
            page_key, {"citations": 0, "first": first_position, "chunk": chunk}
        )
        entry["citations"] += citations
        entry["first"] = min(entry["first"], first_position)
    return sorted(
        pages.items(), key=lambda item: (-item[1]["citations"], item[1]["first"])
    )


def append_cited_visual_assets(result: dict, chunks: list[dict]) -> None:
    """Adjunta (in-place) hasta 4 activos ``useful`` de las páginas citadas.

    Orden de relevancia PRE-DECLARADO (S271): páginas de los fragmentos más
    citados primero; empate → orden de cita en la respuesta. Formato de
    salida = el que ya consume ``telegram_bot.py`` (url/product/
    section/content_type); la leyenda lleva manual + página. Falla abierta:
    cualquier excepción deja ``result`` sin cambios más allá de lo ya añadido
    y emite un warning.
    """
    try:
        answer = str(result.get("answer") or "")
        existing = result.get("diagrams") or []
        existing_urls = {
            diagram.get("url") for diagram in existing if diagram.get("url")
        }
        added: list[dict] = []
        for (document_id, page_number), entry in _cited_pages_by_relevance(
            answer, chunks
        ):
            chunk = entry["chunk"]
            source_file = str(chunk.get("source_file") or "")
            manual_name = (
                source_file.rsplit(".pdf", 1)[0] if source_file else "manual"
            )
            page_label = None
            for asset in lookup_visual_assets(document_id, page_number):
                # Re-verificación final del contrato: solo 'useful' con rol
                # técnico-servible se sirve, aunque el lookup (o un reemplazo
                # suyo) devolviera otra cosa.
                if not _is_servable(asset):
                    continue
                url = asset.get("storage_url")
                if not url or url in existing_urls:
                    continue
                existing_urls.add(url)
                page_label = asset.get("page_label") or str(page_number)
                added.append(
                    {
                        "url": url,
                        # Leyenda del transporte (telegram_bot.py): manual + página.
                        "product": manual_name,
                        "section": f"pág. {page_label}",
                        "content_type": asset.get("visual_role") or "",
                    }
                )
                if len(added) >= MAX_ASSETS_PER_ANSWER:
                    break
            if len(added) >= MAX_ASSETS_PER_ANSWER:
                break
        if added:
            result["diagrams"] = list(existing) + added
    except Exception:
        # Falla abierta: la respuesta de texto es independiente del canal visual.
        logger.warning(
            "VISUAL_ASSETS_REGISTRY: lookup falló — respuesta sin adjuntos",
            exc_info=True,
        )
