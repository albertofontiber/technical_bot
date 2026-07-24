#!/usr/bin/env python3
"""Multi-turn eval harness (S281 / MT-1b): conduce flujos conversacionales por el
ORQUESTADOR sobre un FakeConvoStore y verifica el ROUTING + la RESOLUCIÓN de la
policy (src/orchestrator/conversation_policy.py).

Dos modos:

  --contract  (default, $0, sin API, sin DB):
      * Carga evals/multiturn_golds_v1.yaml + la policy activa (default_policy()).
      * Si la policy es el STUB (MT-1a aún no implementó) -> reporta cada turno
        como PENDING y sale 0: el eval es un SPEC listo, no un gate que falla.
        Aun así DRIVEA el orquestador con la resolución del gold para probar que
        los flujos corren $0 y el store entrega (plumbing verde).
      * Con la policy REAL -> aserciones DETERMINISTAS por turno (route,
        target_models, gate producto-explícito, $0-guarantee requires_llm_rewrite,
        substrings/códigos verbatim en la query de recuperación).

  --e2e  (DEFINIDO, NO se ejecuta en esta lane — cuesta API):
      * Rewriter económico (Sonnet, mandato Alberto 23-jul) + generate real +
        juez GPT-5.5 K=3 mayoría sobre la CONDUCTA conversacional + rewrite.
      * Gateado tras MT1B_E2E_CONFIRM=1 (nunca seteado aquí). El coste real se
        estampa por-lane en el DEC de cierre.

Uso:  python scripts/test_multiturn_vs_gold.py            # --contract
      python scripts/test_multiturn_vs_gold.py --e2e     # imprime el gate y sale
"""
from __future__ import annotations

import argparse
import os

# extract_product_models importa config/retriever, que leen CHUNKS_TABLE. Es puro
# (regex, sin DB) — lo fijamos ANTES del import como hace test_bot_vs_gold.py.
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.orchestrator import replay_adapters  # noqa: E402
from src.orchestrator.contracts import TurnRequest  # noqa: E402
from src.orchestrator.fake_convo_store import FakeConvoStore, ManualClock  # noqa: E402
from src.orchestrator.lifecycle import run_conversational_turn  # noqa: E402
from src.orchestrator.conversation_policy import (  # noqa: E402
    NON_PRODUCT_CODES,
    PolicyRoute,
    TurnResolution,
    WorkingState,
    default_policy,
)

GOLDS = ROOT / "evals" / "multiturn_golds_v1.yaml"
WINDOW_SECONDS = 3600  # carry-forward de 1h (telegram_bot SESSION_TIMEOUT)
BASE_TIME = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)

_COVERAGE_CLASSES = frozenset(
    {
        "followup_detalle",
        "pronombre",
        "cambio_producto_explicito",
        "correccion",
        "no_contestable_admit",
        "reinicio_tema",
        "carry_forward_1h",
        "codigos_tecnicos",
        "dos_conversaciones_aisladas",
        "clarify_solo_si_diverge",
        # s281 round-2 hardening (dúo blind spots — adjudicación MT-1a r1):
        "standalone_autocontenida",       # F1: self-contained Qs with articles -> standalone
        "compatibilidad_marca",           # F3: brand-compat follow-up (carry-forward / switch)
        "continuacion_dominio_limitrofe", # F4: in-window continuation past the gas gate
    }
)

# Rutas que la orquestación RECUPERA (drivean run_conversational_turn). CLARIFY y
# DECLINE cortan antes de recuperar (el bot responde sin cruzar el pipeline).
_RETRIEVING_ROUTES = frozenset(
    {PolicyRoute.STANDALONE, PolicyRoute.CARRY_FORWARD, PolicyRoute.REWRITE}
)


# ---------------------------------------------------------------------------
# Carga + validación de esquema
# ---------------------------------------------------------------------------
def load_flows(path: Path = GOLDS) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    flows = data["flows"]
    assert isinstance(flows, list) and flows, "multiturn_golds: 'flows' vacío"
    return flows


