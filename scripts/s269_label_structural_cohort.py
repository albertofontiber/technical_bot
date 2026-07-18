#!/usr/bin/env python3
"""S269 Etapa 1 — etiquetado DUAL independiente de la cohorte estructural congelada.

GOLD independiente del detector (dúo-Sol C2): dos etiquetadores modelo con prompts
DISTINTOS que ven SOLO el fragmento crudo (jamás el output del detector ni el bucket):

  A) Luna  — gpt-5.6-luna (OpenAI, Responses API; patrón scripts/s191_..._luna.py)
  B) Haiku — claude-haiku-4-5-20251001 (Anthropic, tool-use forzado con schema PLANO:
     sin arrays ni minItems/maxItems — restricción de dialecto conocida; patrón
     rectangular de src/rag/source_unit_gold.py)

Desacuerdo por (fragmento, familia) → árbitro claude-sonnet-4-6 (tercera opinión
independiente, decide la MAYORÍA); si el árbitro falla → DESCARTE declarado del ítem.
No-retry: una sola llamada por (modelo, fragmento); un fallo se registra, no se repite.

MODO PREFLIGHT POR DEFECTO: sin ``--execute`` NO hace ninguna llamada pagada — cuenta
ítems, estima coste contra el presupuesto del prereg (≤$6) y verifica el freeze de la
cohorte (sha256). Con ``--execute`` etiqueta y escribe:

  evals/s269_structural_cohort_labels_v1.jsonl   (progresivo, crash-safe)
  evals/s269_labeling_receipts_v1.json           (tokens/coste por modelo)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consola Windows cp1252

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
COHORT_PATH = EVALS / "s269_structural_cohort_v1.jsonl"
PREREG_PATH = EVALS / "s269_structural_cohort_prereg_v1.yaml"
LABELS_PATH = EVALS / "s269_structural_cohort_labels_v1.jsonl"
RECEIPTS_PATH = EVALS / "s269_labeling_receipts_v1.json"

MODEL_LUNA = "gpt-5.6-luna"
MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_ARBITER = "claude-sonnet-4-6"

BUDGET_USD = 6.0
MAX_OUTPUT_TOKENS = 1500

# USD por millón de tokens (pins de la casa: Luna = s191; Haiku/Sonnet = tarifas vigentes)
PRICES = {
    MODEL_LUNA: (1.0, 6.0),
    MODEL_HAIKU: (1.0, 5.0),
    MODEL_ARBITER: (3.0, 15.0),
}

FAMILY_KEYS = ("frange", "fbundle", "fmandatory", "fcount")
FAMILY_BY_KEY = {
    "frange": "F-RANGE",
    "fbundle": "F-BUNDLE",
    "fmandatory": "F-MANDATORY",
    "fcount": "F-COUNT",
}
SPAN_SLOTS = 3


def flat_label_schema() -> dict:
    """Transporte PLANO compartido: booleans + slots de span. Sin arrays/enums/refs
    (compatible con el dialecto de structured-output de Anthropic)."""
    props: dict = {}
    required: list[str] = []
    for key in FAMILY_KEYS:
        props[f"{key}_present"] = {"type": "boolean"}
        required.append(f"{key}_present")
        for slot in range(1, SPAN_SLOTS + 1):
            props[f"{key}_span_{slot}"] = {"type": "string"}
            required.append(f"{key}_span_{slot}")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": props,
    }


# ── prompts INDEPENDIENTES (definiciones desde las familias genéricas s243, ──
# ── NUNCA desde los regex del detector; el etiquetador ve SOLO el fragmento) ──

PROMPT_LUNA = """You are labeling one fragment extracted from a fire-protection technical manual
(Spanish or English). Decide, for each of four structural atom families, whether the fragment
contains at least one atom of that family. Judge only from the fragment text itself.

Families:
1. BOUNDED RANGE ("frange"): a numeric operating/configuration constraint stated as a bounded
   range or tolerance — both ends with their unit (e.g. a value programmable from X to Y seconds),
   possibly with a step/granularity or a configuration scope (switch positions, channels).
   A lone number without a bounded range does not count.
2. STRUCTURED BUNDLE ("fbundle"): a parent header, tab or rule schema whose member fields or
   options are defined together (e.g. a heading followed by labeled fields "Label: definition",
   or a definition list that forms a schema). A heading with prose only does not count.
