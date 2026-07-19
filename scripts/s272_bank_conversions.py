#!/usr/bin/env python3
"""S272 (DEC-131): BANKING determinista de las 2 conversiones certificadas del contrato
must-preserve sobre el funnel adjudicado (patrón S270/DEC-125: aritmética pura sobre
insumos SHA-pineados, $0, cero llamadas a modelo, cero red en el run por defecto).

Proyección: 143 OK / 9 synth / 2 retr / 154 (evals/s270_adjudicated_funnel_v1.json)
  + obl_b6f6211be439  (cert det-only v2: 3/3 estable — evals/s271_probe_det_certification_v2.json)
  + obl_872c35fb41d7  (re-score de spec opción-1 DEC-128: 3/3 ON / 0/3 OFF —
                       evals/s271_872c_respec_rescore_v1.json; cert v2: 2/3 ≥ regla)
  → **145 OK / 7 synth / 2 retr / 154 (94,16%)** — quedan +6 para 151 (98%).

RECIBO VIVO (adjudicación del alcance, coordinador s272): Alberto encendió
``MUST_PRESERVE_CONTRACT=on`` en Railway y disparó 3 preguntas (query_logs 2026-07-19):
  16:26Z ASD535    → apéndice CON el aviso de seguridad + checklist = b6f6 FIRE EN VIVO ✓
  16:29Z PEARL     → SIN apéndice: los chunks del 997-671 p43-45 (tabla de tipos) quedan
                     en posiciones 22-33 del pool, FUERA del top-10 servido → clase
                     composición-de-serving (retrieval-side), NO fallo del contrato;
                     la conversión 872c es harness-only (la ruta congelada SÍ los sirve)
  16:34Z CAD-250   → SIN apéndice = control sano, silencio correcto en vivo ✓
Los recibos (query/response/created_at + sha256 del response, sin datos personales) se
persisten en ``evals/s272_live_receipts_v1.json`` (``--fetch-receipts``, GET-only) y se
verifican aquí contra su pin.

Salida: ``evals/s272_banked_funnel_v1.json``.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import write_json  # noqa: E402

ADJUDICATED = ROOT / "evals/s270_adjudicated_funnel_v1.json"
CERT_B6F6 = ROOT / "evals/s271_probe_det_certification_v2.json"
RESCORE_872C = ROOT / "evals/s271_872c_respec_rescore_v1.json"
RECEIPTS = ROOT / "evals/s272_live_receipts_v1.json"
OUTPUT = ROOT / "evals/s272_banked_funnel_v1.json"

APPENDIX_MARKER = "Información adicional del manual"

# SHA-256 de bytes LF-normalizados (checkout Windows/autocrlf); el pin FALLA ante drift.
PINNED_SHA256_LF = {
    "evals/s270_adjudicated_funnel_v1.json": (
        "99e11e281a73a1396b1d64b9b335a0a6bed34149cd2a205f305afa5aea3d61fa"
    ),
    "evals/s271_probe_det_certification_v2.json": (
        "a8dd0c7130ac234e1765c26155e532f3041aeed8614348307dba151534b16e2d"
    ),
    "evals/s271_872c_respec_rescore_v1.json": (
        "541092b51624a7c28b8758072a2c82a2ff33c66596ee8d74f9a6aaf2ffe6a496"
    ),
    "evals/s272_live_receipts_v1.json": (
        "f4b764431226b1748630f31e83377c69262cf454b8f35bec4e14ee4ff274e001"
    ),
}

BANKED = ("obl_b6f6211be439", "obl_872c35fb41d7")

# Los 7 synth restantes POR CLASE (mapa causal DEC-127; ids del funnel adjudicado).
REMAINING_BY_CLASS = {
    "serving_view": ["obl_0d6a30948dfd"],
    "uncited_scope": ["obl_2f5d79e354b9"],
    "binding_tension": ["obl_7bba8d03d496"],
    "composites_hybrid_gap": [
        "obl_015f9b9aaa3a",
        "obl_7aa723717412",
        "obl_a5d9fa1f9253",
        "obl_b2043cd4379b",
    ],
}


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_pins() -> dict[str, str]:
    seen: dict[str, str] = {}
    for rel, expected in PINNED_SHA256_LF.items():
        actual = _sha256_lf(ROOT / rel)
        if actual != expected:
            raise ValueError(
                f"SHA drift en insumo pineado {rel}: esperado {expected}, actual {actual}"
            )
        seen[rel] = actual
    return seen


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_receipts(receipts_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Los 3 recibos vivos: sha256 del response RECALCULADO y flag de apéndice
    RECALCULADO desde el texto (el artefacto no se auto-atestigua)."""
    receipts = receipts_doc["receipts"]
    if len(receipts) != 3:
        raise ValueError(f"esperaba 3 recibos vivos, hay {len(receipts)}")
    expected = [
        ("b6f6_live_fire_asd535", "2026-07-19T16:26", True),
        ("872c_no_fire_pearl", "2026-07-19T16:29", False),
        ("control_sano_cad250", "2026-07-19T16:34", False),
    ]
    for receipt, (label, ts_prefix, appendix) in zip(receipts, expected):
        if receipt["label"] != label:
            raise ValueError(f"recibo fuera de orden: {receipt['label']} != {label}")
        if not str(receipt["created_at"]).startswith(ts_prefix):
            raise ValueError(f"timestamp inesperado en {label}: {receipt['created_at']}")
        recomputed = hashlib.sha256(receipt["response"].encode("utf-8")).hexdigest()
        if recomputed != receipt["response_sha256"]:
            raise ValueError(f"sha256 del response no cierra en {label}")
        marker = APPENDIX_MARKER in receipt["response"]
        if marker is not appendix or receipt["appendix_present"] is not appendix:
            raise ValueError(f"flag de apéndice no cierra en {label}: marker={marker}")
    return receipts