def validate_schema(flows: list[dict[str, Any]]) -> list[str]:
    """Devuelve una lista de errores de esquema (vacía = OK)."""
    errs: list[str] = []
    seen: set[str] = set()
    for f in flows:
        fid = f.get("flow_id", "<sin flow_id>")
        if fid in seen:
            errs.append(f"{fid}: flow_id duplicado")
        seen.add(fid)
        if f.get("clase") not in _COVERAGE_CLASSES:
            errs.append(f"{fid}: clase desconocida {f.get('clase')!r}")
        turns = f.get("turns") or []
        if not turns:
            errs.append(f"{fid}: sin turnos")
        for t in turns:
            exp = t.get("expect") or {}
            route = exp.get("route")
            if route not in {r.value for r in PolicyRoute}:
                errs.append(f"{fid} t{t.get('n')}: route inválido {route!r}")
            # $0-guarantee declarada en el gold: requires_llm_rewrite True <=> rewrite.
            rlr = exp.get("requires_llm_rewrite", route == "rewrite")
            if (route == "rewrite") != bool(rlr):
                errs.append(
                    f"{fid} t{t.get('n')}: requires_llm_rewrite={rlr} incoherente con route={route}"
                )
    return errs


def covered_classes(flows: list[dict[str, Any]]) -> set[str]:
    return {f["clase"] for f in flows}


# ---------------------------------------------------------------------------
# Detección de modelos (compone extract_product_models, no lo duplica)
# ---------------------------------------------------------------------------
def _detect(query: str) -> tuple[list[str], list[str] | None]:
    """(turn_models, available_models) — espeja telegram_bot pasos 1a/2b, $0."""
    from src.rag.retriever import (
        extract_product_models,
        get_category_models,
        CATEGORY_TERMS,
    )

    turn_models = extract_product_models(query)
    available: list[str] | None = None
    if not turn_models:
        ql = query.lower()
        for term, cat in CATEGORY_TERMS.items():
            if term in ql:
                try:
                    available = get_category_models(cat)
                except Exception:
                    # Fail-open (CI sin credenciales Supabase / hiccup DB): la
                    # categoría solo alimenta opciones de CLARIFY, nunca bloquea.
                    available = None
                break
    return turn_models, available


# ---------------------------------------------------------------------------
# Aserciones deterministas (importadas por los tests)
# ---------------------------------------------------------------------------
def assert_resolution(resolution: TurnResolution, expect: dict[str, Any]) -> list[str]:
    """Compara una TurnResolution real con el gold. Devuelve fallos ([] = PASS)."""
    fails: list[str] = []
    exp_route = expect["route"]
    if resolution.route.value != exp_route:
        fails.append(f"route {resolution.route.value} != esperado {exp_route}")

    # $0 guarantee: solo REWRITE puede requerir el rewriter.
    exp_rlr = bool(expect.get("requires_llm_rewrite", exp_route == "rewrite"))
    if resolution.requires_llm_rewrite != exp_rlr:
        fails.append(
            f"requires_llm_rewrite {resolution.requires_llm_rewrite} != {exp_rlr}"
        )

    got_models = set(resolution.target_models or ())
    if "target_models" in expect and not expect.get("entity_out_of_corpus"):
        exp_models = set(expect["target_models"])
        if got_models != exp_models:
            fails.append(f"target_models {sorted(got_models)} != {sorted(exp_models)}")

    for forbidden in expect.get("must_not_target", []):
        if forbidden in got_models:
            fails.append(f"filtró producto prohibido {forbidden!r} en target_models")

    if exp_route == "clarify" and not resolution.clarify_question:
        fails.append("route=clarify sin clarify_question")
    if exp_route == "decline" and not resolution.decline_reason:
        fails.append("route=decline sin decline_reason")

    # Substrings / códigos verbatim en la query de recuperación (rutas que NO
    # reescriben: el texto crudo se preserva; en rewrite el código va a --e2e).
    if resolution.route in (PolicyRoute.STANDALONE, PolicyRoute.CARRY_FORWARD):
        qfr = resolution.query_for_retrieval or ""
        for sub in expect.get("query_for_retrieval_contains", []):
            if sub not in qfr:
                fails.append(f"query_for_retrieval no contiene {sub!r}")
        for tok in expect.get("query_for_retrieval_preserves", []):
            if tok not in qfr:
                fails.append(f"query_for_retrieval no preserva verbatim {tok!r}")
    return fails