3. MANDATORY/SAFETY ("fmandatory"): a sentence carrying mandatory, prohibition or hazard force —
   words like obligatorio, imprescindible, nunca, jamás, advertencia, atención, peligro, evite,
   mandatory, must not, never, warning, caution, danger, or an obligation tied to a precondition
   ("debe ... antes de", "must ... before"). A plain "antes de"/"before" without obligation
   wording does NOT count.
4. COUNT CONFLICT ("fcount"): the text declares a count of options/members (words or digits) and
   the members actually enumerated nearby (bullets, table rows, columns) contradict that count.
   A consistent declared count is NOT an atom.

Return a strict JSON object with exactly these keys and nothing else:
frange_present, frange_span_1..3, fbundle_present, fbundle_span_1..3,
fmandatory_present, fmandatory_span_1..3, fcount_present, fcount_span_1..3.
Each *_present is a boolean. Each *_span_N is a VERBATIM substring copied exactly from the
fragment supporting the family (use "" for unused slots; fill spans only when present=true).

FRAGMENT:
<<<FRAGMENT>>>"""

PROMPT_HAIKU = """Eres revisor técnico de manuales PCI. Te doy UN fragmento extraído de un manual
(español o inglés). Tu tarea: decidir si el fragmento contiene átomos de estas cuatro familias
estructurales, juzgando SOLO por el texto del fragmento.

fcount — CONFLICTO DE CARDINALIDAD: el texto declara un número de opciones/miembros (en cifra o
palabra) y la enumeración cercana (viñetas, filas o columnas de tabla) NO cuadra con ese número.
Si el conteo declarado y lo enumerado COINCIDEN, no hay átomo.

fmandatory — LENGUAJE OBLIGATORIO/PELIGRO: una oración con fuerza de obligación, prohibición o
peligro (imprescindible, obligatorio, "de vital importancia", nunca, jamás, advertencia, atención,
peligro, evite; mandatory, must not, never, warning, caution, danger; o una obligación ligada a
un requisito previo tipo "debe ... antes de"). OJO: "antes de"/"before" sin término de obligación
NO cuenta.

fbundle — ESQUEMA CABECERA-MIEMBROS: una cabecera, pestaña o regla cuyos campos/opciones miembro
se definen juntos (p. ej. un encabezado seguido de líneas "Etiqueta: definición", o una lista de
definiciones que forma un esquema). Una cabecera con solo prosa NO cuenta.

frange — RANGO ACOTADO: una restricción numérica de operación/configuración expresada como rango
o tolerancia con AMBOS extremos y su unidad (p. ej. programable de X a Y segundos), opcionalmente
con paso/granularidad o ámbito de configuración (posiciones de switch, canales). Un número suelto
sin rango NO cuenta.

Usa la herramienta registrar_etiquetas. Para cada familia: *_present (booleano) y hasta 3 spans
VERBATIM copiados EXACTAMENTE del fragmento que la sustentan ("" en los huecos sin usar; solo
rellena spans si present=true).

FRAGMENTO:
<<<FRAGMENT>>>"""

PROMPT_ARBITER = """Actúas como árbitro independiente. Dos revisores han discrepado al etiquetar
un fragmento de manual técnico PCI. NO verás sus etiquetas: emite tu propia opinión desde cero,
juzgando SOLO el texto del fragmento, y la mayoría decidirá.

Familias (marca present=true solo si el fragmento contiene al menos un átomo claro):
- frange: rango numérico ACOTADO con ambos extremos y unidad (opcional paso/ámbito). Un número
  suelto no cuenta.
- fbundle: cabecera/pestaña/regla con sus campos u opciones miembro definidos juntos (schema
  "Etiqueta: definición" o lista de miembros bajo un encabezado). Cabecera con solo prosa no
  cuenta.
- fmandatory: oración con fuerza obligatoria/prohibición/peligro (imprescindible, obligatorio,
  nunca, advertencia, atención, peligro, evite; mandatory, must not, never, warning, caution,
  danger; "debe ... antes de"). "antes de"/"before" solo, sin término obligatorio, NO cuenta.
- fcount: conteo declarado de opciones/miembros que CONTRADICE lo realmente enumerado al lado.
  Conteo consistente no es átomo.

Usa la herramienta registrar_etiquetas: *_present + hasta 3 spans VERBATIM ("" si no aplica).

