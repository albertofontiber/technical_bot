# -*- coding: utf-8 -*-
"""De dónde viene un turno: el canal y, si es voz, el ASR crudo.

Nace de un fallo del piloto vivo (s324h): la misma pregunta contestada por texto
y rechazada por voz. La causa NO era la ruta que faltaba — era que la procedencia
viajaba como **dos parámetros opcionales con un default que miente**. Censo de la
sesión: el mismo ``= "text"`` estaba replicado SEIS veces (``log_query``,
``_process_query``, ``TurnRequest``, ``build_turn_request``, ``Meta.fuente`` y el
propio ``query_logs.source`` del esquema).

Un default sólo debe existir cuando el valor omitido es VERDAD. ``"text"`` es la
mitad de los casos, así que olvidarse no fallaba: registraba en silencio, y para
siempre, que un audio se había tecleado.

Esta clase es el único origen. La invariante vive en ``__post_init__`` y no en los
constructores nombrados — el dúo (Sol y Fable, r47, convergente) tumbó la versión
que la ponía sólo ahí: ``Procedencia(...)`` es público y saltárselos es trivial.

**Binario a propósito, aunque la columna sea ternaria.** ``query_logs.source``
admite además ``'error'``, pero eso es una pseudo-fuente de *logging* que escribe
el manejador de errores directamente y que nunca construye una ``Procedencia``:
un turno viene de una persona por un canal, y los canales son dos. La asimetría
es deliberada y no hay que «arreglarla» en ninguna de las dos direcciones.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Los canales por los que puede llegar un turno. `Meta.fuente` mantiene su
#: propio vocabulario en castellano y se traduce con un mapa explícito en el
#: manejador; un canal nuevo debe aparecer en LOS DOS sitios o falla el test.
CANALES = ("text", "voice")


@dataclass(frozen=True)
class Procedencia:
    """Canal de un turno y, sólo en voz, la transcripción cruda del ASR.

    Se construye UNA vez, en el manejador que recibe el mensaje, y viaja hasta
    quien escribe la fila. No tiene default: omitir el canal es un `TypeError`,
    no una fila mal atribuida.
    """

    source: str
    transcription: str | None = None

    def __post_init__(self) -> None:
        if self.source not in CANALES:
            raise ValueError(
                f"canal desconocido: {self.source!r} (esperado uno de {CANALES})")
        if self.source == "voice" and not (self.transcription or "").strip():
            # `is not None` no bastaba: la cadena vacía colaba y dejaba una fila
            # de voz sin nada que auditar (Sol, r48).
            raise ValueError("una procedencia de voz sin ASR crudo no es auditable")
        if self.source == "text" and self.transcription is not None:
            raise ValueError("una procedencia de texto no puede llevar transcripción")

    @classmethod
    def de_texto(cls) -> "Procedencia":
        return cls(source="text")

    @classmethod
    def de_voz(cls, asr_crudo: str) -> "Procedencia":
        """`asr_crudo` es lo que dijo el ASR, TAL CUAL: es lo que el técnico ve y
        lo que se registra. La forma normalizada para búsqueda viaja aparte."""
        return cls(source="voice", transcription=asr_crudo)

    @property
    def es_voz(self) -> bool:
        return self.source == "voice"