def update_working_state(
    ws: WorkingState,
    resolution: TurnResolution,
    query: str,
    answer_excerpt: str | None,
    now: datetime,
    available: list[str] | None,
) -> WorkingState:
    """Estado durable tras un turno resuelto. CLARIFY/DECLINE no fijan modelo (el
    usuario aún no desambiguó) y devuelven el estado previo INTACTO — sin refrescar
    ``last_turn_at``. Refrescarlo RESUCITARÍA un producto caducado (clarify a 70 min
    + otro turno colgante lo re-encontraría "en ventana"). Espeja el fix de
    ``advance_working_state`` en el bot (S99 / sol-S4 + F2) para que prod y eval
    queden en lock-step."""
    if resolution.route in (PolicyRoute.CLARIFY, PolicyRoute.DECLINE):
        return ws
    models = tuple(resolution.target_models or ())
    return WorkingState(
        last_target_models=models,
        last_query=query,
        last_answer_excerpt=(answer_excerpt or "")[:500] or None,
        last_turn_at=now,
        available_models=tuple(available) if available else None,
    )


# ---------------------------------------------------------------------------
# Driver del orquestador (contract, $0)
# ---------------------------------------------------------------------------
def _recording_generate(record: dict[str, Any]):
    def generate(query, chunks, *, available_models=None):
        record["served_query"] = query
        record["n_chunks"] = len(chunks)
        return {"answer": f"[stub] {query}", "diagrams": [], "input_tokens": 0,
                "output_tokens": 0}

    return generate


def _drive_turn_through_orchestrator(
    store: FakeConvoStore,
    *,
    query: str,
    query_for_retrieval: str,
    target_models: tuple[str, ...] | None,
    available_models: tuple[str, ...] | None,
    conversation_id: str,
    update_id: str,
    adapters: Any | None = None,
) -> tuple[str, str]:
    """Un turno RECUPERADOR por run_conversational_turn. Por defecto usa adapters
    replay ($0, --contract); en --e2e se inyectan adapters REALES (retrieve+rerank+
    generate de producción). Devuelve (served_query, answer_excerpt). Verifica que
    el store ENTREGA exactly-once."""
    record: dict[str, Any] = {}
    if adapters is None:
        adapters = replay_adapters(
            retrieved=[{"id": "c0", "content": "ctx", "similarity": 0.9}],
            generate=_recording_generate(record),
        )
    req = TurnRequest(
        query=query,
        query_for_retrieval=query_for_retrieval,
        target_models=target_models,
        available_models=available_models,
        retrieval_top_k=50,
        rerank_top_k=5,
        channel="telegram",
        conversation_id=conversation_id,
        external_update_id=update_id,
    )
    sends: list[Any] = []

    def _sender(payload):
        sends.append(payload)
        return f"tg-{payload.outbox_id}-{payload.attempt_no}"

    out = run_conversational_turn(store, req, adapters, "mt1b-worker", _sender)
    assert out.status == "delivered", f"orquestador no entregó: {out.status}"
    assert len(sends) == 1, "entrega no exactly-once en el happy path"
    return record.get("served_query", ""), (out.result.answer if out.result else "")