FRAGMENTO:
<<<FRAGMENT>>>"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cohort() -> list[dict]:
    rows = [
        json.loads(line)
        for line in COHORT_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    frozen = prereg["cohort_artifact"]["sha256"]
    actual = sha256_file(COHORT_PATH)
    if actual != frozen:
        raise RuntimeError(
            f"freeze roto: sha256 de la cohorte {actual[:12]}… ≠ prereg {frozen[:12]}…"
        )
    if prereg["cohort_artifact"]["rows"] != len(rows):
        raise RuntimeError("freeze roto: número de filas ≠ prereg")
    budget = float(prereg["labeling_protocol"]["budget_usd_max"])
    if budget != BUDGET_USD:
        raise RuntimeError("presupuesto del prereg ≠ presupuesto del runner")
    return rows


def estimate_cost(rows: list[dict]) -> dict:
    total_chars = sum(len(r["texto"]) for r in rows)
    frag_tokens = total_chars / 4
    per_model_in = frag_tokens + 700 * len(rows)     # prompt + fragmento
    per_model_out = 350 * len(rows)
    detail = {}
    total = 0.0
    for model in (MODEL_LUNA, MODEL_HAIKU, MODEL_ARBITER):
        p_in, p_out = PRICES[model]
        cost = per_model_in / 1e6 * p_in + per_model_out / 1e6 * p_out
        # el árbitro solo corre en desacuerdos; presupuestamos el PEOR caso (todos)
        detail[model] = round(cost, 2)
        total += cost
    return {"items": len(rows), "per_model_usd": detail,
            "total_worst_case_usd": round(total, 2), "budget_usd": BUDGET_USD}


def _validate_labels(payload: dict, fragment: str) -> dict:
    """Valida el shape plano y la GROUNDEDNESS de los spans (deben ser substrings
    verbatim del fragmento; un span no-grounded se registra y se vacía)."""
    from jsonschema import Draft202012Validator

    errors = sorted(
        Draft202012Validator(flat_label_schema()).iter_errors(payload),
        key=lambda e: list(e.absolute_path),
    )
    if errors:
        raise ValueError(f"schema inválido: {errors[0].message}")
    out: dict = {}
    for key in FAMILY_KEYS:
        present = bool(payload[f"{key}_present"])
        spans = []
        ungrounded = 0
        for slot in range(1, SPAN_SLOTS + 1):
            span = str(payload[f"{key}_span_{slot}"]).strip()
            if not span:
                continue
            if span in fragment:
                spans.append(span)
            else:
                ungrounded += 1
        out[key] = {"present": present, "spans": spans, "ungrounded_spans": ungrounded}
    return out


class Usage:
    def __init__(self) -> None:
        self.by_model: dict[str, dict] = {}

    def add(self, model: str, tokens_in: int, tokens_out: int) -> None:
        rec = self.by_model.setdefault(
            model, {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        )
        rec["input_tokens"] += tokens_in
        rec["output_tokens"] += tokens_out
        rec["calls"] += 1

    def cost_usd(self) -> float:
        total = 0.0
        for model, rec in self.by_model.items():
            p_in, p_out = PRICES[model]
            total += rec["input_tokens"] / 1e6 * p_in + rec["output_tokens"] / 1e6 * p_out
        return total


def _call_luna(client, fragment: str, usage: Usage) -> dict:
    response = client.responses.create(
        model=MODEL_LUNA,
        reasoning={"effort": "low"},
        max_output_tokens=MAX_OUTPUT_TOKENS,
        input=[{
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": PROMPT_LUNA.replace("<<<FRAGMENT>>>", fragment),
            }],
        }],
    )
    usage.add(
        MODEL_LUNA,
        getattr(response.usage, "input_tokens", 0) or 0,
        getattr(response.usage, "output_tokens", 0) or 0,
    )
    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return _validate_labels(json.loads(raw), fragment)