def build_projection() -> dict[str, Any]:
    pins = verify_pins()
    adjudicated = _load(ADJUDICATED)
    cert = _load(CERT_B6F6)
    rescore = _load(RESCORE_872C)
    receipts = verify_receipts(_load(RECEIPTS))

    baseline = adjudicated["adjudicated_funnel"]
    if (
        baseline["denominator"],
        baseline["ok"],
        baseline["synthesis_miss"],
        baseline["retrieval_miss"],
    ) != (154, 143, 9, 2):
        raise ValueError(f"baseline adjudicado fuera de contrato: {baseline}")

    # Certificaciones: ambas conversiones ESTABLES en sus artefactos congelados.
    if cert.get("status") != "GO" or not cert["b6f6_check"]["pass"]:
        raise ValueError("certificación det-only v2 de b6f6 no está en GO/pass")
    if set(cert["aggregate"]["stable_conversions"]) != set(BANKED):
        raise ValueError(
            f"stable_conversions de la cert v2 != banked: "
            f"{cert['aggregate']['stable_conversions']}"
        )
    if rescore.get("status") != "SECOND_CONVERSION" or not rescore["stable_conversion"]:
        raise ValueError("re-score de spec de 872c no certifica la conversión")
    if rescore["obligation_id"] != "obl_872c35fb41d7":
        raise ValueError("el re-score no es de obl_872c")

    # Partición: los 9 synth adjudicados = 2 banked + 7 restantes por clase.
    effects = adjudicated["adjudication_effects"]
    adjudicated_synth = set(effects["core_required_confirmed"]) | {
        effects["warning_block_merge"]["carrier"]
    } | set(effects["disclosure_respec"])
    remaining = {oid for ids in REMAINING_BY_CLASS.values() for oid in ids}
    if adjudicated_synth != remaining | set(BANKED) or remaining & set(BANKED):
        raise ValueError("la partición banked+restantes no reconstruye los 9 synth")
    if len(remaining) != 7:
        raise ValueError(f"esperaba 7 synth restantes, hay {len(remaining)}")

    ok = baseline["ok"] + len(BANKED)
    synth = baseline["synthesis_miss"] - len(BANKED)
    retrieval = baseline["retrieval_miss"]
    denominator = baseline["denominator"]
    if ok + synth + retrieval != denominator:
        raise ValueError("la aritmética del funnel banked no cierra")
    if (ok, synth, retrieval, denominator) != (145, 7, 2, 154):
        raise ValueError(
            f"proyección fuera de contrato: {ok}/{synth}/{retrieval}/{denominator}"
        )
    ok_pct = round(100.0 * ok / denominator, 2)
    required_ok = adjudicated["target"]["required_ok"]  # ceil(0.98 * 154) = 151
    if required_ok != 151:
        raise ValueError(f"required_ok inesperado: {required_ok}")

    return {
        "schema": "s272_banked_funnel_v1",
        "date": "2026-07-19",
        "dec": "DEC-131",
        "generated_by": "scripts/s272_bank_conversions.py",
        "authority": (
            "evals/s270_adjudicated_funnel_v1.json (DEC-125) + certificaciones s271 "
            "congeladas + recibos vivos query_logs (ventana ON de Alberto)"
        ),
        "inputs_sha256_lf_normalized": pins,
        "baseline_funnel": {
            **{k: baseline[k] for k in (
                "denominator", "ok", "synthesis_miss", "retrieval_miss", "ok_pct"
            )},
            "provenance": "DEC-125 (funnel adjudicado, s270)",
        },
        "production_flag": "MUST_PRESERVE_CONTRACT=on (Railway, confirmado por Alberto)",
        "mecanismo_verificado_en_produccion": "sí (query_logs 16:26Z)",
        "conversions_banked": [
            {
                "obligation_id": "obl_b6f6211be439",
                "qid": "hp002",
                "certificacion": (
                    "det-only v2 3/3 estable — evals/s271_probe_det_certification_v2.json"
                ),
                "estado_vivo": (
                    "FIRE EN VIVO ✓ — apéndice con el aviso de seguridad + checklist "
                    "servido en producción (recibo query_logs 2026-07-19T16:26Z)"
                ),
            },
            {
                "obligation_id": "obl_872c35fb41d7",
                "qid": "hp017",
                "certificacion": (
                    "re-score de spec opción-1 (DEC-128) 3/3 ON / 0/3 OFF — "
                    "evals/s271_872c_respec_rescore_v1.json; cert det-only v2 2/3 ≥ regla"
                ),
                "estado_vivo": (
                    "NO disparó en vivo (recibo 16:29Z, PEARL) — DIAGNOSTICADO: los "
                    "chunks del 997-671 p43-45 con la tabla de tipos quedan en "
                    "posiciones 22-33 del pool, FUERA del top-10 servido; el mecanismo "
                    "no puede anexar átomos de fragmentos no servidos. Clase: "
                    "composición-de-serving (retrieval-side), NO fallo del contrato. "
                    "La conversión se sostiene en la ruta harness congelada (donde esos "
                    "fragmentos SÍ se sirven); convergencia viva = lever retrieval de "
                    "la misma familia que Bloque B/C, sin acción ahora"
                ),
            },
        ],
        "control_sano_vivo": (
            "CAD-250 (recibo 16:34Z): SIN apéndice — silencio correcto en vivo ✓"
        ),
        "live_receipts": receipts,
        "banked_funnel": {
            "denominator": denominator,
            "ok": ok,
            "synthesis_miss": synth,
            "retrieval_miss": retrieval,
            "ok_pct": ok_pct,
        },
        "remaining_synthesis_miss_by_class": REMAINING_BY_CLASS,
        "facts_moved_to_ok": len(BANKED),
        "facts_moved_note": (
            "Banking oficial de las 2 conversiones certificadas del contrato "
            "must-preserve (DEC-127/128/129/130): crédito respaldado por replays "
            "det-only congelados + mecanismo verificado en producción (b6f6 vivo; "
            "872c harness-only con alcance declarado)."
        ),
        "official_atomic_kpi": None,
        "official_atomic_kpi_note": (
            "Los 77 legacy carries siguen (S205); sin KPI atómico oficial hasta cerrarlos."
        ),
        "target": {
            "declared": "98% de 154 = 151 → +6",
            "target_pct": 0.98,
            "required_ok": required_ok,
            "conversions_needed": required_ok - ok,
        },
    }