# ---------------------------------------------------------------------------
# Modo --contract
# ---------------------------------------------------------------------------
def run_contract(flows: list[dict[str, Any]], policy: Any | None = None) -> dict[str, Any]:
    """Ejecuta el eval en modo contrato. Reporta PENDING si la policy es stub.

    ``policy`` inyectable (los tests pasan una policy de referencia determinista
    para probar que las aserciones tienen dientes; por defecto = default_policy()).
    """
    if policy is None:
        policy = default_policy()
    is_stub = bool(getattr(policy, "IS_STUB", False))

    report: dict[str, Any] = {
        "mode": "contract",
        "policy_stub": is_stub,
        "flows": len(flows),
        "turns": sum(len(f.get("turns") or []) for f in flows),
        "classes_covered": sorted(covered_classes(flows)),
        "pass": 0,
        "fail": 0,
        "pending": 0,
        "failures": [],
        "plumbing_ok": 0,
    }

    for f in flows:
        fid = f["flow_id"]
        clock = ManualClock(start=BASE_TIME)
        store = FakeConvoStore(clock=clock)
        ws = WorkingState()
        for i, t in enumerate(f["turns"]):
            clock.advance(int(t.get("advance_seconds", 0)))
            now = clock.now()
            query = t["query"]
            expect = t["expect"]
            turn_models, available = _detect(query)
            avail_tuple = tuple(available) if available else None

            if is_stub:
                # No hay policy: DRIVEA el orquestador con la resolución del gold
                # (prueba $0 de que el flujo corre y el store entrega) y marca la
                # aserción de policy como PENDING.
                report["pending"] += 1
                if expect["route"] in {r.value for r in _RETRIEVING_ROUTES}:
                    served, answer = _drive_turn_through_orchestrator(
                        store,
                        query=query,
                        query_for_retrieval=query,  # crudo: replay ignora la query
                        target_models=tuple(expect.get("target_models", ())) or None,
                        available_models=avail_tuple,
                        conversation_id=f["conversation"],
                        update_id=f"{fid}-{i}",
                    )
                    report["plumbing_ok"] += 1
                continue

            # ---- policy REAL: aserciones deterministas ----
            resolution = policy.resolve(
                query=query,
                turn_models=turn_models,
                available_models=available,
                working_state=ws,
                now=now,
            )
            fails = assert_resolution(resolution, expect)
            answer_excerpt = None
            if not fails and resolution.route in _RETRIEVING_ROUTES:
                served, answer_excerpt = _drive_turn_through_orchestrator(
                    store,
                    query=query,
                    query_for_retrieval=resolution.query_for_retrieval,
                    target_models=resolution.target_models,
                    available_models=resolution.available_models or avail_tuple,
                    conversation_id=f["conversation"],
                    update_id=f"{fid}-{i}",
                )
                report["plumbing_ok"] += 1
            if fails:
                report["fail"] += 1
                report["failures"].append({"flow": fid, "turn": t["n"], "errs": fails})
            else:
                report["pass"] += 1
            ws = update_working_state(
                ws, resolution, query, answer_excerpt, now, available
            )
    return report


def _print_report(report: dict[str, Any]) -> int:
    print("=" * 66)
    print(f"MT-1b eval — modo {report['mode']}")
    print(f"  flujos={report['flows']}  turnos={report['turns']}  "
          f"clases={len(report['classes_covered'])}/{len(_COVERAGE_CLASSES)}")
    print(f"  clases: {', '.join(report['classes_covered'])}")
    if report["policy_stub"]:
        print("\n  POLICY = STUB (MT-1a pendiente). Aserciones de routing: PENDING.")
        print(f"  Plumbing del orquestador ejecutado $0 en {report['plumbing_ok']} "
              f"turnos recuperadores (store entregó exactly-once).")
        print(f"  PENDING={report['pending']}  (re-corre --contract cuando MT-1a "
              f"implemente default_policy())")
        return 0
    print(f"\n  PASS={report['pass']}  FAIL={report['fail']}  "
          f"plumbing_ok={report['plumbing_ok']}")
    for fr in report["failures"]:
        print(f"  [FAIL] {fr['flow']} t{fr['turn']}: {'; '.join(fr['errs'])}")
    return 0 if report["fail"] == 0 else 1


# ---------------------------------------------------------------------------
# Modo --e2e (REAL, doble-gateado — no se ejecuta pagado en esta lane)
# ---------------------------------------------------------------------------
E2E_SPEC = """\
--e2e (REAL, doble-gateado — no se ejecuta pagado en la lane MT-1a):
  Wiring:
    * rewrite  = rewriter económico source-bound (make_rewriter, Sonnet; mandato
                 Alberto 23-jul). Se inyecta como RewriteFn en policy.resolve(...)
                 en las rutas REWRITE. Cliente Anthropic REAL solo bajo doble gate.
    * generate = adapters de producción (retrieve+rerank+generate, chunks_v2/Voyage)
                 conducidos por el ORQUESTADOR (run_conversational_turn).
    * juez     = GPT-5.5 K=3 mayoría (freeze DEC-023) sobre la CONDUCTA del último
                 turno: (a) fidelidad del rewrite, (b) expected_behavior
                 (answer|admit|clarify|refuse-inference), (c) no-fuga de producto.
  Control: el ROUTING ya se asevera determinista y $0 en --contract; --e2e SOLO
  cubre lo que exige LLM. Se corre una vez con freeze (corpus+índice+embeddings+
  juez+seeds+config) y el coste se ESTAMPA en el YAML de salida + DEC de cierre.
  DOBLE GATE: requiere MT1B_E2E_CONFIRM=1 Y MT1B_E2E_SPEND_ACK=1. Sin ambos,
  imprime el spec y sale 0 (cero gasto).
"""