def _call_anthropic_tool(client, model: str, prompt: str, fragment: str,
                         usage: Usage) -> dict:
    response = client.messages.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0,
        tools=[{
            "name": "registrar_etiquetas",
            "description": "Registra las etiquetas de familias estructurales del fragmento.",
            "input_schema": flat_label_schema(),
        }],
        tool_choice={"type": "tool", "name": "registrar_etiquetas"},
        messages=[{
            "role": "user",
            "content": prompt.replace("<<<FRAGMENT>>>", fragment),
        }],
    )
    usage.add(
        model,
        getattr(response.usage, "input_tokens", 0) or 0,
        getattr(response.usage, "output_tokens", 0) or 0,
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return _validate_labels(dict(tool_use.input), fragment)


def execute(rows: list[dict]) -> int:
    import anthropic
    import os
    from openai import OpenAI

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    usage = Usage()

    done: set[str] = set()
    if LABELS_PATH.exists():
        for line in LABELS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["fragment_id"])
        print(f"Reanudando: {len(done)} fragmentos ya etiquetados (no se repiten — no-retry)")

    with LABELS_PATH.open("a", encoding="utf-8", newline="\n") as out:
        for i, row in enumerate(rows, 1):
            if row["fragment_id"] in done:
                continue
            if usage.cost_usd() >= BUDGET_USD:
                print(f"PRESUPUESTO AGOTADO (${usage.cost_usd():.2f} >= ${BUDGET_USD}) — "
                      f"parando en el ítem {i}/{len(rows)}")
                break
            fragment = row["texto"]
            record: dict = {
                "fragment_id": row["fragment_id"],
                "sha256": row["sha256"],
                "status": "gold",
            }
            try:
                record["luna"] = _call_luna(openai_client, fragment, usage)
            except Exception as exc:  # no-retry: se registra y sigue
                record["luna"] = None
                record["luna_error"] = str(exc)[:300]
            try:
                record["haiku"] = _call_anthropic_tool(
                    anthropic_client, MODEL_HAIKU, PROMPT_HAIKU, fragment, usage
                )
            except Exception as exc:
                record["haiku"] = None
                record["haiku_error"] = str(exc)[:300]

            if record["luna"] is None or record["haiku"] is None:
                record["status"] = "discarded_labeler_error"
                record["final"] = None
            else:
                disagreements = [
                    key for key in FAMILY_KEYS
                    if record["luna"][key]["present"] != record["haiku"][key]["present"]
                ]
                record["disagreements"] = disagreements
                if disagreements:
                    try:
                        record["arbiter"] = _call_anthropic_tool(
                            anthropic_client, MODEL_ARBITER, PROMPT_ARBITER,
                            fragment, usage,
                        )
                    except Exception as exc:
                        record["arbiter"] = None
                        record["arbiter_error"] = str(exc)[:300]
                        record["status"] = "discarded_arbiter_error"
                        record["final"] = None
                if record["status"] == "gold":
                    final: dict = {}
                    for key in FAMILY_KEYS:
                        votes = [record["luna"][key]["present"],
                                 record["haiku"][key]["present"]]
                        if record.get("arbiter") is not None:
                            votes.append(record["arbiter"][key]["present"])
                        final[key] = sum(votes) >= 2 if len(votes) == 3 else votes[0]
                    record["final"] = final
            out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            out.flush()
            if i % 10 == 0:
                print(f"  {i}/{len(rows)} | ${usage.cost_usd():.2f}")

    receipts = {
        "instrument": "s269_label_structural_cohort",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cohort_sha256": sha256_file(COHORT_PATH),
        "models": {"labeler_a": MODEL_LUNA, "labeler_b": MODEL_HAIKU,
                   "arbiter": MODEL_ARBITER},
        "usage": usage.by_model,
        "total_cost_usd": round(usage.cost_usd(), 4),
        "budget_usd": BUDGET_USD,
        "no_retry": True,
    }
    RECEIPTS_PATH.write_text(
        json.dumps(receipts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"\nEtiquetas: {LABELS_PATH.relative_to(ROOT)}")
    print(f"Receipts: {RECEIPTS_PATH.relative_to(ROOT)} | coste ${usage.cost_usd():.2f}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute", action="store_true",
        help="ejecuta el etiquetado PAGADO (sin este flag: preflight, 0 llamadas)",
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)

    rows = load_cohort()
    estimate = estimate_cost(rows)
    print(f"Cohorte congelada verificada (sha256 OK): {len(rows)} fragmentos")
    print(f"Estimación de coste (peor caso, árbitro en TODOS los ítems): "
          f"{json.dumps(estimate['per_model_usd'])} → total "
          f"${estimate['total_worst_case_usd']} (presupuesto ${BUDGET_USD})")
    if estimate["total_worst_case_usd"] > BUDGET_USD:
        print("ESTIMACIÓN > PRESUPUESTO — no ejecutar sin revisar el prereg")
        return 1
    if not args.execute:
        print("\nPREFLIGHT (0 llamadas pagadas). Para etiquetar:")
        print("  python scripts/s269_label_structural_cohort.py --execute")
        return 0
    return execute(rows)


if __name__ == "__main__":
    sys.exit(main())