def fetch_receipts() -> int:
    """GET-only a query_logs (Supabase REST) → evals/s272_live_receipts_v1.json.
    Se niega a sobrescribir un recibo ya versionado (el pin manda)."""
    if RECEIPTS.exists():
        print(f"{RECEIPTS.relative_to(ROOT)} ya existe — no se sobrescribe (pin).")
        return 1
    import httpx

    from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

    params = {
        "select": "query,response,created_at",
        "created_at": "gte.2026-07-19T00:00:00",
        "order": "created_at.asc",
    }
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/query_logs", headers=headers, params=params
        )
        resp.raise_for_status()
        rows = resp.json()
    labels = ["b6f6_live_fire_asd535", "872c_no_fire_pearl", "control_sano_cad250"]
    if len(rows) != len(labels):
        raise ValueError(f"esperaba {len(labels)} filas vivas, hay {len(rows)}")
    receipts = [
        {
            "label": label,
            "created_at": row["created_at"],
            "query": row["query"],
            "response": row["response"],
            "response_sha256": hashlib.sha256(
                row["response"].encode("utf-8")
            ).hexdigest(),
            "appendix_present": APPENDIX_MARKER in row["response"],
        }
        for label, row in zip(labels, rows)
    ]
    write_json(RECEIPTS, {
        "schema": "s272_live_receipts_v1",
        "date": "2026-07-19",
        "source": (
            "query_logs (Supabase REST, GET-only; "
            "scripts/s272_bank_conversions.py --fetch-receipts)"
        ),
        "nota": (
            "Recibos vivos de la ventana MUST_PRESERVE_CONTRACT=on en Railway (Alberto "
            "disparó las 3 preguntas). SIN datos personales: solo query/response/"
            "created_at. La columna response trunca a 4096 chars "
            "(logging_db._RESPONSE_MAX_CHARS)."
        ),
        "receipts": receipts,
    })
    print(f"escrito: {RECEIPTS.relative_to(ROOT)} — actualiza el pin en este script.")
    return 0


def main() -> int:
    if "--fetch-receipts" in sys.argv[1:]:
        return fetch_receipts()
    report = build_projection()
    write_json(OUTPUT, report)
    funnel = report["banked_funnel"]
    print(
        f"OK {funnel['ok']} / synth {funnel['synthesis_miss']} / retr "
        f"{funnel['retrieval_miss']} / den {funnel['denominator']} "
        f"({funnel['ok_pct']}%) -- objetivo 98% de 154 = "
        f"{report['target']['required_ok']} -> +{report['target']['conversions_needed']}"
    )
    print(f"escrito: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
