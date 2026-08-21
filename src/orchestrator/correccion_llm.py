# -*- coding: utf-8 -*-
"""s333 — El clasificador de corrección de marca del lever `F1_CORRECCION_LLM`
(DEC del GO, pendiente de número).

UNA fuente para el prompt y el parser: este módulo lo importan el gate de juicio
(la cohorte congelada `evals/s333_correccion_cohort_v1.yaml`) y el transporte — el
prompt que se midió ES el que sirve. ANTI-GATE-SHOPPING: revisar el prompt =
cohorte nueva congelada (DEC-126).

Arquitectura (v2 §1): la plantilla determinista de s332/s332b es el fast-path ($0,
0 ms) y este clasificador es la RED que entra SOLO en su miss, sobre la población
acotada de v2 §2 (una marca no-ambigua, sin modelos bindeados, sin código de
modelo en el turno). Latencia solo ahí: la declarada del seam espejo
(`intent_llm.py`: p50 1,3 s / p95 4,4 s) frente a turnos RAG de ~28 s.

Modelo: `claude-sonnet-4-6` como pin CONSERVADOR — la familia que ya pasó un gate
de juicio en este seam. NO hereda el «Haiku NO-GO» de INTENT_LLM: aquel midió
COMPAT/SWITCH, métrica DISTINTA de la de aquí (Protocolo 2.5); el brazo Haiku del
gate de s333 es INFORMATIVO y no auto-swapea (v2 §3).

MINIMIZACIÓN (v2 §3, desviación DECLARADA vs `intent_llm`): el callable recibe
`last_query` y `marca` EXPLÍCITOS, no el `WorkingState` entero — solo viaja al
proveedor lo que el prompt usa (`last_answer_excerpt` NO viaja). El juicio ES
sobre la relación entre los dos turnos, así que `last_query` es imprescindible.

El callable devuelve SOLO "correccion" | "nuevo" | None; None = fail-open = la
conducta de hoy (la cascada sigue). JAMÁS lanza. La última decisión queda en
`fn.ultima` para que el transporte la estampe en la traza.
"""
from __future__ import annotations

import time
from typing import Callable

CORRECCION_MODEL = "claude-sonnet-4-6"

# EL prompt del gate (v1 §1.C, sin cambios en v2 §3 — una fuente).
PROMPT = """Eres el enrutador de un asistente técnico de sistemas contra incendios.
El técnico preguntó antes: «{last_query}»
Su siguiente mensaje es: «{q}»
La marca «{marca}» aparece en el mensaje nuevo.

¿El mensaje CORRIGE su pregunta anterior — indica que la marca/nombre que usó
antes estaba mal y que la correcta es «{marca}» (espera la respuesta a la MISMA
pregunta, ahora con esa marca)—, o es un TEMA NUEVO sobre «{marca}»?

Responde EXACTAMENTE una palabra: CORRECCION o NUEVO."""


def parse_decision(raw: str) -> str | None:
    """Parser ESTRICTO (v2 §3): CORRECCION/NUEVO con tolerancia a puntuación final;
    cualquier otra cosa → None. La política trata todo valor fuera del contrato
    como None (defensa en profundidad)."""
    token = (raw or "").strip().rstrip(".!").upper()
    return {"CORRECCION": "correccion", "NUEVO": "nuevo"}.get(token)


def construir_correccion_fn(api_key: str, model: str = CORRECCION_MODEL,
                            timeout_s: float = 6.0) -> Callable:
    """El CorreccionFn del transporte. Síncrono a propósito: el llamador lo mueve a
    `asyncio.to_thread` (el resolve corre en el event loop — Sol-1 v2 §1: la regla
    es `to_thread` con CUALQUIER seam LLM activo, no solo con el de intención)."""
    import anthropic

    # max_retries=0 (precedente Fable r11 de intent_llm): el default (2) convertia
    # un timeout de 6 s en ~19 s de espera antes del fail-open — una cola que el
    # gate jamas midio. Un intento: o responde a tiempo o fail-open YA (la conducta
    # de hoy —la cascada sin corregir— es aceptable).
    cliente = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=0)

    def _correccion(query: str, last_query: str, marca: str) -> str | None:
        t0 = time.perf_counter()
        decision = None
        try:
            msg = cliente.messages.create(
                model=model, max_tokens=4, temperature=0,
                messages=[{"role": "user", "content": PROMPT.format(
                    q=query, last_query=last_query, marca=marca)}])
            raw = "".join(b.text for b in msg.content
                          if getattr(b, "type", "") == "text")
            decision = parse_decision(raw)
        except Exception:                        # noqa: BLE001 — fail-open TOTAL
            decision = None
        _correccion.ultima = {"decision": decision,
                              "ms": int((time.perf_counter() - t0) * 1000)}
        return decision

    _correccion.ultima = None
    # Atestación de config (espejo Sol r12 M2): el e2e del flip verifica que el fn
    # que el seam construyó lleva EXACTAMENTE la config servida (timeout 6 s,
    # max_retries=0) — sin esto, un leg con cliente alterado no puede probar nada
    # sobre el default de producción.
    _correccion.config = {"model": model, "timeout_s": timeout_s, "max_retries": 0}
    return _correccion
