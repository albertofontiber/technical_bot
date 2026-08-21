"""Transport-neutral contracts for one conversational turn (S276 assessment §3).

Frozen dataclasses only: no telegram, no I/O, no LLM. Phase 0 supports a single
executable plan — ``SingleHopPlan`` (passthrough to the current pipeline).
``ClarifyPlan`` is declared for the contract surface (Phase 1 deterministic
classifier) but ``run_turn`` never produces it in Phase 0.

The four contracts named by the assessment are ``TurnRequest``, ``TurnPlan``
(``single_hop`` | ``clarify``), ``RetrievalResult`` and ``TurnResult``. Extra
fields beyond the assessment are the minimum needed to drive the existing
``execute_rag_turn`` seam without changing its behavior; each is annotated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Union

# (s332) `TurnIdentity` (de `conversation_policy`) se anota como CADENA y NO se
# importa: las anotaciones ya eran diferidas, así que el import era puro tipado — y
# a cambio ataba este módulo al de la política. Ese lazo era el que hacía crecer el
# ciclo permitido `conversation_policy ↔ ..._impl` en cuanto `_impl` importaba de
# aquí (`Asuncion`), y `test_import_contract` lo pone rojo con razón. Cortarlo aquí
# es la raíz: `contracts` queda como superficie de contratos SIN dependencias de la
# política, que es lo que siempre debió ser (y libera el import inverso).


class PlanKind(str, Enum):
    SINGLE_HOP = "single_hop"
    CLARIFY = "clarify"


# (s332 §2) Enums CERRADOS de `Asuncion`. El guard es estricto a propósito: una
# asunción mal construida revienta al construirse, no al renderizarse.
_ASUNCION_KINDS = frozenset({"marca_asr", "marca_corregida", "marca_fuzzy"})
_ASUNCION_MODOS = frozenset({"reescrito", "aviso"})


@dataclass(frozen=True, kw_only=True)
class Asuncion:
    """Una asunción DECLARADA que el turno hace en nombre del usuario (s332 §2).

    Es la primitiva GENERALIZABLE del mandato: cualquier mecanismo que sustituya o
    interprete lo que el usuario dijo la emite, y el transporte la renderiza de
    forma determinista (cero LLM — la conducta no se delega al prompt).

    ``detectado`` es lo que llegó (ASR crudo / token del usuario) y JAMÁS viaja al
    trace: al trace solo va ``asumido``, que es término gobernado (allowlist s331).
    """

    kind: str        # 'marca_asr' | 'marca_corregida'
    detectado: str
    asumido: str
    modo: str        # 'reescrito' (el texto se sustituyó) | 'aviso' (texto intacto)

    def __post_init__(self) -> None:
        if self.kind not in _ASUNCION_KINDS:
            raise ValueError(
                f"Asuncion.kind inválido: {self.kind!r} — esperado uno de "
                f"{sorted(_ASUNCION_KINDS)}")
        if self.modo not in _ASUNCION_MODOS:
            raise ValueError(
                f"Asuncion.modo inválido: {self.modo!r} — esperado uno de "
                f"{sorted(_ASUNCION_MODOS)}")
        if not self.detectado.strip():
            raise ValueError(
                "Asuncion.detectado vacío: sin lo que se detectó, el aviso al "
                "usuario no dice nada verificable")
        if not self.asumido.strip():
            raise ValueError(
                "Asuncion.asumido vacío: una asunción sin término gobernado no es "
                "una asunción, es ruido")


@dataclass(frozen=True, kw_only=True)
class TurnRequest:
    """Ingress unit of one turn (assessment §3: ``turn -> resolved context``).

    ``query`` and the routing identity describe what the user sent. The resolved
    retrieval inputs (``query_for_retrieval`` / ``target_models`` /
    ``available_models``) mirror the work ``_process_query`` already does before
    the pipeline (carry-forward, model detection, category lookup); in Phase 0
    the ingress adapter fills them so ``run_turn`` stays a pure passthrough.
    """

    # --- user-facing / routing identity ---
    query: str
    retrieval_top_k: int
    rerank_top_k: int
    channel: str = "telegram"
    conversation_id: str | None = None
    # Ingress dedup key (assessment: unique ``(channel, external_update_id)``).
    external_update_id: str | None = None
    # (s324h Fase 2) SIN default: el mismo `= "text"` estaba replicado seis veces
    # y ninguna era verdad la mitad de las veces, asi que olvidar la procedencia
    # registraba en silencio que un audio se habia tecleado. `kw_only` obliga a
    # nombrarlo; sin default, olvidarlo es un TypeError y no una fila falsa.
    source: str  # text | voice — lo construye `Procedencia` en el manejador
    transcription: str | None = None  # raw ASR preserved for audit

    # --- resolved retrieval inputs (Phase 0: filled by the ingress adapter) ---
    # None means "caller did not resolve a distinct retrieval query" -> use query.
    query_for_retrieval: str | None = None
    # None is passed through to the pipeline as None; an empty tuple is passed as
    # ``[]``. The distinction matters: the handler passes ``[]`` while the gold
    # harness passes ``None`` — both must be reproducible byte-for-byte.
    target_models: tuple[str, ...] | None = None
    available_models: tuple[str, ...] | None = None

    # (s331 §3.D) Identidad ESTRUCTURADA del turno (modelos resueltos + mención
    # no-resuelta, cada uno con su procedencia). Es el canal por el que la
    # resolución viaja hasta generación SIN pasar por el texto de la query. El
    # ingress la copia de `TurnResolution.turn_identity`; `None` (el default, y
    # lo único que produce el régimen sin F1) = conducta de hoy byte-idéntica.
    turn_identity: "TurnIdentity | None" = None

    @property
    def effective_retrieval_query(self) -> str:
        """The retrieval query the pipeline should use (falls back to ``query``)."""
        return self.query if self.query_for_retrieval is None else self.query_for_retrieval


@dataclass(frozen=True, kw_only=True)
class SingleHopPlan:
    """The only plan Phase 0 executes: retrieve -> rerank -> coverage -> generate
    once, delegating to the current pipeline. Carries the resolved inputs that
    ``run_turn`` hands to ``execute_rag_turn``."""

    query_for_retrieval: str
    retrieval_top_k: int
    rerank_top_k: int
    target_models: tuple[str, ...] | None = None
    available_models: tuple[str, ...] | None = None
    # (s331 §3.D) La identidad del turno viaja del request al plan sin
    # transformarse: `plan_turn` la COPIA y `run_turn` la entrega al seam. `None`
    # = sin identidad (o levers apagados) ⇒ byte-idéntico a antes del threading.
    turn_identity: "TurnIdentity | None" = None
    kind: PlanKind = field(default=PlanKind.SINGLE_HOP, init=False)


@dataclass(frozen=True, kw_only=True)
class ClarifyPlan:
    """Declared for the contract surface; not produced by ``run_turn`` in Phase 0.
    Phase 1 emits it from the deterministic standalone classifier when a turn is
    ambiguous (variant/product divergence)."""

    reason: str
    question: str
    kind: PlanKind = field(default=PlanKind.CLARIFY, init=False)


TurnPlan = Union[SingleHopPlan, ClarifyPlan]


@dataclass(frozen=True, kw_only=True)
class RetrievalResult:
    """Outcome of retrieval + rerank + governed coverage for the turn.

    ``chunks`` are the served chunks (the exact context the writer sees).
    ``coverage_trace`` is the receipt already produced by ``execute_rag_turn``.
    """

    chunks: tuple[dict[str, Any], ...]
    coverage_trace: dict[str, Any]
    retrieval_rows: int
    reranked_rows: int
    # (s306/#63) Fail-opens de canal del retriever este turno. Shape del seam:
    # {"channel", "error", "error_type"} — `error` es el repr in-process (NO
    # persiste; la telemetría acotada solo toma channel+error_type). `retrieval_
    # measured` distingue «el seam midió» de «no había seam» (dúo s306) — los
    # defaults dicen SIN MEDIDA, lo honesto para un constructor previo a s306.
    channel_failures: tuple[dict[str, Any], ...] = ()
    retrieval_measured: bool = False


@dataclass(frozen=True, kw_only=True)
class TurnResult:
    """Final outcome of the turn.

    ``compute_status`` uses the adjudicated ``convo.turn_runs`` vocabulary
    (``pending`` | ``running`` | ``answer_ready`` | ``delivered`` | ``failed``,
    MT-0b DDL). Phase 0 returns ``answer_ready`` on success; the
    ``pending -> running`` lifecycle and its persistence are MT-0c/0d, not this
    lane. ``generation`` keeps the raw writer
    dict (stop_reason/tokens/traces) so downstream persistence never has to
    reconstruct it.
    """

    answer: str
    diagrams: tuple[dict[str, Any], ...]
    plan: TurnPlan
    compute_status: str
    retrieval: RetrievalResult | None = None
    generation: dict[str, Any] | None = None
    # (s315/punto-1) Desglose de latencia del seam. `None` = sin medida (el
    # default honesto para constructores previos, espejo de retrieval_measured).
    stage_timings: dict[str, int] | None = None
