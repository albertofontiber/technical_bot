"""Transport-neutral turn orchestrator (multi-turn Phase 0, MT-0a).

Public surface: the four assessment contracts, the two plan variants, and the
Phase 0 ``run_turn`` passthrough plus the composition-seam helpers. No telegram
import here — Telegram is an ingress/egress adapter over this package (MT-0d).
"""

from __future__ import annotations

from .adapters import (
    RagServingAdapters,
    execute_rag_turn,
    from_production,
    replay_adapters,
)
from .contracts import (
    ClarifyPlan,
    PlanKind,
    RetrievalResult,
    SingleHopPlan,
    TurnPlan,
    TurnRequest,
    TurnResult,
)
from .orchestrator import plan_turn, run_turn

__all__ = [
    "ClarifyPlan",
    "PlanKind",
    "RagServingAdapters",
    "RetrievalResult",
    "SingleHopPlan",
    "TurnPlan",
    "TurnRequest",
    "TurnResult",
    "execute_rag_turn",
    "from_production",
    "plan_turn",
    "replay_adapters",
    "run_turn",
]