# Coste aproximado por 1M tokens (USD). Placeholders honestos: la corrida pagada de
# cierre estampa los ACTUALES; aquí solo dan un orden de magnitud del gasto e2e.
_E2E_PRICES_USD_PER_MTOK = {
    "generate": {"in": 3.0, "out": 15.0},   # Sonnet tier
    "judge": {"in": 1.25, "out": 10.0},      # gpt-5.5 (aprox)
}


def _majority(labels: list[str]) -> str:
    from collections import Counter

    if not labels:
        return "?"
    return Counter(labels).most_common(1)[0][0]


def _usd_estimate(cost: dict[str, Any]) -> float:
    g = _E2E_PRICES_USD_PER_MTOK["generate"]
    j = _E2E_PRICES_USD_PER_MTOK["judge"]
    return round(
        (cost["generate_input_tokens"] * g["in"] + cost["generate_output_tokens"] * g["out"]
         + cost["judge_input_tokens"] * j["in"] + cost["judge_output_tokens"] * j["out"]) / 1e6,
        4,
    )


def run_e2e_flows(
    flows: list[dict[str, Any]],
    *,
    rewrite: Any,
    adapters: Any,
    judge_fn: Any,
    gold_rows: dict[str, Any] | None = None,
    judge_k: int = 3,
    now0: datetime = BASE_TIME,
) -> dict[str, Any]:
    """Núcleo del --e2e, TESTEABLE con fakes ($0). Conduce cada flujo con la policy
    REAL + ``rewrite`` inyectado; los turnos recuperadores cruzan el ORQUESTADOR con
    ``adapters`` (reales en la corrida pagada, fakes en tests); el último turno se
    juzga con ``judge_fn`` K veces (mayoría). Acumula y estampa el coste.

    Inyectables (todos fakeables): ``rewrite`` (RewriteFn), ``adapters``
    (RagServingAdapters), ``judge_fn(question, expected, gold, bot) -> dict`` con
    claves ``veredicto`` y opcional ``usage={'in','out'}``."""
    import dataclasses

    policy = default_policy()
    gold_rows = gold_rows or {}
    cost: dict[str, Any] = {
        "rewrite_calls": 0, "generate_calls": 0, "judge_calls": 0,
        "generate_input_tokens": 0, "generate_output_tokens": 0,
        "judge_input_tokens": 0, "judge_output_tokens": 0,
    }

    # Envuelve generate para acumular uso de tokens (real o fake, byte-invariante).
    _orig_generate = adapters.generate

    def _accruing_generate(*a: Any, **k: Any) -> Any:
        r = _orig_generate(*a, **k)
        if isinstance(r, dict):
            cost["generate_input_tokens"] += int(r.get("input_tokens") or 0)
            cost["generate_output_tokens"] += int(r.get("output_tokens") or 0)
        return r

    adapters = dataclasses.replace(adapters, generate=_accruing_generate)

    def _counting_rewrite(q: str, w: WorkingState) -> Any:
        cost["rewrite_calls"] += 1
        return rewrite(q, w)

    report: dict[str, Any] = {"mode": "e2e", "flows": len(flows),
                              "turns": sum(len(f.get("turns") or []) for f in flows),
                              "flow_results": [], "cost": cost}

    for f in flows:
        fid = f["flow_id"]
        clock = ManualClock(start=now0)
        store = FakeConvoStore(clock=clock)
        ws = WorkingState()
        gold_txt = ""
        for qid in f.get("reuses_golds", []):
            g = gold_rows.get(qid)
            if g and g.get("answer"):
                gold_txt = str(g["answer"]); break
        last: dict[str, Any] = {}
        for i, t in enumerate(f["turns"]):
            clock.advance(int(t.get("advance_seconds", 0)))
            now = clock.now()
            query = t["query"]
            expect = t["expect"]
            turn_models, available = _detect(query)
            avail_tuple = tuple(available) if available else None
            resolution = policy.resolve(
                query=query, turn_models=turn_models, available_models=available,
                working_state=ws, now=now, rewrite=_counting_rewrite,
            )
            answer = None
            answer_excerpt = None
            if resolution.route in _RETRIEVING_ROUTES:
                # La pregunta RESUELTA alimenta también la GENERACIÓN (patrón
                # condense-question BP): con la cruda, el writer no ve el
                # antecedente y pide el modelo pese al carry — 6/8 FALLOs de la
                # 1ª pasada e2e s281 tenían exactamente ese mecanismo. Para
                # standalone resuelta==cruda (paridad F0 intacta).
                _served, answer = _drive_turn_through_orchestrator(
                    store, query=resolution.query_for_retrieval,
                    query_for_retrieval=resolution.query_for_retrieval,
                    target_models=resolution.target_models,
                    available_models=resolution.available_models or avail_tuple,
                    conversation_id=f["conversation"], update_id=f"{fid}-{i}",
                    adapters=adapters,
                )
                cost["generate_calls"] += 1
                answer_excerpt = answer
            last = {
                "turn": t["n"], "route": resolution.route.value, "query": query,
                "query_for_retrieval": resolution.query_for_retrieval,
                "rewritten_query": resolution.rewritten_query,
                "clarify_question": resolution.clarify_question,
                "decline_reason": resolution.decline_reason,
                "answer": answer, "expected_behavior": expect.get("expected_behavior"),
            }
            ws = update_working_state(ws, resolution, query, answer_excerpt, now, available)

        verdicts: list[str] = []
        diagnosticos: list[str] = []
        for _ in range(judge_k):
            # Sin expected_behavior explícito en el gold, la conducta esperada se
            # deriva de la RUTA adjudicada del turno (una policy-clarify esperada
            # por el gold NO es "answer" — artefacto mt07b/mt07c 1ª pasada).
            _route_default = {
                "clarify": "clarify", "decline": "refuse-inference",
            }.get(str(last.get("route")), "answer")
            v = judge_fn(
                question=last.get("query_for_retrieval") or last.get("query", ""),
                expected=last.get("expected_behavior") or _route_default,
                gold=gold_txt,
                bot=last.get("answer") or last.get("clarify_question")
                    or last.get("decline_reason") or "",
            )
            cost["judge_calls"] += 1
            u = v.get("usage") or {}
            cost["judge_input_tokens"] += int(u.get("in") or 0)
            cost["judge_output_tokens"] += int(u.get("out") or 0)
            verdicts.append(str(v.get("veredicto", "?")))
            diagnosticos.append(str(v.get("diagnostico", ""))[:400])
        report["flow_results"].append({
            "flow": fid, "last_route": last.get("route"),
            "expected_behavior": last.get("expected_behavior"),
            "veredicto": _majority(verdicts), "verdicts": verdicts,
            # Sin diagnóstico no hay adjudicación posible (lección smoke s281):
            "diagnosticos": diagnosticos,
            "rewritten_query": last.get("rewritten_query"),
            "query_for_retrieval": (last.get("query_for_retrieval") or "")[:300],
            "answer_excerpt": (last.get("answer") or last.get("clarify_question") or "")[:400],
        })

    cost["usd_estimate"] = _usd_estimate(cost)
    cost["_note"] = ("USD aproximado (placeholders); la corrida de cierre pagada "
                     "estampa el coste real por-lane en el DEC.")
    return report


