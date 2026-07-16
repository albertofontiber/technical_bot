#!/usr/bin/env python3
"""Read-only corpus audit for technical-notation fidelity and five partial facts.

The audit intentionally does not claim that a suspicious extracted token is
wrong.  It identifies rows that need a pixel/source check and records the exact
scope in which the five S113 partial-evidence facts were searched.  Only a
minimal projection of ``chunks_v2`` is downloaded; no model or database write
is used.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals/s114_extraction_fidelity_audit_v1.json"
TRIAGE_OUT = ROOT / "evals/s114_partial_evidence_search_v1.json"

SELECT = (
    "id,content,context,source_file,page_number,section_title,product_model,"
    "manufacturer,document_id,extraction_sha256,has_diagram,diagram_url,created_at"
)
PAGE_SIZE = 1000
MAX_SAMPLES = 30

_EXPLICIT_POWER = re.compile(
    r"(?:\d+\s*\^\s*[+\-]?\d+|\d+[\u00b2\u00b3\u00b9\u2070\u2074-\u2079]+|"
    r"<sup>\s*[+\-]?\d+\s*</sup>)",
    re.I,
)
_COLLAPSED_POWER_RELATION = re.compile(
    r"(?:life(?:time)?|service\s+life|contact(?:s)?|vida\s+[uú]til|contactos?)"
    r"[^\n]{0,180}(?<!\d)10[2-9](?!\d)[^\n]{0,100}"
    r"(?:operation(?:s)?|cycle(?:s)?|operaciones?|ciclos?|maniobras?)|"
    r"(?:operation(?:s)?|cycle(?:s)?|operaciones?|ciclos?|maniobras?)"
    r"[^\n]{0,100}(?<!\d)10[2-9](?!\d)[^\n]{0,180}"
    r"(?:life(?:time)?|service\s+life|contact(?:s)?|vida\s+[uú]til|contactos?)",
    re.I,
)
_SPLIT_UNIT_CELL = re.compile(
    r"(?<!\d)[+\-]?\d+(?:[.,]\d+)?\s*\|\s*"
    r"(?:k?ohm|[kmun]?[avw]|hz|sec|seg|min|bar|pa|db)\b",
    re.I,
)
_RICH_GLYPH = re.compile(r"[±≤≥ΩΩµμ°Δ×÷]")
_MOJIBAKE = re.compile(r"(?:Ã.|Â.|â(?:€|‰|ˆ|€™|€œ|€|€“|€”))")


TARGETS = {
    "cat017": {
        "fact_key": "cat017#2:licencia CLIP por lazo",
        "scope": lambda row: "inspire" in norm(row.get("product_model"))
        or "hop138" in norm(row.get("source_file")),
        "signals": {
            "clip": re.compile(r"\bclip\b", re.I),
            "licence": re.compile(r"licen[cs]", re.I),
            "loop": re.compile(r"\b(?:lazo|loop)\w*\b", re.I),
            "per_loop_quantifier": re.compile(
                r"\b(?:una?\s+licencia\s+para\s+)?cada\s+(?:circuito\s+de\s+)?lazo\b|"
                r"\bpor\s+(?:el\s+)?(?:circuito\s+de\s+)?lazo\b|"
                r"\b(?:each|per)\s+(?:loop\s+circuit|loop)\b",
                re.I,
            ),
        },
    },
    "hp002": {
        "fact_key": "hp002#3:7.6.1",
        "scope": lambda row: "asd535" in norm(row.get("product_model"))
        or "asd535" in norm(row.get("source_file")),
        "signals": {
            "v01": re.compile(r"(?<![a-z0-9])v[\s._-]*0?1(?!\d)", re.I),
            "v02": re.compile(r"(?<![a-z0-9])v[\s._-]*0?2(?!\d)", re.I),
            "airflow": re.compile(r"flujo\s+de\s+aire|air\s*flow", re.I),
            "threshold_direction": re.compile(
                r"(?:debajo|inferior|below).{0,60}100\s*%|"
                r"(?:encima|superior|above).{0,60}100\s*%",
                re.I | re.S,
            ),
        },
    },
    "hp010": {
        "fact_key": "hp010#1:Nivel 3",
        "scope": lambda row: norm(row.get("product_model")) == "dxc"
        or norm(row.get("source_file")).startswith("dxc"),
        "signals": {
            "autosearch": re.compile(r"auto[\s-]*b[uú]squeda|autosearch", re.I),
            "level3": re.compile(r"nivel\s*3|level\s*3", re.I),
            "memory_unlock": re.compile(
                r"desbloq\w*.{0,40}memoria|memoria.{0,40}desbloq\w*|"
                r"unlock\w*.{0,40}memory|memory.{0,40}unlock\w*",
                re.I | re.S,
            ),
        },
    },
    "hp013": {
        "fact_key": "hp013#1:PWR-R",
        "scope": lambda row: "adw535" in norm(row.get("product_model"))
        or "adw535" in norm(row.get("source_file")),
        "signals": {
            "pwr_r": re.compile(r"\bpwr[\s-]*r\b", re.I),
            "rtc_lithium": re.compile(
                r"(?:bater[ií]a|battery).{0,50}(?:litio|lithium|rtc)|"
                r"(?:litio|lithium|rtc).{0,50}(?:bater[ií]a|battery)",
                re.I | re.S,
            ),
            "input_voltage": re.compile(
                r"(?:tensi[oó]n|voltaje|voltage).{0,60}(?:entrada|input)|"
                r"(?:entrada|input).{0,60}(?:tensi[oó]n|voltaje|voltage)|"
                r"(?<!\d)\d+(?:[.,]\d+)?\s*v(?:dc|ac)?\b",
                re.I | re.S,
            ),
            "buffer": re.compile(r"\b(?:buffer|respaldo|backup|tamp[oó]n)\w*\b", re.I),
            "eeprom": re.compile(r"\beeprom\b", re.I),
        },
    },
    "hp015": {
        "fact_key": "hp015#2:32",
        "scope": lambda row: "ccd103" in norm(row.get("product_model"))
        or "ccd103" in norm(row.get("source_file")),
        "signals": {
            "disable": re.compile(r"desconexi[oó]n|deshabilit\w*|disable\w*|isolat\w*", re.I),
            "individual": re.compile(r"individual|detector|dispositivo|device", re.I),
            "zone": re.compile(r"\bzona\w*\b|\bzone\w*\b", re.I),
            "capacity32": re.compile(r"(?<!\d)32(?!\d)", re.I),
            "explicit_impossibility": re.compile(
                r"no\s+se\s+(?:puede|permite).{0,60}(?:desconect|deshabilit|aisl)\w*.{0,60}"
                r"(?:individual|detector|dispositivo)|"
                r"(?:cannot|can['’]?t|impossible).{0,60}(?:disable|isolate)\w*.{0,60}"
                r"(?:individual|detector|device)|"
                r"(?:individual|detector|dispositivo|device).{0,60}"
                r"(?:no\s+se\s+(?:puede|permite)|cannot|can['’]?t|impossible).{0,60}"
                r"(?:desconect|deshabilit|aisl|disable|isolate)\w*",
                re.I | re.S,
            ),
        },
    },
}

REQUIRED_SIGNAL_BUNDLES = {
    "cat017": {"clip", "licence", "loop", "per_loop_quantifier"},
    "hp002": {"v01", "v02", "airflow", "threshold_direction"},
    "hp010": {"autosearch", "level3", "memory_unlock"},
    "hp013": {"pwr_r", "rtc_lithium", "input_voltage", "buffer"},
    "hp015": {"disable", "individual", "zone", "capacity32", "explicit_impossibility"},
}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def excerpt(text: str, match: re.Match[str] | None = None, width: int = 360) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= width:
        return clean
    center = match.start() if match else 0
    start = max(0, center - width // 3)
    end = min(len(clean), start + width)
    return clean[start:end]


def notation_signals(row: dict) -> list[tuple[str, re.Match[str] | None]]:
    text = row.get("content") or ""
    out: list[tuple[str, re.Match[str] | None]] = []
    for name, pattern in (
        ("explicit_scientific_notation", _EXPLICIT_POWER),
        ("split_numeric_unit_cell", _SPLIT_UNIT_CELL),
        ("rich_technical_glyph", _RICH_GLYPH),
        ("unicode_replacement_character", re.compile("\ufffd")),
        ("mojibake_sequence", _MOJIBAKE),
    ):
        match = pattern.search(text)
        if match:
            out.append((name, match))
    collapsed_relation = _COLLAPSED_POWER_RELATION.search(text)
    if collapsed_relation:
        out.append(("collapsed_power_candidate", collapsed_relation))
    if (
        row.get("has_diagram")
        and not row.get("diagram_url")
        and re.search(r"\d", text)
        and ("|" in text or re.search(r"table|tabla|figure|figura", text, re.I))
    ):
        out.append(("numeric_page_image_without_render_receipt", None))
    return out


def target_matches(row: dict, target: dict) -> dict[str, re.Match[str]]:
    if not target["scope"](row):
        return {}
    text = target_search_text(row)
    return {
        name: match
        for name, pattern in target["signals"].items()
        if (match := pattern.search(text))
    }


def target_matches_by_field(row: dict, target: dict) -> dict[str, dict[str, re.Match[str]]]:
    if not target["scope"](row):
        return {}
    return {
        field: {
            name: match
            for name, pattern in target["signals"].items()
            if (match := pattern.search(str(row.get(field) or "")))
        }
        for field in ("content", "context", "section_title")
    }


def target_search_text(row: dict) -> str:
    return "\n".join(
        str(row.get(field) or "")
        for field in ("section_title", "context", "content")
    )


def keep_best_receipt(receipts: list[dict], receipt: dict, limit: int = MAX_SAMPLES) -> None:
    receipts.append(receipt)
    receipts.sort(
        key=lambda item: (
            -len(item.get("content_signals") or []),
            -len(item.get("signals") or []),
            str(item.get("source_file") or ""),
            int(item.get("page_number") or -1),
            str(item.get("id") or ""),
        )
    )
    del receipts[limit:]


def iter_rows(url: str, key: str, page_size: int = PAGE_SIZE):
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    offset = 0
    with httpx.Client(timeout=60.0) as client:
        while True:
            response = client.get(
                f"{url.rstrip('/')}/rest/v1/chunks_v2",
                headers=headers,
                params={
                    "select": SELECT,
                    "order": "id.asc",
                    "limit": str(page_size),
                    "offset": str(offset),
                },
            )
            response.raise_for_status()
            rows = response.json()
            yield rows
            if len(rows) < page_size:
                break
            offset += len(rows)


def row_receipt(row: dict, match: re.Match[str] | None = None) -> dict:
    return {
        "id": row.get("id"),
        "manufacturer": row.get("manufacturer"),
        "product_model": row.get("product_model"),
        "source_file": row.get("source_file"),
        "page_number": row.get("page_number"),
        "section_title": row.get("section_title"),
        "has_diagram": bool(row.get("has_diagram")),
        "diagram_url_present": bool(row.get("diagram_url")),
        "excerpt": excerpt(row.get("content") or "", match),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE)
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_KEY missing")

    total = 0
    pages = 0
    documents: set[str] = set()
    sources: set[str] = set()
    manufacturers: set[str] = set()
    max_created_at = ""
    signal_counts: Counter[str] = Counter()
    signal_sources: dict[str, set[str]] = defaultdict(set)
    signal_manufacturers: dict[str, set[str]] = defaultdict(set)
    samples: dict[str, list[dict]] = defaultdict(list)
    target_scope_counts: Counter[str] = Counter()
    target_signal_counts: dict[str, Counter[str]] = defaultdict(Counter)
    target_context_signal_counts: dict[str, Counter[str]] = defaultdict(Counter)
    target_section_signal_counts: dict[str, Counter[str]] = defaultdict(Counter)
    target_combination_counts: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    target_complete_bundle_counts: Counter[str] = Counter()
    target_rows: dict[str, list[dict]] = defaultdict(list)

    for batch in iter_rows(url, key, args.page_size):
        pages += 1
        for row in batch:
            total += 1
            if row.get("document_id"):
                documents.add(str(row["document_id"]))
            if row.get("source_file"):
                sources.add(str(row["source_file"]))
            if row.get("manufacturer"):
                manufacturers.add(str(row["manufacturer"]))
            max_created_at = max(max_created_at, str(row.get("created_at") or ""))

            for name, match in notation_signals(row):
                signal_counts[name] += 1
                signal_sources[name].add(str(row.get("source_file") or ""))
                signal_manufacturers[name].add(str(row.get("manufacturer") or ""))
                if len(samples[name]) < MAX_SAMPLES:
                    samples[name].append(row_receipt(row, match))

            for qid, target in TARGETS.items():
                if target["scope"](row):
                    target_scope_counts[qid] += 1
                matches_by_field = target_matches_by_field(row, target)
                if not matches_by_field:
                    continue
                content_matches = matches_by_field["content"]
                context_matches = matches_by_field["context"]
                section_matches = matches_by_field["section_title"]
                all_names = set(content_matches) | set(context_matches) | set(section_matches)
                if not all_names:
                    continue
                target_signal_counts[qid].update(content_matches.keys())
                target_context_signal_counts[qid].update(context_matches.keys())
                target_section_signal_counts[qid].update(section_matches.keys())
                combination = tuple(sorted(content_matches))
                target_combination_counts[qid][combination] += 1
                if REQUIRED_SIGNAL_BUNDLES[qid] <= set(content_matches):
                    target_complete_bundle_counts[qid] += 1
                receipt = row_receipt(row)
                receipt["signals"] = sorted(all_names)
                receipt["content_signals"] = sorted(content_matches)
                receipt["retrieval_context_signals"] = sorted(context_matches)
                receipt["section_title_signals"] = sorted(section_matches)
                receipt["content_signal_excerpts"] = {
                    name: excerpt(str(row.get("content") or ""), match, width=520)
                    for name, match in sorted(content_matches.items())
                }
                if content_matches:
                    evidence_text = str(row.get("content") or "")
                    first_match = min(content_matches.values(), key=lambda match: match.start())
                    receipt["excerpt_source"] = "content"
                elif context_matches:
                    evidence_text = str(row.get("context") or "")
                    first_match = min(context_matches.values(), key=lambda match: match.start())
                    receipt["excerpt_source"] = "retrieval_context_not_evidence"
                else:
                    evidence_text = str(row.get("section_title") or "")
                    first_match = min(section_matches.values(), key=lambda match: match.start())
                    receipt["excerpt_source"] = "section_title"
                receipt["excerpt"] = excerpt(evidence_text, first_match)
                keep_best_receipt(target_rows[qid], receipt)

    audit = {
        "instrument": "s114_extraction_fidelity_audit_v1",
        "status": "candidate_risk_audit_not_source_pixel_verdict",
        "corpus_snapshot": {
            "table": "chunks_v2",
            "rows": total,
            "documents": len(documents),
            "source_files": len(sources),
            "manufacturers": len(manufacturers),
            "max_created_at": max_created_at,
        },
        "signals": {
            name: {
                "rows": count,
                "source_files": len(signal_sources[name] - {""}),
                "manufacturers": len(signal_manufacturers[name] - {""}),
                "samples": samples[name],
            }
            for name, count in sorted(signal_counts.items())
        },
        "cost_receipt": {
            "database_get_requests": pages,
            "database_writes": 0,
            "embedding_calls": 0,
            "reranker_calls": 0,
            "generator_calls": 0,
            "judge_calls": 0,
        },
        "limitations": [
            "A suspicious token is a source-pixel review candidate, not proof of extraction error.",
            "The audit cannot detect a lost glyph when the flattened value lacks a technical context cue.",
            "A missing diagram_url is a missing render receipt, not proof that extracted prose is wrong.",
        ],
    }
    triage = {
        "instrument": "s114_partial_evidence_search_v1",
        "status": "deterministic_full_corpus_search_pending_adjudication",
        "corpus_snapshot": audit["corpus_snapshot"],
        "rows": [
            {
                "qid": qid,
                "fact_key": target["fact_key"],
                "scope_rows": target_scope_counts[qid],
                "content_signal_counts": dict(sorted(target_signal_counts[qid].items())),
                "retrieval_context_signal_counts": dict(
                    sorted(target_context_signal_counts[qid].items())
                ),
                "section_title_signal_counts": dict(
                    sorted(target_section_signal_counts[qid].items())
                ),
                "required_signal_bundle": sorted(REQUIRED_SIGNAL_BUNDLES[qid]),
                "complete_bundle_rows": target_complete_bundle_counts[qid],
                "signal_combinations": [
                    {"signals": list(signals), "rows": count}
                    for signals, count in sorted(
                        target_combination_counts[qid].items(),
                        key=lambda item: (-len(item[0]), item[0]),
                    )
                ],
                "candidate_rows": target_rows[qid],
            }
            for qid, target in TARGETS.items()
        ],
        "cost_receipt": audit["cost_receipt"],
        "limitations": [
            "Regex search establishes lexical presence only; relation and entailment require adjudication.",
            "Only content_signal_counts are source evidence; retrieval-context text is reported separately and cannot support an answer.",
            "Absence of a term in extracted chunks cannot by itself prove absence from source pixels.",
        ],
    }
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    TRIAGE_OUT.write_text(
        json.dumps(triage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "corpus_snapshot": audit["corpus_snapshot"],
        "signal_counts": dict(signal_counts),
        "target_scope_counts": dict(target_scope_counts),
        "target_content_signal_counts": {
            qid: dict(counts) for qid, counts in target_signal_counts.items()
        },
        "cost_receipt": audit["cost_receipt"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
