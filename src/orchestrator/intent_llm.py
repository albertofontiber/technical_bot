# -*- coding: utf-8 -*-
"""s316g — El clasificador de intención del lever INTENT_LLM (DEC-203, GO adjudicado).

UNA fuente para el prompt y el parser: este módulo lo importan el gate de juicio
(`scripts/s316g_intent_cohort_gate.py`) y el transporte — el prompt que se midió ES el
que sirve. ANTI-GATE-SHOPPING: revisar el prompt = cohorte nueva congelada (DEC-126).

Modelo: `claude-sonnet-4-6` — el único que pasó el gate v1.1 (40/40, 0 falsos SWITCH
tras la adjudicación de Alberto; Haiku NO-GO con un fallo claro en EN). Latencia
declarada: p50 1,3 s / p95 4,4 s en la rama ambigua (~19% de turnos con marca sin
modelo, subset in-window) contra turnos de ~28 s.

El callable cumple el contrato del seam (v2 §4): devuelve SOLO "compat" | "switch" |
None; None = fail-open = la conducta de hoy (carry). JAMÁS lanza. La última decisión
queda en `fn.ultima` para que el transporte la estampe en la traza.
"""
from __future__ import annotations

import time
from typing import Callable

INTENT_MODEL = "claude-sonnet-4-6"

# EL prompt del gate (evals/s316g_intent_cohort_v1.yaml · resultado v1.1: GO).
PROMPT = """Eres el enrutador de un asistente técnico de sistemas contra incendios.
El técnico estaba consultando sobre este producto: {contexto}.
Su siguiente mensaje es: «{q}»

¿El mensaje pregunta por la COMPATIBILIDAD/integración de otra marca CON el producto en
curso (la consulta sigue siendo sobre ese producto), o CAMBIA DE TEMA a la otra marca
(el producto en curso deja de ser el sujeto)?

Responde EXACTAMENTE una palabra: COMPAT o SWITCH."""


def parse_decision(raw: str) -> str | None:
    """Parser ESTRICTO (v2 §4): COMPAT/SWITCH con tolerancia a puntuación final;
    cualquier otra cosa → None. La política trata todo valor fuera del contrato
    como None (defensa en profundidad)."""
    token = (raw or "").strip().rstrip(".!").upper()
    return {"COMPAT": "compat", "SWITCH": "switch"}.get(token)


def contexto_del_estado(working_state) -> str:
    """Inputs del prompt (v2 §4): modelos del estado + marca resuelta si la hay.
    `last_query` NO se manda (minimización)."""
    from ..rag.retriever import classify_model_manufacturer

    modelos = list(getattr(working_state, "last_target_models", ()) or ())
    if not modelos:
        return "desconocido"
    marcas = sorted({m for m in (classify_model_manufacturer(x) for x in modelos) if m})
    etiqueta = ", ".join(modelos)
    return f"{etiqueta} ({', '.join(marcas)})" if marcas else f"{etiqueta} (marca desconocida)"


def construir_intent_fn(api_key: str, model: str = INTENT_MODEL,
                        timeout_s: float = 6.0) -> Callable:
    """El IntentFn del transporte. Síncrono a propósito: el llamador lo mueve a
    `asyncio.to_thread` (el resolve corre en el event loop — Sol r10 M2)."""
    import anthropic

    # max_retries=0 (Fable r11): el default (2) convertia un timeout de 6 s en ~19 s
    # de espera antes del fail-open — una cola que el gate jamas midio. Un intento:
    # o responde a tiempo o fail-open YA (la conducta de hoy es aceptable).
    cliente = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=0)

    def _intent(query: str, working_state) -> str | None:
        t0 = time.perf_counter()
        decision = None
        try:
            msg = cliente.messages.create(
                model=model, max_tokens=4, temperature=0,
                messages=[{"role": "user", "content": PROMPT.format(
                    q=query, contexto=contexto_del_estado(working_state))}])
            raw = "".join(b.text for b in msg.content
                          if getattr(b, "type", "") == "text")
            decision = parse_decision(raw)
        except Exception:                        # noqa: BLE001 — fail-open TOTAL
            decision = None
        _intent.ultima = {"decision": decision,
                          "ms": int((time.perf_counter() - t0) * 1000)}
        return decision

    _intent.ultima = None
    return _intent
