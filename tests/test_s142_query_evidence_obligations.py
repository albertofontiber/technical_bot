from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from src.rag.query_evidence_obligations import extract_query_evidence_obligations


ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "evals" / "s114_procedure_bundle_heldout_freeze_v1.json"

# This development set was opened only after S141 v1's independent gate. The
# runtime extractor contains none of these literals. Item 9 is excluded because
# its source is Russian-only while the question is Spanish.
DEV_SUPPORT = {
    1: ("Flow Fault Delay", "umbral y el retraso se utilizan"),
    2: ("parpadeará una vez por segundo hasta que se confirme",),
    3: ("Press F3 again to restart", "automatically reverts"),
    4: ("3,9 kΩ", "0 Ω"),
    5: ("solo se puede configurar mediante la aplicación de software Remote",),
    6: ("duplicate addresses have not been assigned",),
    7: ("0-20mA", "Determine las salidas"),
    8: ("Use Table 23",),
    10: ("ZONA DE INICIACIÓN (+)",),
    11: ("también se monitorizará cuando alguno",),
    12: ("DAM_PA_SRC_IN_VA_CUT_THRESHOLD",),
    13: ("Guardar | F1", "Aplicar | F1"),
    14: ("Módulo 2º com.",),
    15: ("Hold a suitable magnet",),
    16: ("Communication between the module",),
    17: ("Transmission to ARC with the KIT-FB-25",),
    18: ("Пожарный сигнал",),
    19: ("calibración periódica sólo la puede realizar",),
    20: ("deben conectarse en serie",),
    21: ("volume control potentiometer",),
    22: ("Tone 1 | Continuous 340Hz",),
    23: ("DELAYED from 1 to 30 minutes",),
    24: ("Con uscita di guasto",),
}


def _payload() -> dict:
    return json.loads(DEV.read_text(encoding="utf-8"))


def _normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).casefold()
    return re.sub(r"[\\\s|]+", "", folded)


def test_source_first_development_support_is_covered_28_of_28_with_three_records():
    payload = _payload()
    covered = 0
    total = 0
    for one_based_index, quotes in DEV_SUPPORT.items():
        selected = payload["chosen"][one_based_index - 1]
        chunk = payload["source_rows"][selected["chunk_id"]]
        rows = extract_query_evidence_obligations(
            selected["question"], [(1, chunk)], max_candidates=3
        )
        assert len(rows) <= 3
        raw_spans = [
            _normalized(chunk["content"][row.source_start : row.source_end])
            for row in rows
        ]
        for quote in quotes:
            total += 1
            matched = any(_normalized(quote) in span for span in raw_spans)
            covered += int(matched)
            assert matched, (one_based_index, quote)
    assert (covered, total) == (28, 28)


def test_every_candidate_is_an_exact_bounded_source_span_and_is_deterministic():
    payload = _payload()
    for one_based_index in DEV_SUPPORT:
        selected = payload["chosen"][one_based_index - 1]
        chunk = payload["source_rows"][selected["chunk_id"]]
        aligned = [(1, chunk)]
        first = extract_query_evidence_obligations(
            selected["question"], aligned, max_candidates=3
        )
        second = extract_query_evidence_obligations(
            selected["question"], aligned, max_candidates=3
        )
        assert first == second
        for row in first:
            assert row.candidate_id == chunk["id"]
            assert 0 <= row.source_start < row.source_end <= len(chunk["content"])
            assert chunk["content"][row.source_start : row.source_end].strip()


def test_unrelated_or_content_free_queries_fail_closed():
    aligned = [
        (
            1,
            {
                "id": "manual-a",
                "content": "The control panel enclosure is red and weighs 3 kg.",
                "section_title": "Mechanical data",
            },
        )
    ]
    assert extract_query_evidence_obligations("Hola", aligned) == []
    assert extract_query_evidence_obligations("¿Cuál es el precio?", aligned) == []
    assert extract_query_evidence_obligations(
        "¿Cómo se rearma la central después de una alarma?", aligned
    ) == []


def test_runtime_module_contains_no_development_or_product_literals():
    runtime = (ROOT / "src" / "rag" / "query_evidence_obligations.py").read_text(
        encoding="utf-8"
    ).casefold()
    forbidden = {
        "vesda-e",
        "iu2055nc",
        "sg100-is",
        "fhds8310",
        "modulaser",
        "sensitron",
        "spectrex",
        "xtralis",
        "cat018",
        "hp017",
    }
    assert not {term for term in forbidden if term in runtime}