def _make_openai_judge() -> Any:
    """Juez GPT-5.5 real (reusa el patrón de scripts/test_bot_vs_gold.py). Cliente
    perezoso: no se construye hasta que se llama (solo bajo el doble gate)."""
    import json as _json

    _sys = (
        "Eres un evaluador imparcial de un bot técnico de sistemas PCI (detección de "
        "incendios) en conversación MULTI-TURNO. Juzgas la CONDUCTA del último turno."
    )
    _user = (
        "PREGUNTA (resuelta para recuperación):\n{question}\n\n"
        "CONDUCTA ESPERADA: {expected}\n"
        "(answer = responde con contenido; admit = admite que el corpus no lo cubre, "
        "sin inventar; clarify = pide la variante/modelo ante divergencia real; "
        "refuse-inference = no infiere lo no documentado)\n\n"
        "REFERENCIA (gold, si existe):\n{gold}\n\n"
        "RESPUESTA DEL BOT:\n{bot}\n\n"
        "Responde SOLO JSON: {{\"conducta_bot\": \"...\", \"veredicto\": "
        "\"PASS | PARCIAL | FALLO\", \"diagnostico\": \"1-2 frases\"}}"
    )
    state: dict[str, Any] = {"client": None}

    def _judge(*, question: str, expected: str, gold: str, bot: str) -> dict[str, Any]:
        if state["client"] is None:
            from openai import OpenAI  # local: solo en la corrida pagada

            state["client"] = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = state["client"].chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": _sys},
                {"role": "user", "content": _user.format(
                    question=question, expected=expected,
                    gold=(gold or "")[:3000], bot=(bot or "")[:3000])},
            ],
        )
        txt = resp.choices[0].message.content.strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1].lstrip("json").strip()
        usage = getattr(resp, "usage", None)
        try:
            out = _json.loads(txt)
        except Exception as e:
            out = {"veredicto": "?", "diagnostico": f"(parse error: {e}) {txt[:200]}"}
        if usage is not None:
            out["usage"] = {"in": getattr(usage, "prompt_tokens", 0),
                            "out": getattr(usage, "completion_tokens", 0)}
        return out

    return _judge


