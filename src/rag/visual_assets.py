"""Registro de activos visuales por revisión documental (S269, contrato S190).

Lectura GET-only de la tabla ``document_visual_assets`` (migración 014) para
adjuntar a la respuesta los renders de página clasificados como
``technical_utility='useful'`` cuya página pertenece a un fragmento CITADO como
evidencia. Todo el módulo vive detrás del flag ``VISUAL_ASSETS_REGISTRY``
(default off, patrón ``_strict_on_off``): con el flag off el generador no toca
este módulo y no hay ni una llamada extra.

Contrato de servicio (evals/s190_visual_asset_contract_design_v1.md):
    * SOLO ``useful`` se sirve. ``uncertain`` (default de carga) y
      ``not_useful`` JAMÁS — el filtro va en la query REST y se re-verifica
      en cliente (cinturón y tirantes).
    * Máximo ``MAX_ASSETS_PER_ANSWER`` (2) activos por respuesta.
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
MAX_ASSETS_PER_ANSWER = 2
_LOOKUP_TIMEOUT_S = 3.0

# Refs de fragmento del mecanismo de citas del planner ("... [F3]").
_FRAGMENT_REF = re.compile(r"\[F(\d+)\]")


def lookup_visual_assets(document_id: str, page_number: int) -> list[dict]:
    """Activos ``useful`` de una página documental exacta, vía REST GET.

    Devuelve las filas de ``document_visual_assets`` para
    ``(document_id, page_index=page_number)`` con ``technical_utility=useful``,
    en orden determinista. Lanza la excepción HTTP al caller (el caller decide
    fallar abierto).
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
    # Re-verificación en cliente: 'uncertain'/'not_useful' no se sirven NUNCA,
    # aunque la API (o un mock/misconfig) devolviera otra cosa.
    return [row for row in rows if row.get("technical_utility") == "useful"]


def cited_fragment_numbers(answer: str, chunks: list[dict]) -> list[int]:
    """Números de fragmento (1-based) citados como evidencia en la respuesta.

    Vía primaria: refs ``[F<n>]`` (mecanismo de citas del answer-planner).
    Fallback: la línea obligatoria de fuentes del SYSTEM_PROMPT ("Fuentes:
    manual A (rev. 2); manual B") — un fragmento se considera citado si el
    nombre de su manual (source_file sin .pdf) aparece en la respuesta.
    Sin cita detectable → lista vacía (la falta de adjunto es preferible a un
    adjunto incorrecto).
    """
    refs = {
        int(match)
        for match in _FRAGMENT_REF.findall(answer or "")
        if 1 <= int(match) <= len(chunks)
    }
    if refs:
        return sorted(refs)

    lowered = (answer or "").casefold()
    cited: list[int] = []
    for number, chunk in enumerate(chunks, 1):
        source_file = str(chunk.get("source_file") or "")
        manual_name = source_file.rsplit(".pdf", 1)[0].strip()
        if manual_name and manual_name.casefold() in lowered:
            cited.append(number)
    return cited


def append_cited_visual_assets(result: dict, chunks: list[dict]) -> None:
    """Adjunta (in-place) hasta 2 activos ``useful`` de las páginas citadas.

    Formato de salida = el que ya consume ``telegram_bot.py`` (url/product/
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
        seen_pages: set[tuple[str, int]] = set()
        for number in cited_fragment_numbers(answer, chunks):
            chunk = chunks[number - 1]
            document_id = str(chunk.get("document_id") or "")
            page_number = chunk.get("page_number")
            if not document_id or not isinstance(page_number, int):
                continue
            page_key = (document_id, page_number)
            if page_key in seen_pages:
                continue
            seen_pages.add(page_key)

            source_file = str(chunk.get("source_file") or "")
            manual_name = (
                source_file.rsplit(".pdf", 1)[0] if source_file else "manual"
            )
            page_label = None
            for asset in lookup_visual_assets(document_id, page_number):
                # Re-verificación final del contrato: solo 'useful' se sirve,
                # aunque el lookup (o un reemplazo suyo) devolviera otra cosa.
                if asset.get("technical_utility") != "useful":
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