def run_e2e() -> int:
    print(E2E_SPEC)
    # DOBLE GATE: ambos flags deben estar puestos para tocar la API.
    gate1 = os.getenv("MT1B_E2E_CONFIRM") == "1"
    gate2 = os.getenv("MT1B_E2E_SPEND_ACK") == "1"
    if not (gate1 and gate2):
        print(f">> --e2e deshabilitado (MT1B_E2E_CONFIRM={os.getenv('MT1B_E2E_CONFIRM')!r}, "
              f"MT1B_E2E_SPEND_ACK={os.getenv('MT1B_E2E_SPEND_ACK')!r}). "
              "Se requieren AMBOS =1. Cero gasto. Salida 0.")
        return 0

    # Ambos gates puestos -> corrida pagada real (fuera de la lane MT-1a).
    import yaml as _yaml

    from src.orchestrator.adapters import from_production
    from src.orchestrator.rewriter import make_rewriter

    flows = load_flows()
    # Subset dirigido para smoke/A-B (patrón ONLY_QIDS de test_bot_vs_gold):
    # MT1B_ONLY_FLOWS=mt01,mt12 corre solo esos flow_ids. Plumbing, no vara.
    only = {f.strip() for f in os.getenv("MT1B_ONLY_FLOWS", "").split(",") if f.strip()}
    if only:
        flows = [f for f in flows if f["flow_id"] in only]
        print(f">> subset MT1B_ONLY_FLOWS: {sorted(only)} -> {len(flows)} flujos")
    gold_path = ROOT / "evals" / "gold_answers_v1.yaml"
    gold_rows = {r["qid"]: r for r in _yaml.safe_load(gold_path.read_text(encoding="utf-8"))}
    # Pin del run pagado: modelo del rewriter = tier de generación de prod salvo
    # override; variante de prompt para el A/B autorizado (fontiber|condense_lc).
    from src.config import LLM_MODEL as _prod_model
    rewrite = make_rewriter(
        model=os.getenv("MT1B_REWRITER_MODEL", _prod_model),
        prompt_variant=os.getenv("MT1B_REWRITE_VARIANT", "fontiber"),
    )
    adapters = from_production()
    judge_fn = _make_openai_judge()

    report = run_e2e_flows(
        flows, rewrite=rewrite, adapters=adapters, judge_fn=judge_fn, gold_rows=gold_rows,
    )
    out_path = ROOT / "evals" / "multiturn_e2e_result_v1.yaml"
    out_path.write_text(_yaml.safe_dump(report, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    print(f"\n>> --e2e completado. Coste: {report['cost']}")
    print(f">> Resultado estampado en {out_path}")
    fails = [r for r in report["flow_results"] if r["veredicto"] == "FALLO"]
    return 0 if not fails else 1


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="MT-1b multi-turn eval harness")
    ap.add_argument("--e2e", action="store_true", help="modo pagado (definido, no ejecuta)")
    args = ap.parse_args(argv)

    flows = load_flows()
    errs = validate_schema(flows)
    if errs:
        print("ESQUEMA INVÁLIDO:")
        for e in errs:
            print("  -", e)
        return 2
    missing = _COVERAGE_CLASSES - covered_classes(flows)
    if missing:
        print(f"COBERTURA INCOMPLETA: faltan clases {sorted(missing)}")
        return 2

    if args.e2e:
        return run_e2e()
    report = run_contract(flows)
    return _print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
