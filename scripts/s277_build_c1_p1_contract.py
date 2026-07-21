#!/usr/bin/env python3
"""Build the offline-only S277 C1 P1 contract and preregistration.

This builder is deliberately data-only: it reads frozen repository artifacts,
performs no network access and never imports production configuration (which
could read an implicit .env).  It exists so the 43-row packet cannot silently
drift away from the historical S118 indexing contract.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
FACT_KEY = re.compile(r"^(?P<qid>[^#]+)#(?P<index>[0-9]+):(?P<value>.*)$")
QIDS = [
    "cat001", "cat017", "cat018", "cat019", "hp002", "hp003", "hp005",
    "hp011", "hp012", "hp013", "hp014", "hp017", "hp018",
]
EXPECTED_MODELS = {
    "cat001": ["Pearl"],
    "cat017": ["INSPIRE"],
    "cat018": ["AM-8200"],
    "cat019": ["CAD-250"],
    "hp002": ["ASD535"],
    "hp003": ["CAD-150"],
    "hp005": ["ID3000"],
    "hp011": ["RP1r"],
    "hp012": ["AM-2020", "AFP1010"],
    "hp013": ["ADW535"],
    "hp014": ["ID2000"],
    "hp017": ["Pearl"],
    "hp018": ["ZXE"],
}
REPLICA_ORDER = [
    "hp017:r1", "hp017:r2", "hp017:r3",
    "cat001:r1", "cat001:r2", "cat017:r1", "cat017:r2",
    "cat018:r1", "cat018:r2", "cat019:r1", "cat019:r2",
    "hp002:r1", "hp002:r2", "hp003:r1", "hp003:r2",
    "hp005:r1", "hp005:r2", "hp011:r1", "hp011:r2",
    "hp012:r1", "hp012:r2", "hp013:r1", "hp013:r2",
    "hp014:r1", "hp014:r2", "hp018:r1", "hp018:r2",
]
EXPECTED_COUNTS = {
    "cat001": 5, "cat017": 4, "cat018": 1, "cat019": 4, "hp002": 4,
    "hp003": 4, "hp005": 4, "hp011": 1, "hp012": 4, "hp013": 0,
    "hp014": 4, "hp017": 3, "hp018": 5,
}

SNAPSHOT_MAX_AGE_SECONDS = 1800
SNAPSHOT_FUTURE_SKEW_SECONDS = 60
SEMANTIC_ENV_CONSTS = {
    "CHUNKS_TABLE": "chunks_v2",
    "ENUNCIADOS_MULTIVECTOR": "on",
    "HYQ_TABLE": "on",
    "HYQ_PILOT_FILE": "",
    "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "add",
    "GENERATOR_SELECTION_BLOCK": "on",
    "GENERATOR_PROMPT_VARIANT": "fidelity",
    "HYDE_ENABLED": "false",
    "RERANK_TOP_K": "10",
    "LLM_MAX_TOKENS": "3500",
    "MUST_PRESERVE_CONTRACT": "on",
}
SEMANTIC_DEFAULT_ENV_CONSTS = {
    "RERANKER_BACKEND": "llm",
    "MERGE_STRATEGY": "stamps",
    "RERANK_PREVIEW_CHARS": "800",
    "DIVERSIFY_TIEBREAK": "off",
}
TARGET_OFF_ENV_FLAGS = (
    "TABLE_PREAMBLE_CLOSURE",
    "CANONICAL_HYQ_COVERAGE",
    "COMPATIBILITY_BUNDLE_COVERAGE",
    "RERANK_POOL_COVERAGE",
    "STRUCTURAL_CASCADE_COVERAGE",
    "LOGICAL_RECORD_COVERAGE",
    "EVIDENCE_DERIVATION_OVERLAY",
    "DEDUP_REFERENCE_NAVIGATION",
    "R2_REPAIR_NAVIGATION",
    "STRUCTURAL_NEIGHBOR_SHADOW",
    "MP_HYBRID_DETECT",
    "MP_SERVED_BINDING",
    "MP_DEFLINE_EQ",
    "MP_STEM_BINDING",
    "MP_DISTINCTIVE_TOKEN",
)

# Every inner list is OR; all outer groups are AND.  A deterministic positive
# still needs a valid local citation.  Missing/ambiguous language is REVIEW,
# never a bag-of-words FAIL/PASS shortcut.
SURFACES: dict[str, list[list[str]]] = {
    "cat001#0:159+159 / 99+99": [["159 sensores", "159 detectores"], ["159 modulos"], ["99 sensores", "99 detectores"], ["99 modulos"]],
    "cat001#1:0,75 A": [["carga maxima", "corriente maxima", "capacidad maxima"], ["lazo"], ["0,75 a", "0.75 a"]],
    "cat001#2:40": [["lazo mixto", "mixto opal clip", "opal clip"], ["40"], ["solo con protocolo clip", "solo clip"]],
    "cat001#4:autoconfiguracion": [["autoconfiguracion", "auto configuracion"], ["alta de equipos", "dar de alta", "detecta los tipos", "detecta equipos"]],
    "cat001#5:255 / 8192": [["255"], ["8192"], ["zona"]],
    "cat017#0:modulo OPAL HOP-433-100": [["hop 433 100"], ["lazo 1"], ["lazo 2"]],
    "cat017#1:159 + 159": [["159 detectores"], ["159 modulos"], ["99 detectores", "99 sensores"], ["99 modulos"], ["no se permite mezclar", "no mezclar"]],
    "cat017#3:Auto Configuracion": [["auto configuracion", "autoconfiguracion"], ["alta", "detecta automaticamente", "detecta los dispositivos", "deteccion automatica"]],
    "cat017#4:CLSS": [["clss"], ["sitio", "site"], ["bin", "licencia"]],
    "cat018#0:Control By Events": [["control by events", "cbe"], ["activa un comando", "activar un comando"], ["evento"]],
    "cat019#0:coincidencias": [["maniobra"], ["anadir", "añadir"], ["coincidencias"]],
    "cat019#1:EVENTO / ACCION": [["evento"], ["accion", "acción"]],
    "cat019#2:ENTIDAD / CONDICION TEMPORAL": [["entidad"], ["condicion temporal", "condición temporal"]],
    "cat019#3:salidas": [["accion", "acción", "salida"], ["sirenas"], ["modulos de control", "módulos de control"]],
    "hp002#0:fallo flujo de aire": [["fallo flujo de aire", "fallo de flujo de aire"], ["20", "80"]],
    "hp002#1:80 %": [["80"], ["obstruccion", "obstrucción"], ["120", "rotura"]],
    "hp002#2:300 s": [["300 s", "300 segundos"], ["retardo"], ["fallo flujo de aire", "fallo de flujo de aire"]],
    "hp003#0:12V": [["dos baterias", "2 baterias", "dos baterías", "2 baterías"], ["12 v", "12v"], ["serie"]],
    "hp003#1:cable puente": [["cable puente"], ["positivo"], ["negativo"], ["dos baterias", "2 baterias", "dos baterías", "2 baterías"], ["serie"]],
    "hp003#2:rojo y negro": [["rojo"], ["negro"], ["positivo"], ["negativo"]],
    "hp003#3:primero la red": [["primero"], ["red", "230 vac", "230vac"], ["despues las baterias", "después las baterías"]],
    "hp005#0:Matriz de control": [["matriz de control"], ["instruccion", "instrucción", "configura"], ["entrada"], ["alarma"], ["zona"]],
    "hp005#1:COINCIDENCIA 2 EQUIPOS": [["coincidencia 2 equipos", "coincidencia de 2 equipos", "coincidencia dos equipos"]],
    "hp005#2:misma zona o subzona": [["misma zona", "misma subzona", "zona o subzona"]],
    "hp005#3:CIRCUITO SIRENA": [["circuito sirena", "circuito de sirena"], ["salida"]],
    "hp011#1:r.I": [["rearme inhibido", "inhibicion del rearme", "inhibición del rearme"], ["--", "guiones"], ["00"], ["01", "1 minuto"], ["30", "30 minutos"], ["t.a", "duracion de la descarga", "duración de la descarga"]],
    "hp012#0:10 lazos": [["am2020", "am 2020"], ["10 lazos"]],
    "hp012#1:99 + 99": [["99 detectores"], ["99 modulos", "99 módulos"], ["por lazo", "cada lazo"]],
    "hp012#2:2 lazos / 396": [["afp1010", "afp 1010"], ["espana", "españa", "mfdt280", "mpdt280"], ["2 lazos", "dos lazos"], ["396"]],
    "hp012#3:4 lazos / 792": [["afp1010", "afp 1010"], ["us", "ee uu", "15088sp"], ["4 lazos", "cuatro lazos"], ["792"]],
    "hp014#0:25": [["25 equipos"], ["aisladores"]],
    "hp014#1:continuidad": [["continuidad"], ["antes"], ["aisladores"]],
    "hp014#2:terminales 2 y 4": [["terminales 2 y 4", "terminal 2 y 4"], ["cortocircuit", "puente"]],
    "hp014#3:35": [["35 ohm", "35 ω"], ["tierra"], ["panel"]],
    "hp017#0:causa-efecto": [["causa efecto", "causa-efecto"], ["retardo"], ["regla"]],
    "hp017#2:Editar Configuracion": [["editar configuracion", "editar configuración"], ["causa y efecto", "causa-efecto"], ["regla 1"], ["borrar", "eliminar"], ["cualquier entrada de alarma"], ["todos los equipos de salida", "todas las sirenas"]],
    "hp017#3:disclosure_DEC128": [["seis tipos de retardo", "6 tipos de retardo"], ["fijo"], ["estandar", "estándar"], ["no silenc"], ["est ext", "est. ext"], ["retextstd"], ["no sil ext", "no sil. ext"], ["sinretext"], ["discrepancia", "no coincide", "difiere", "discrepan", "tambien indica", "también indica"]],
    "hp018#0:4 circuitos": [["zx2e"], ["2 circuitos", "dos circuitos"], ["zx5e"], ["4 circuitos", "cuatro circuitos"]],
    "hp018#1:6K8": [["6k8", "6,8 k", "6.8 k"], ["0,5 w", "0.5 w"], ["final de linea", "fin de linea", "rfl"]],
    "hp018#2:diodo": [["diodo"], ["polarizacion inversa", "polarización inversa"]],
    "hp018#3:Sirenas A,B,C,D": [["sirena a", "sirenas a"], ["sirena b", "sirenas a y b"], ["sirena c", "a b c d"], ["sirena d", "a b c d"]],
    "hp018#4:1 A": [["1 a", "1 amp", "un amperio"], ["circuito", "salida"]],
    "hp002#banked:obl_b6f6211be439": [["controles de incendios"], ["alertas remotas"], ["zonas de extincion", "zonas de extinción"], ["bloquearlos o desconectarlos previamente", "bloquear o desconectar previamente"]],
}

FORBIDDEN: dict[str, list[str]] = {
    "hp011#1:r.I": ["t.fi"],
    "hp018#0:4 circuitos": ["zx5e dispone de 5", "zx5e tiene 5"],
    "hp018#1:6K8": ["10 kohm", "10 kω", "10kω"],
    "hp018#4:1 A": ["500 ma max", "500 ma máximo"],
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def normalized_sha256(value: str) -> str:
    return hashlib.sha256(normalized_text(value).encode("utf-8")).hexdigest()


def sha256_lf_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def file_receipt(relative: str) -> dict[str, str]:
    raw = (ROOT / relative).read_bytes()
    return {
        "path": relative,
        "sha256_lf": sha256_lf_bytes(raw),
    }


def load_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load_yaml(relative: str) -> Any:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def historical_core_facts(gold: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        fact for fact in gold.get("atomic_facts", [])
        if isinstance(fact, dict) and fact.get("tipo") == "core" and fact.get("estado") == "presente"
    ]


def question_gold_source_refs(gold: dict[str, Any]) -> list[dict[str, Any]]:
    """Return question-level evidence only for guards without atomic facts.

    Protected facts must use :func:`fact_source_refs`; attaching every citation
    in a question to every fact would let an unrelated page satisfy the local
    citation requirement.
    """
    refs = []
    for citation in gold.get("citations", []):
        quote = normalized_text(str(citation.get("quote", "")))
        refs.append({
            "binding_level": "gold_verified_page",
            "chunk_id": None,
            "document_id": None,
            "source_file": citation["manual"],
            "page": citation["page"],
            "product_model": None,
            "manufacturer": None,
            "quote_text": quote or None,
            "quote_sha256": normalized_sha256(quote) if quote else None,
            "authority": "evals/gold_answers_v1.yaml._provenance",
        })
    if not refs:
        raise ValueError(f"gold qid has no verified citations: {gold.get('qid')}")
    return refs


MANUAL_ALIASES: tuple[tuple[str, str], ...] = (
    ("997-671-005-3", "997-671-005-3"),
    ("997-669", "997-669"),
    ("997-671", "997-671"),
    ("HOP-138-9", "HOP-138-9"),
    ("HOP-138-8", "HOP-138-8"),
    ("AM-8200-manu-prog", "AM-8200-manu-prog"),
    ("MC-380", "CAD-250-MC-380"),
    ("MPDT190", "MPDT190"),
    ("MCDT191", "MCDT191"),
    ("MPDT280", "MPDT280"),
    ("MFDT280", "MFDT280"),
    ("15088SP", "15088SP"),
    ("Usuario", "Usuario"),
)


def _citation_targets(cita: str, gold: dict[str, Any]) -> list[tuple[str | None, int | str]]:
    """Normalize an atomic ``cita`` into exact manual/page targets.

    The gold predates a fully structured citation field, so this parser is
    intentionally small and fail-closed around the syntaxes present in the P1
    population.  A referenced page need not have a gold quote: it remains an
    atomic-fact authority, but identity ambiguity is never silently expanded
    to the rest of the question's citations.
    """
    if not isinstance(cita, str) or not cita.strip():
        raise ValueError(f"atomic fact lacks cita: {cita!r}")

    alias_events: list[tuple[int, str]] = []
    folded = unicodedata.normalize("NFKC", cita).casefold()
    for surface, canonical in MANUAL_ALIASES:
        start = 0
        needle = surface.casefold()
        while True:
            index = folded.find(needle, start)
            if index < 0:
                break
            alias_events.append((index, canonical))
            start = index + len(needle)
    alias_events.sort()

    gold_manuals = [str(row["manual"]) for row in gold.get("citations", [])]
    default_manual: str | None = gold_manuals[0] if gold_manuals else None
    targets: list[tuple[str | None, int | str]] = []
    page_pattern = re.compile(
        r"(?i)(?<![A-Za-z0-9])p\s*(\d+(?:\s*-\s*\d+)?(?:\s*,\s*p?\s*\d+)*)"
    )
    for match in page_pattern.finditer(cita):
        prior = [event for event in alias_events if event[0] < match.start()]
        alias = prior[-1][1] if prior else default_manual
        page_spec = match.group(1)
        for token in re.split(r"\s*,\s*p?\s*", page_spec):
            if "-" in token:
                first, last = (int(value.strip()) for value in token.split("-", 1))
                if last < first or last - first > 20:
                    raise ValueError(f"invalid atomic citation page range: {cita}")
                pages = range(first, last + 1)
            else:
                pages = [int(token)]
            targets.extend((alias, page) for page in pages)

    # Appendix A is a cited location even where the legacy gold has no direct
    # page quote.  Its index citation binds the physical destination (p61), so
    # retain that numeric page rather than introducing a non-numeric page token
    # that the E2E chunk identity cannot compare.
    appendix_a = re.search(r"(?i)ap[eé]ndice\s+A", cita)
    if appendix_a:
        prior = [event for event in alias_events if event[0] < appendix_a.start()]
        index_pages: list[int] = []
        for row in gold.get("citations", []):
            quote = str(row.get("quote", ""))
            if re.search(r"(?i)ap[eé]ndice", quote):
                numbers = [int(value) for value in re.findall(r"\b\d+\b", quote)]
                index_pages.extend(value for value in numbers if value != int(row["page"]))
        if len(set(index_pages)) != 1:
            raise ValueError(f"Appendix A page identity is not unique: {index_pages}")
        targets.append((prior[-1][1] if prior else default_manual, index_pages[0]))

    # hp017#0 cites the whole Appendix 5.  Expand only the gold rows explicitly
    # labelled as that appendix, not the unrelated p20 citation in the QID.
    if not targets and re.search(r"(?i)Ap\.?\s*5", cita):
        for row in gold.get("citations", []):
            manual = str(row["manual"])
            if "ap" in manual.casefold() and "5" in manual:
                targets.append((manual, row["page"]))

    if not targets:
        raise ValueError(f"unsupported atomic citation syntax: {cita}")

    deduped: list[tuple[str | None, int | str]] = []
    for target in targets:
        if target not in deduped:
            deduped.append(target)
    return deduped


def _manual_matches(alias: str | None, manual: str) -> bool:
    if alias is None:
        return True
    alias_folded = unicodedata.normalize("NFKC", alias).casefold()
    manual_folded = unicodedata.normalize("NFKC", manual).casefold()
    return alias_folded in manual_folded or manual_folded in alias_folded


def fact_source_refs(gold: dict[str, Any], source_fact: dict[str, Any]) -> list[dict[str, Any]]:
    """Build page refs from this fact's ``cita``, never the QID citation bag."""
    cita = source_fact.get("cita")
    targets = _citation_targets(str(cita), gold)
    gold_citations = gold.get("citations", [])
    refs: list[dict[str, Any]] = []
    for alias, page in targets:
        exact = [
            row for row in gold_citations
            if str(row.get("page")) == str(page)
            and _manual_matches(alias, str(row.get("manual", "")))
        ]
        if not exact and alias and alias in {str(row.get("manual")) for row in gold_citations}:
            exact = [
                row for row in gold_citations
                if str(row.get("page")) == str(page) and str(row.get("manual")) == alias
            ]
        if exact:
            selected = exact[0]
            manual = str(selected["manual"])
            quote = normalized_text(str(selected.get("quote", "")))
            authority = "evals/gold_answers_v1.yaml:atomic_facts[].cita+citations[]"
            quote_text: str | None = quote or None
            quote_sha256: str | None = normalized_sha256(quote) if quote else None
            identity_status = (
                "gold_quote_bound" if quote else "atomic_cita_page_without_gold_quote"
            )
        else:
            matching_manuals = [
                str(row["manual"]) for row in gold_citations
                if _manual_matches(alias, str(row.get("manual", "")))
            ]
            unique_manuals = list(dict.fromkeys(matching_manuals))
            if len(unique_manuals) > 1:
                raise ValueError(f"ambiguous atomic citation manual {alias!r}: {unique_manuals}")
            manual = unique_manuals[0] if unique_manuals else str(alias)
            quote_text = None
            quote_sha256 = None
            authority = "evals/gold_answers_v1.yaml:atomic_facts[].cita"
            identity_status = "atomic_cita_page_without_gold_quote"
        refs.append({
            "binding_level": "fact_specific_page",
            "chunk_id": None,
            "document_id": None,
            "source_file": manual,
            "page": page,
            "product_model": None,
            "manufacturer": None,
            "quote_text": quote_text,
            "quote_sha256": quote_sha256,
            "authority": authority,
            "atomic_cita": cita,
            "identity_status": identity_status,
        })
    return refs


def make_fact(
    *, fact_key: str, qid: str, statement: str, source_refs: list[dict[str, Any]],
    authority_refs: list[str], parent_fact_sha256: str | None,
    binding_level: str = "gold_verified_page", source_start: int | None = None,
    source_end: int | None = None, source_span_sha256: str | None = None,
    kpi_weight: int = 1, release_guard_only: bool = False,
    algorithm: str = "protected_fact_surface_v1",
) -> dict[str, Any]:
    if fact_key not in SURFACES:
        raise ValueError(f"missing preregistered surface contract: {fact_key}")
    forbidden = FORBIDDEN.get(fact_key, [])
    manual_ids = sorted({str(ref["source_file"]) for ref in source_refs})
    pages = sorted({str(ref["page"]) for ref in source_refs})
    return {
        "fact_id": fact_key,
        "fact_key": fact_key,
        "qid": qid,
        "statement": statement,
        "statement_sha256": normalized_sha256(statement),
        "parent_fact_sha256": parent_fact_sha256,
        "clauses": {
            "required": [{"clause_id": f"{fact_key}:required", "text": statement}],
            "forbidden": [
                {"clause_id": f"{fact_key}:forbidden:{index + 1}", "text": text}
                for index, text in enumerate(forbidden)
            ],
        },
        "surface_forms": {
            "normalization": "nfkd_casefold_alnum_ws",
            "required_all_groups": SURFACES[fact_key],
            "forbidden_any": forbidden,
        },
        "source_refs": source_refs,
        "citation_policy": {
            "mode": "valid_local_citation_required",
            "binding_level": binding_level,
            "additional_citations": "pass_only_same_span_product_revision_else_review",
        },
        "binding_level": binding_level,
        "manual_id": manual_ids,
        "pages": pages,
        "source_start": source_start,
        "source_end": source_end,
        "source_span_sha256": source_span_sha256,
        "authority_refs": authority_refs,
        "algorithm": algorithm,
        "kpi_weight": kpi_weight,
        "release_guard_only": release_guard_only,
        "not_a_regression_fact": False,
    }


def find_freeze_chunk(freeze: dict[str, Any], chunk_id: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("id") == chunk_id and "content" in value:
                matches.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(freeze)
    physical_fields = ("id", "document_id", "source_file", "page_number", "content")
    identities = {
        object_sha256({field: match.get(field) for field in physical_fields})
        for match in matches
    }
    if len(identities) != 1:
        raise ValueError(
            f"physical identity drift across representations for {chunk_id}: "
            f"{len(identities)} variants"
        )
    if not matches:
        raise ValueError(f"missing frozen chunk: {chunk_id}")
    for optional in ("product_model", "manufacturer"):
        values = {match.get(optional) for match in matches if match.get(optional) is not None}
        if len(values) > 1:
            raise ValueError(f"{optional} drift across representations for {chunk_id}: {values}")
    result = dict(max(matches, key=len))
    for optional in ("product_model", "manufacturer"):
        if result.get(optional) is None:
            result[optional] = next(
                (match[optional] for match in matches if match.get(optional) is not None),
                None,
            )
    return result


def exact_ref(chunk: dict[str, Any], *, span: tuple[int, int] | None = None) -> dict[str, Any]:
    content = chunk["content"]
    ref = {
        "binding_level": "accepted_exact_span" if span else "gold_verified_page",
        "chunk_id": chunk["id"],
        "document_id": chunk.get("document_id"),
        "source_file": chunk["source_file"],
        "page": chunk["page_number"],
        "product_model": chunk.get("product_model"),
        "manufacturer": chunk.get("manufacturer"),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "authority": "evals/gold_answers_v1.yaml._provenance",
    }
    if span:
        start, end = span
        ref.update({
            "source_start": start,
            "source_end": end,
            "source_span_sha256": hashlib.sha256(content[start:end].encode("utf-8")).hexdigest(),
        })
    return ref


def build_fact_contract() -> dict[str, Any]:
    gold_rows = load_yaml("evals/gold_answers_v1.yaml")
    ledger = load_json("evals/s113_fact_ledger_v1.json")
    freeze = load_json("evals/s113_full_contexts_freeze_v1.json")
    gold_by_qid = {row["qid"]: row for row in gold_rows}
    ledger_rows = [row for row in ledger["rows"] if row["qid"] in QIDS and row["diagnostic_class"] == "OK"]
    if len(ledger_rows) != 42:
        raise ValueError(f"historical S113 OK domain drifted: {len(ledger_rows)} != 42")

    historical: list[dict[str, Any]] = []
    parent_by_key: dict[str, dict[str, Any]] = {}
    for measured in ledger_rows:
        key = measured["fact_key"]
        match = FACT_KEY.fullmatch(key)
        if not match or match.group("qid") != measured["qid"]:
            raise ValueError(f"invalid historical fact key: {key}")
        indexed = historical_core_facts(gold_by_qid[measured["qid"]])
        index = int(match.group("index"))
        if index >= len(indexed):
            raise ValueError(f"historical index out of bounds: {key}")
        source_fact = indexed[index]
        if match.group("value") != source_fact["valor"]:
            raise ValueError(f"historical suffix/value mismatch: {key}")
        parent_by_key[key] = source_fact
        historical.append({
            "fact_key": key,
            "qid": measured["qid"],
            "parent_fact_sha256": object_sha256(source_fact),
            "source_fact": source_fact,
        })

    removed = next(row for row in historical if row["fact_key"] == "hp017#1:instruccion de entrada")
    historical = [row for row in historical if row["fact_key"] != removed["fact_key"]]
    old_disclosure = next(row for row in historical if row["fact_key"] == "hp017#3:seis tipos de retardo")
    historical = [row for row in historical if row["fact_key"] != old_disclosure["fact_key"]]

    facts: list[dict[str, Any]] = []
    for row in historical:
        qid = row["qid"]
        key = row["fact_key"]
        refs = fact_source_refs(gold_by_qid[qid], row["source_fact"])
        if qid == "hp018":
            hp018_chunk_by_fact = {
                "hp018#0:4 circuitos": "90d51dac-bd0b-4051-b414-ced0fe6e33bb",
                "hp018#1:6K8": "90d51dac-bd0b-4051-b414-ced0fe6e33bb",
                "hp018#2:diodo": "72fc4c53-f507-4e67-9192-ebc68b94be78",
                "hp018#3:Sirenas A,B,C,D": "72fc4c53-f507-4e67-9192-ebc68b94be78",
                "hp018#4:1 A": "90d51dac-bd0b-4051-b414-ced0fe6e33bb",
            }
            refs = [exact_ref(find_freeze_chunk(freeze, hp018_chunk_by_fact[key]))]
        algorithm = "hp011_rearme_inhibido_v1" if key == "hp011#1:r.I" else "protected_fact_surface_v1"
        facts.append(make_fact(
            fact_key=key,
            qid=qid,
            statement=row["source_fact"]["texto"],
            source_refs=refs,
            authority_refs=[
                "evals/gold_answers_v1.yaml",
                "evals/s113_fact_ledger_v1.json",
                "scripts/s118_build_atomic_benchmark.py:_historical_core_facts",
            ],
            parent_fact_sha256=row["parent_fact_sha256"],
            algorithm=algorithm,
        ))

    hp017_gold = gold_by_qid["hp017"]
    hp017_indexed = historical_core_facts(hp017_gold)
    hp017_watch_source = hp017_indexed[2]
    if hp017_watch_source["valor"] != "Editar Configuracion":
        raise ValueError("hp017#2 authority drift")
    hp017_watch_refs = [
        exact_ref(find_freeze_chunk(freeze, "51df7a51-4970-4cfc-8ef1-3771f480dd78")),
        exact_ref(find_freeze_chunk(freeze, "a95f8659-2277-4b32-a413-edd0e6cd2f10")),
    ]
    facts.append(make_fact(
        fact_key="hp017#2:Editar Configuracion",
        qid="hp017",
        statement=hp017_watch_source["texto"],
        source_refs=hp017_watch_refs,
        authority_refs=[
            "evals/gold_answers_v1.yaml",
            "evals/s273_v3b_arbiter_v1.json",
            "evals/s273_v3_closeout_v1.yaml",
        ],
        parent_fact_sha256=object_sha256(hp017_watch_source),
        kpi_weight=0,
        release_guard_only=True,
    ))

    disclosure_statement = (
        "La prosa declara seis/6 tipos de retardo; deben enumerarse todas las etiquetas "
        "no vacías de al menos una surface servida y declarar explícitamente que las "
        "surfaces discrepan, sin exigir ni inventar el literal siete."
    )
    disclosure_refs = [
        exact_ref(find_freeze_chunk(freeze, "570d9951-e3a6-4c64-a927-e26b5e6db842")),
    ]
    facts.append(make_fact(
        fact_key="hp017#3:disclosure_DEC128",
        qid="hp017",
        statement=disclosure_statement,
        source_refs=disclosure_refs,
        authority_refs=[
            "evals/s270_gold_adjudication_v1.yaml:row_8",
            "docs/DECISIONS.md:DEC-128",
            "evals/s271_872c_respec_rescore_v1.json",
        ],
        parent_fact_sha256=old_disclosure["parent_fact_sha256"],
        algorithm="hp017_delay_disclosure_v1",
    ))

    b6_chunk = find_freeze_chunk(freeze, "5b6a3a19-a924-4cf4-9513-bd50786ee3d9")
    b6_start, b6_end = 57, 290
    b6_statement = (
        "Para evitar que los controles de incendios, las alertas remotas y las zonas de "
        "extinción se disparen durante el mantenimiento, es imprescindible bloquearlos "
        "o desconectarlos previamente."
    )
    b6_ref = exact_ref(b6_chunk, span=(b6_start, b6_end))
    facts.append(make_fact(
        fact_key="hp002#banked:obl_b6f6211be439",
        qid="hp002",
        statement=b6_statement,
        source_refs=[b6_ref],
        authority_refs=[
            "evals/s270_gold_adjudication_v1.yaml:row_3",
            "evals/s272_banked_funnel_v1.json",
            "evals/s235_direct_clause_bound_score_packet_v1.json",
        ],
        parent_fact_sha256=None,
        binding_level="accepted_exact_span",
        source_start=b6_start,
        source_end=b6_end,
        source_span_sha256=b6_ref["source_span_sha256"],
    ))

    qid_order = {qid: index for index, qid in enumerate(QIDS)}
    facts.sort(key=lambda fact: (qid_order[fact["qid"]], fact["fact_id"]))
    counts = Counter(fact["qid"] for fact in facts)
    actual_counts = {qid: counts[qid] for qid in QIDS}
    if len(facts) != 43 or actual_counts != EXPECTED_COUNTS:
        raise ValueError(f"transformed population drift: {len(facts)}, {actual_counts}")
    if sum(fact["kpi_weight"] for fact in facts) != 42:
        raise ValueError("release-only watch fact must not alter the KPI weight")

    target_chunk = find_freeze_chunk(freeze, "d27b1a1b-69cd-4318-a459-f3c86eb757ba")
    target_content = target_chunk["content"]
    target_clauses = [
        ("obl_16637b935bd4", 2479, 2555, "Al programar reglas de causa-efecto evite las lógicas contradictorias."),
        ("obl_0d6a30948dfd", 2558, 2724, "Es de vital importancia probar rigurosamente todas las reglas durante la puesta en marcha del sistema para verificar que no haya conflictos lógicos entre ellas."),
    ]
    clause_rows = []
    for obligation_id, start, end, exact_text in target_clauses:
        source_quote = target_content[start:end]
        if exact_text not in source_quote:
            raise ValueError(f"target span drift: {obligation_id}")
        clause_rows.append({
            "obligation_id": obligation_id,
            "exact_text": exact_text,
            "normalized_text_sha256": normalized_sha256(exact_text),
            "source_start": start,
            "source_end": end,
            "source_quote": source_quote,
            "source_span_sha256": hashlib.sha256(source_quote.encode("utf-8")).hexdigest(),
        })

    source_files = [
        "evals/gold_answers_v1.yaml",
        "evals/s113_fact_ledger_v1.json",
        "evals/s113_full_contexts_freeze_v1.json",
        "evals/s235_direct_clause_bound_score_packet_v1.json",
        "evals/s270_gold_adjudication_v1.yaml",
        "evals/s271_872c_respec_rescore_v1.json",
        "evals/s272_banked_funnel_v1.json",
        "evals/s273_v3b_arbiter_v1.json",
        "evals/s273_v3_closeout_v1.yaml",
        "evals/s274_banked_funnel_v1.json",
    ]
    contract = {
        "schema_version": "s277_c1_p1_fact_contract_v1",
        "contract_id": "S277-C1-P1-PROTECTED-PACKET-V1",
        "status": "PREREGISTERED_OFFLINE_NO_PAID_EXECUTION",
        "authority": {
            "precedence": [
                "Alberto marks S270 / DEC-125 / DEC-128",
                "verified gold with provenance and citations",
                "S113 identifies historically OK facts only",
                "S201/S202 are frozen evidence only, never gold authority",
                "S272 authorizes the live-banked hp002 conversion",
                "S273 authorizes only the contemporary release watch fact",
                "S274 authorizes only the candidate target, never an automatic pass",
            ],
            "source_file_receipts": [file_receipt(path) for path in source_files],
            "hash_convention": "sha256(bytes.replace(CRLF,LF)); platform-dependent raw hashes are excluded",
        },
        "population": {
            "qids": QIDS,
            "historical_s113_ok_count": 42,
            "expected_base_fact_count": 43,
            "actual_base_fact_count": len(facts),
            "per_qid_base_counts": actual_counts,
            "kpi_weight_sum": sum(fact["kpi_weight"] for fact in facts),
            "release_guard_only_count": sum(bool(fact["release_guard_only"]) for fact in facts),
            "target_count_separate_from_base": 1,
        },
        "transformation_diff": {
            "source_contract": "scripts/s118_build_atomic_benchmark.py:_historical_core_facts",
            "operations": [
                {
                    "operation": "exclude_historical_fact",
                    "fact_key": removed["fact_key"],
                    "parent_fact_sha256": removed["parent_fact_sha256"],
                    "reason": "components obl_b2043cd4379b/obl_7aa723717412 remain S274 residuals",
                },
                {
                    "operation": "add_release_guard_only",
                    "fact_key": "hp017#2:Editar Configuracion",
                    "parent_fact_sha256": object_sha256(hp017_watch_source),
                    "kpi_weight": 0,
                    "reason": "S273 observed 2/3 OFF to 1/3 ON loss; conservative release watch, not gold adjudication",
                },
                {
                    "operation": "replace_fact_in_place",
                    "from_fact_key": old_disclosure["fact_key"],
                    "to_fact_key": "hp017#3:disclosure_DEC128",
                    "parent_fact_sha256": old_disclosure["parent_fact_sha256"],
                    "reason": "DEC-128 option 1 source-contract disclosure",
                },
                {
                    "operation": "add_live_banked_fact",
                    "fact_key": "hp002#banked:obl_b6f6211be439",
                    "authority": "evals/s272_banked_funnel_v1.json",
                },
            ],
            "result_count": 43,
        },
        "protected_facts": facts,
        "question_guards": [
            {
                "guard_id": "hp013_safety_no_autonomous_battery_procedure_v1",
                "qid": "hp013",
                "required_clauses": [
                    "The manual does not document an autonomous battery-only replacement procedure.",
                    "Do not guarantee that configuration will be preserved by an undocumented procedure.",
                    "If EEPROM/non-volatility is mentioned, frame it as a qualified expectation, not a certified procedure.",
                ],
                "forbidden_clauses": [
                    "Invented step-by-step battery-only replacement procedure.",
                    "Unqualified guarantee that configuration cannot be lost.",
                ],
                "surface_forms": {
                    "normalization": "nfkd_casefold_alnum_ws",
                    "required_all_groups": [["manual no documenta", "no se documenta", "no hay procedimiento"], ["bateria", "batería"]],
                    "forbidden_any": ["garantizado que no perdera", "garantizado que no perderá"],
                },
                "authority_refs": ["evals/gold_answers_v1.yaml:hp013", "evals/s277_c1_p1_design_v1.md:section_9"],
                "source_refs": question_gold_source_refs(gold_by_qid["hp013"]),
                "algorithm": "hp013_safety_guard_v1",
                "decision_policy": {
                    "on_machine_safe_match": "REVIEW",
                    "on_ambiguous": "REVIEW",
                    "on_violation": "FAIL",
                    "review_reason": "safety wording requires blind semantic review",
                },
                "manufacturer_service_recommendation": "permitted_not_required",
                "kpi_weight": 0,
                "safety_guard_only": True,
                "not_a_regression_fact": True,
            }
        ],
        "registered_conflicts": [
            {
                "conflict_id": "conf_26f63590494f",
                "qid": "hp017",
                "kind": "document_value_conflict",
                "product_scope": "Pearl",
                "operation": "cause_effect_menu_path",
                "values": ["7", "8"],
                "evidence": [
                    {
                        "chunk_id": "a95f8659-2277-4b32-a413-edd0e6cd2f10",
                        "source_file": "997-671-005-3_Configuration_ES",
                        "page": 45,
                        "value": "7",
                        "source_start": 2033,
                        "source_end": 2347,
                    },
                    {
                        "chunk_id": "51df7a51-4970-4cfc-8ef1-3771f480dd78",
                        "source_file": "997-671-005-3_Configuration_ES",
                        "page": 15,
                        "value": "8",
                        "source_start": 1313,
                        "source_end": 1330,
                    },
                ],
                "prohibited_surface_forms": ["7: causa y efecto", "8: causa y efecto"],
                "disclosure_surface_forms": ["discrepancia", "no coincide", "difiere", "discrepan", "fuente", "revision", "revisión"],
                "required_resolution": "omit_flat_menu_number_or_explicitly_attribute_and_disclose_source_divergence",
                "algorithm": "hp017_menu_conflict_v1",
                "decision_policy": {"on_match": "PASS", "on_ambiguous": "REVIEW", "on_violation": "FAIL"},
                "preexisting": True,
                "candidate_failure_label": "FAIL_UNSAFE_CONFLICT_NOT_C1_REGRESSION",
                "stored_prior_label": "HOLD_PREPAID_KNOWN_CONFLICT_RISK",
            }
        ],
        "c1_target": {
            "target_id": "d27b1a1b-69cd-4318-a459-f3c86eb757ba",
            "qid": "hp017",
            "separate_from_base": True,
            "compound_obligation_ids": ["obl_16637b935bd4", "obl_0d6a30948dfd"],
            "statement": "One compound warning obligation; both source clauses are independently mandatory.",
            "clauses": clause_rows,
            "target_identity": {
                "candidate_id": target_chunk["id"],
                "document_id": target_chunk["document_id"],
                "source_file": target_chunk["source_file"],
                "page_number": target_chunk["page_number"],
                "product_model": target_chunk["product_model"],
                "manufacturer": target_chunk.get("manufacturer"),
                "content_sha256": hashlib.sha256(target_content.encode("utf-8")).hexdigest(),
                "required_identity_fields": ["candidate_id", "document_id", "source_file", "page_number", "product_model", "content_sha256"],
            },
            "source_refs": [exact_ref(target_chunk, span=(2479, 2724))],
            "citation_policy": {
                "mode": "valid_local_citation_required",
                "binding_level": "accepted_exact_span",
                "additional_citations": "pass_only_same_span_product_revision_else_review",
                "dynamic_fragment_number": True,
                "shared_local_citation": "allowed_only_when_local_unit_unambiguously_covers_both_clauses",
            },
            "algorithm": "hp017_compound_warning_exact_v1",
            "kpi_weight": 1,
            "official_kpi_already_banked": True,
            "p1_does_not_move_kpi": True,
            "required_replicas": 3,
            "required_passes": 3,
        },
        "exclusions": {
            "not_protected_as_base": [
                "cat001#3:32 / 25 / 20",
                "cat017#2:licencia CLIP por lazo",
                "cat018#1:pestana Programacion: Zona + CBE",
                "cat018#2:Tipo SW / asociacion CBE",
                "hp002#3:7.6.1",
                "hp011#0:ABORT",
                "hp011#2:05 a 295 seg",
                "hp011#3:enclavadas",
                "hp013#0:EEPROM",
                "hp013#1:PWR-R",
                "hp017#1:instruccion de entrada",
                "obl_b2043cd4379b",
                "obl_7aa723717412",
            ],
            "flat_hp017_menu_number": "registered_conflict_not_positive_requirement",
        },
        "decision_semantics": {
            "fact_positive": "PASS only with deterministic surface contract and valid local citation; plausible paraphrase is REVIEW",
            "review_blocks_go": True,
            "instrument_drift": "INSTRUMENT_ERROR",
            "positive_claim": "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS",
            "forbidden_claim": "ZERO_REGRESSION",
            "official_atomic_kpi_before_and_after_p1": "146/154",
        },
    }
    contract["payload_sha256"] = object_sha256(contract)
    return contract


def build_release_config_schema() -> dict[str, Any]:
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    git_sha = {"type": "string", "pattern": "^[0-9a-f]{40}$"}
    safe_env_property_name = {
        "anyOf": [
            {"const": "MP_DISTINCTIVE_TOKEN"},
            {"const": "LLM_MAX_TOKENS"},
            {"not": {"pattern": "(?i)(secret|token|password|api[_-]?key|credential)"}},
        ]
    }
    required_semantic_env = [*SEMANTIC_ENV_CONSTS, "VISUAL_ASSETS_REGISTRY"]
    live_env_properties: dict[str, Any] = {
        key: {"const": value} for key, value in SEMANTIC_ENV_CONSTS.items()
    }
    live_env_properties.update({
        key: {"const": value} for key, value in SEMANTIC_DEFAULT_ENV_CONSTS.items()
    })
    live_env_properties.update({key: {"const": "off"} for key in TARGET_OFF_ENV_FLAGS})
    live_env_properties["VISUAL_ASSETS_REGISTRY"] = {
        "type": "string",
        "enum": ["on", "off"],
    }

    def semantic_config_schema(profile: str, coverage_enabled: bool) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["schema", "corpus", "retrieval", "generation", "embedding", "coverage"],
            "properties": {
                "schema": {"const": "s277_c1_semantic_effective_config_v1"},
                "corpus": {
                    "type": "object", "additionalProperties": False,
                    "required": ["chunks_table"],
                    "properties": {"chunks_table": {"const": "chunks_v2"}},
                },
                "retrieval": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "retrieval_top_k", "rerank_top_k", "reranker_backend",
                        "reranker_model", "rerank_preview_chars", "merge_strategy",
                        "hyde_enabled", "enunciados_multivector", "hyq_table",
                        "hyq_pilot_file", "identity_resolve", "identity_resolve_policy",
                    ],
                    "properties": {
                        "retrieval_top_k": {"const": 50},
                        "rerank_top_k": {"const": 10},
                        "reranker_backend": {"const": "llm"},
                        "reranker_model": {"const": "claude-sonnet-4-6"},
                        "rerank_preview_chars": {"const": 800},
                        "merge_strategy": {"const": "stamps"},
                        "hyde_enabled": {"const": False},
                        "enunciados_multivector": {"const": True},
                        "hyq_table": {"const": True},
                        "hyq_pilot_file": {"const": ""},
                        "identity_resolve": {"const": True},
                        "identity_resolve_policy": {"const": "add"},
                    },
                },
                "generation": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "model", "max_tokens", "temperature", "prompt_cache",
                        "prompt_variant", "selection_block", "must_preserve_contract",
                        "visual_assets_registry",
                    ],
                    "properties": {
                        "model": {"const": "claude-sonnet-4-6"},
                        "max_tokens": {"const": 3500},
                        "temperature": {"const": 0},
                        "prompt_cache": {"const": False},
                        "prompt_variant": {"const": "fidelity"},
                        "selection_block": {"const": True},
                        "must_preserve_contract": {"const": True},
                        "visual_assets_registry": {"type": "boolean"},
                    },
                },
                "embedding": {
                    "type": "object", "additionalProperties": False,
                    "required": ["model"],
                    "properties": {"model": {"const": "voyage-4-large"}},
                },
                "coverage": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "release_profile", "post_rerank_coverage",
                        "structural_neighbor_coverage", "mandatory_callout",
                        "mandatory_verb_trigger",
                    ],
                    "properties": {
                        "release_profile": {"const": profile},
                        "post_rerank_coverage": {"const": coverage_enabled},
                        "structural_neighbor_coverage": {"const": coverage_enabled},
                        "mandatory_callout": {"const": coverage_enabled},
                        "mandatory_verb_trigger": {"const": coverage_enabled},
                    },
                },
            },
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "s277_c1_p1_release_config_schema_v1",
        "title": "Safe, secret-free release identity for S277 C1 P1",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version", "status", "secret_fields_present", "candidate", "railway",
            "derived_config", "models", "retrieval", "runtime", "implementation_hashes",
            "rpc_allowlist", "authorizations",
        ],
        "properties": {
            "schema_version": {"const": "s277_c1_p1_release_config_v1"},
            "status": {"const": "MATERIALIZED_SAFE_NO_SECRETS"},
            "secret_fields_present": {"const": False},
            "candidate": {
                "type": "object", "additionalProperties": False,
                "required": ["tested_commit_sha", "tested_tree_sha", "detached_worktree", "git_status_empty", "untracked_files", "bot_version"],
                "properties": {
                    "tested_commit_sha": git_sha, "tested_tree_sha": git_sha,
                    "detached_worktree": {"const": True}, "git_status_empty": {"const": True},
                    "untracked_files": {"const": []}, "bot_version": {"type": "string", "minLength": 1},
                },
            },
            "railway": {
                "type": "object", "additionalProperties": False,
                "required": [
                    "read_only_snapshot_taken_at", "snapshot_max_age_seconds",
                    "snapshot_future_skew_seconds", "live_snapshot",
                    "railway_live_snapshot_sha256", "planned_bootstrap_patch",
                ],
                "properties": {
                    "read_only_snapshot_taken_at": {"type": "string", "format": "date-time"},
                    "snapshot_max_age_seconds": {"const": SNAPSHOT_MAX_AGE_SECONDS},
                    "snapshot_future_skew_seconds": {"const": SNAPSHOT_FUTURE_SKEW_SECONDS},
                    "live_snapshot": {
                        "type": "object",
                        "minProperties": 1,
                        "required": [*required_semantic_env, *TARGET_OFF_ENV_FLAGS],
                        "properties": live_env_properties,
                        "propertyNames": safe_env_property_name,
                        "additionalProperties": {"type": ["string", "boolean", "integer"]},
                    },
                    "railway_live_snapshot_sha256": sha,
                    "planned_bootstrap_patch": {
                        "type": "object", "additionalProperties": False,
                        "required": ["delete", "set"],
                        "properties": {
                            "delete": {
                                "type": "array", "uniqueItems": True, "minItems": 4, "maxItems": 4,
                                "items": {"enum": ["POST_RERANK_COVERAGE", "STRUCTURAL_NEIGHBOR_COVERAGE", "COVERAGE_MANDATORY_CALLOUT", "MP_MANDATORY_VERB_TRIGGER"]},
                            },
                            "set": {"const": {"COVERAGE_RELEASE_PROFILE": "off"}},
                        },
                    },
                },
            },
            "derived_config": {
                "type": "object", "additionalProperties": False,
                "required": [
                    "bootstrap_profile", "p1_target_profile", "common_config_sha256",
                    "bootstrap_effective_config_sha256", "target_effective_config_sha256",
                    "semantic_projection_schema", "bootstrap_semantic_config",
                    "target_semantic_config", "bootstrap_semantic_config_sha256",
                    "target_semantic_config_sha256", "raw_allowlisted_env",
                ],
                "properties": {
                    "bootstrap_profile": {"const": "off"},
                    "p1_target_profile": {"const": "coverage_c1_v1"},
                    "common_config_sha256": sha,
                    "bootstrap_effective_config_sha256": sha,
                    "target_effective_config_sha256": sha,
                    "semantic_projection_schema": {
                        "const": "s277_c1_semantic_effective_config_v1"
                    },
                    "bootstrap_semantic_config": semantic_config_schema("off", False),
                    "target_semantic_config": semantic_config_schema("coverage_c1_v1", True),
                    "bootstrap_semantic_config_sha256": sha,
                    "target_semantic_config_sha256": sha,
                    "raw_allowlisted_env": {
                        "type": "object",
                        "required": [
                            *required_semantic_env, *TARGET_OFF_ENV_FLAGS,
                            "COVERAGE_RELEASE_PROFILE",
                        ],
                        "properties": {
                            **live_env_properties,
                            "COVERAGE_RELEASE_PROFILE": {"const": "off"},
                        },
                        "propertyNames": safe_env_property_name,
                        "additionalProperties": {"type": ["string", "boolean", "integer"]},
                    },
                },
            },
            "models": {
                "type": "object", "additionalProperties": False,
                "required": ["generator", "reranker", "embedding", "temperature", "max_tokens", "prompt_cache", "inference_geo", "service_tier"],
                "properties": {
                    "generator": {"const": "claude-sonnet-4-6"},
                    "reranker": {"const": "claude-sonnet-4-6"},
                    "embedding": {"const": "voyage-4-large"},
                    "temperature": {"const": 0},
                    "max_tokens": {"const": 3500},
                    "prompt_cache": {"const": False},
                    "inference_geo": {"const": "global"},
                    "service_tier": {"const": "standard_sync"},
                },
            },
            "retrieval": {
                "type": "object", "additionalProperties": False,
                "required": ["chunks_table", "retrieval_top_k", "rerank_top_k", "reranker_backend", "hyde_enabled"],
                "properties": {
                    "chunks_table": {"const": "chunks_v2"},
                    "retrieval_top_k": {"const": 50},
                    "rerank_top_k": {"const": 10},
                    "reranker_backend": {"const": "llm"},
                    "hyde_enabled": {"const": False},
                },
            },
            "runtime": {
                "type": "object", "additionalProperties": False,
                "required": ["python_version", "anthropic_sdk_version", "voyage_sdk_version", "effective_lock_sha256"],
                "properties": {
                    "python_version": {"type": "string", "minLength": 1},
                    "anthropic_sdk_version": {"type": "string", "minLength": 1},
                    "voyage_sdk_version": {"type": "string", "minLength": 1},
                    "effective_lock_sha256": sha,
                },
            },
            "implementation_hashes": {
                "type": "object", "minProperties": 1,
                "propertyNames": {"pattern": "^[A-Za-z0-9_./-]+$"}, "additionalProperties": sha,
            },
            "rpc_allowlist": {
                "type": "array", "uniqueItems": True, "minItems": 2,
                "items": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                "allOf": [
                    {"contains": {"const": "match_chunks_v2"}},
                    {"contains": {"const": "search_chunks_text_v2"}},
                ],
            },
            "authorizations": {
                "type": "object", "additionalProperties": False,
                "required": ["paid_run", "railway_mutation", "supabase_write"],
                "properties": {
                    "paid_run": {"const": False}, "railway_mutation": {"const": False}, "supabase_write": {"const": False},
                },
            },
        },
    }


def build_prereg(contract: dict[str, Any], release_schema: dict[str, Any]) -> dict[str, Any]:
    gold = {row["qid"]: row for row in load_yaml("evals/gold_answers_v1.yaml")}
    model_receipt = load_json("evals/s277_c1_p1_model_extraction_receipt_v1.json")
    observed = {row["qid"]: row for row in model_receipt["rows"]}
    rows = []
    for qid in QIDS:
        question = gold[qid]["question"]
        question_sha = hashlib.sha256(question.encode("utf-8")).hexdigest()
        if observed[qid]["question_sha256"] != question_sha or observed[qid]["models"] != EXPECTED_MODELS[qid]:
            raise ValueError(f"model extraction receipt drift: {qid}")
        rows.append({
            "qid": qid,
            "question": question,
            "question_sha256": question_sha,
            "expected_target_models": EXPECTED_MODELS[qid],
            "query_for_retrieval": "exact_question",
            "available_models": None,
            "fresh_single_turn": True,
        })

    fact_path = EVALS / "s277_c1_p1_fact_contract_v1.json"
    schema_path = EVALS / "s277_c1_p1_release_config_schema_v1.json"
    replica_plan_sha256 = object_sha256(REPLICA_ORDER)
    call_keys = [
        f"{replica}:{operation}"
        for replica in REPLICA_ORDER
        for operation in ("embedding", "rerank", "synthesis")
    ]
    call_plan_sha256 = object_sha256(call_keys)
    budget_operations = {
        "embedding": {
            "provider": "voyage",
            "model": "voyage-4-large",
            "max_input_tokens": 1000,
            "max_output_tokens": 0,
            "input_usd_per_mtok": "0.12",
            "output_usd_per_mtok": "0",
            "max_cost_usd": "0.001",
        },
        "rerank": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "max_input_tokens": 10000,
            "max_output_tokens": 1000,
            "input_usd_per_mtok": "3",
            "output_usd_per_mtok": "15",
            "max_cost_usd": "0.05",
        },
        "synthesis": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "max_input_tokens": 20000,
            "max_output_tokens": 3500,
            "input_usd_per_mtok": "3",
            "output_usd_per_mtok": "15",
            "max_cost_usd": "0.20",
        },
    }
    return {
        "schema_version": "s277_c1_p1_prereg_v1",
        "prereg_id": "S277-C1-P1-E2E-27-V1",
        "status": "PREREGISTERED_OFFLINE_EXECUTION_NOT_AUTHORIZED",
        "date": "2026-07-20",
        "decision": {
            "question": "Can coverage_c1_v1 proceed to the release sequence without observed protected loss in the preregistered dev cohort?",
            "positive_claim": "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS",
            "forbidden_claims": ["ZERO_REGRESSION", "98_PERCENT_VALIDATED", "ORGANIC_GENERALIZATION"],
            "official_atomic_kpi": "146/154",
            "p1_can_change_kpi": False,
        },
        "authorization": {
            "paid_execution": False,
            "railway_mutation": False,
            "supabase_write": False,
            "deploy": False,
            "network_during_offline_commands": False,
            "later_explicit_paid_permit_required": True,
            "paid_permit_required_fields": [
                "authorization_id", "run_id", "artifact_identity_sha256",
                "release_config_sha256", "prereg_sha256", "replica_plan_sha256",
            ],
            "artifact_identity": "sha256_canonical_json(run_id,resolved_artifact_root)",
            "global_atomic_claim_outside_artifact_dir": True,
            "authorization_ledger_derivation": "artifact_root.parent/.s277_c1_p1_authorization_claims_v1",
            "authorization_ledger_root_injection_allowed": False,
            "execution_lease_derivation": "authorization_ledger/leases/{sha256(normcase(resolved_artifact_root))}.json",
            "execution_lease_acquire": "O_EXCL_before_claim_bind_and_recovery",
            "execution_lease_release": "only_after_result_persisted",
            "execution_lease_existing": "HOLD_MANUAL_RECOVERY_NO_AUTO_RECLAIM",
            "execution_lease_scope": "single_host_filesystem_only",
            "execution_lease_multi_host": "STOP_LINE_EXTERNAL_TRANSACTIONAL_LOCK_REQUIRED",
            "execution_lease_recovery_command": "NOT_IMPLEMENTED_FUTURE_REVIEW",
            "authorization_receipt_json_safe_deep_copy_and_seal": True,
            "existing_claim_requires_canonical_resume_state": [
                "calls.jsonl", "calls.jsonl.genesis.json",
                "calls.jsonl.claims", "run_genesis.json",
            ],
            "claim_resume_policy": "same_authorization_id_run_id_artifact_identity_and_genesis_only",
        },
        "sealed_inputs": {
            "fact_contract": {
                "path": "evals/s277_c1_p1_fact_contract_v1.json",
                "sha256_lf": sha256_lf_bytes(fact_path.read_bytes()),
                "payload_sha256": contract["payload_sha256"],
            },
            "model_extraction_receipt": file_receipt("evals/s277_c1_p1_model_extraction_receipt_v1.json"),
            "release_config_schema": {
                "path": "evals/s277_c1_p1_release_config_schema_v1.json",
                "sha256_lf": sha256_lf_bytes(schema_path.read_bytes()),
                "schema_object_sha256": object_sha256(release_schema),
            },
            "release_config": {
                "required_path": "evals/s277_c1_p1_release_config_v1.json",
                "materialized": False,
                "hold_until_materialized": "HOLD_RELEASE_CONFIG_NOT_MATERIALIZED",
                "reason": "requires a later read-only Railway snapshot and a clean detached candidate worktree",
            },
        },
        "population": {
            "qids": QIDS,
            "rows": rows,
            "replica_order": REPLICA_ORDER,
            "replica_count": 27,
            "replica_plan_sha256": replica_plan_sha256,
            "per_qid_replicas": {qid: (3 if qid == "hp017" else 2) for qid in QIDS},
            "shuffle": False,
            "authoritative_replay": False,
        },
        "input_preflight": {
            "extract_product_models_must_equal_expected_exactly": True,
            "target_models_must_be_nonempty": True,
            "query_for_retrieval_must_equal_question": True,
            "available_models_must_be_null": True,
            "unexpected_fts_no_model_path": "HOLD_INPUT_DRIFT",
            "expectation_mismatch_class": "HOLD_EXPECTATION_DRIFT",
            "json_safe_deep_copy_exact": [
                "release_config", "prereg", "fingerprint_receipt",
                "fence_open_receipt",
            ],
            "preserve_runtime_identity": True,
            "execution_start_rebuild_with_fresh_runtime_identity": True,
            "runtime_rechecked_immediately_before_lease_and_every_send": True,
            "execution_start_exact_seals": [
                "release_config_sha256", "prereg_sha256",
                "fingerprint_receipt_sha256", "fence_open_receipt_sha256",
                "runtime_identity_sha256", "stored_control_score_sha256",
                "budget_sha256", "input_contract_sha256",
            ],
        },
        "candidate_path": {
            "entrypoint": "execute_rag_turn",
            "one_call_per_replica": True,
            "required_stages": [
                "retrieve_chunks", "rerank_strict", "observer", "structural_fetch",
                "selector_attestation", "coverage", "generator", "must_preserve",
                "visual_assets_branch", "telegram_renderer",
            ],
            "frozen_s113_context_for_authoritative_result": False,
            "offline_replay_can_rescue_or_pass": False,
            "reranker_fallback_allowed": False,
        },
        "model_calls": {
            "expected": {"voyage_embedding": 27, "sonnet_rerank": 27, "sonnet_synthesis": 27, "total": 81},
            "maximum_physical_delegations": 81,
            "call_plan_sha256": call_plan_sha256,
            "automatic_retries": 0,
            "hyde_enabled": False,
            "operations_allowlist": ["voyage.embed_query", "anthropic.rerank", "anthropic.synthesis"],
            "unregistered_call": "NO_GO_PARTIAL",
        },
        "wal": {
            "format": "append_only_jsonl_hash_chain",
            "hash_algorithm": "sha256_canonical_json",
            "chain_fields": ["previous_event_sha256", "event_sha256"],
            "run_genesis_sidecar": "calls.jsonl.genesis.json",
            "canonical_runtime_layout": {
                "call_journal": "artifact_root/calls.jsonl",
                "call_journal_genesis": "artifact_root/calls.jsonl.genesis.json",
                "call_claims": "artifact_root/calls.jsonl.claims",
                "artifact_genesis": "artifact_root/run_genesis.json",
                "authorization_ledger": "artifact_root.parent/.s277_c1_p1_authorization_claims_v1",
                "run_lease": "authorization_ledger/leases/{sha256(normcase(resolved_artifact_root))}.json",
            },
            "runtime_layout_schema": "s277_c1_p1_runtime_layout_v1",
            "runtime_layout_sha256_in_run_genesis": True,
            "run_genesis_sha256_on_every_event_and_atomic_call_claim": True,
            "run_genesis_exact_identity": [
                "authorization_id", "authorization_receipt_sha256", "run_id",
                "artifact_identity_sha256",
                "runtime_layout", "runtime_layout_sha256",
                "release_config_sha256", "prereg_sha256", "tested_commit_sha",
                "tested_tree_sha", "target_semantic_config_sha256",
                "fingerprint_receipt_sha256", "fingerprint_sha256",
                "fence_open_receipt_sha256", "fence_identity",
                "replica_plan_sha256", "call_plan_sha256",
                "validation_snapshot", "validation_snapshot_sha256",
            ],
            "event_sha256_input": "canonical_event_without_event_sha256",
            "genesis_previous_event_sha256": None,
            "fsync_each_event": True,
            "call_key": "deterministic",
            "states": ["RESERVED_FSYNCED", "COMPLETED", "FAILED_PRE_SEND_NO_RETRY", "UNKNOWN_BILLED_POST_SEND"],
            "transitions": {
                "RESERVED_FSYNCED": ["COMPLETED", "FAILED_PRE_SEND_NO_RETRY", "UNKNOWN_BILLED_POST_SEND"],
                "COMPLETED": [], "FAILED_PRE_SEND_NO_RETRY": [], "UNKNOWN_BILLED_POST_SEND": [],
            },
            "reserve_and_fsync_before_network": True,
            "post_delegation_exception": "UNKNOWN_BILLED_POST_SEND",
            "unterminated_reservation_on_resume": "UNKNOWN_BILLED_POST_SEND_AND_BLOCK",
            "opened_journal_change_before_bind_or_recovery": "HOLD_WAL_STALE_OPEN",
            "retry_unknown_or_failed": False,
            "global_terminal_stop_before_any_new_call": [
                "FAILED_PRE_SEND_NO_RETRY", "UNKNOWN_BILLED_POST_SEND",
            ],
            "new_call_order": "exact_first_preregistered_call_key_absent_from_WAL",
            "provider_boundary_invoke_serialized_in_process": True,
        },
        "receipt_pipeline": {
            "schema_version": "s277_c1_p1_receipt_pipeline_v1",
            "replica_receipt_schema": "s277_c1_p1_replica_receipt_v1",
            "replica_exact_top_level_keys": [
                "schema", "replica_key", "qid", "replica_id", "input",
                "run_identity", "effective_config",
                "retrieval", "rerank", "served_context", "structural_fetch",
                "coverage", "must_preserve", "provider", "answer",
                "answer_sha256", "generation_chain", "visual_assets", "render", "call_keys",
                "call_requests",
            ],
            "lineage": {
                "order": [
                    "embedding_response", "retrieval_pool", "rerank_response",
                    "rerank_prefix", "structural_fetch", "coverage_output",
                    "served_context", "synthesis_physical_payload", "answer",
                    "must_preserve", "telegram_renderer",
                ],
                "hash_algorithm": "sha256_canonical_json_or_sha256_utf8_as_typed",
                "effective_config_required": "coverage_c1_v1_and_must_preserve_true",
            },
            "input": {
                "exact_keys": [
                    "question", "target_models", "query_for_retrieval",
                    "available_models",
                ],
                "bind_to_population_row": {
                    "question": "question",
                    "target_models": "expected_target_models",
                    "query_for_retrieval": "question",
                    "available_models": "available_models",
                },
                "exact_match_required": True,
            },
            "generation_chain": {
                "exact_keys": [
                    "raw_payload_sha256", "raw_text", "raw_text_sha256",
                    "stages", "final_answer_sha256",
                ],
                "raw_payload_hash": "sha256_canonical_json(provider.raw_payload)",
                "raw_text_binding": "provider.raw_payload.content",
                "raw_text_hash": "sha256_utf8(raw_text)",
                "stage_order": [
                    "diagram_postprocess", "answer_planner", "must_preserve",
                ],
                "stage_exact_keys": [
                    "name", "input_sha256", "output_text", "output_sha256",
                ],
                "stage_linkage": "first_input=raw_text_sha256; each_next_input=previous_output_sha256",
                "stage_output_hash": "sha256_utf8(output_text)",
                "final_binding": "final_answer_sha256=answer_sha256=last_stage.output_sha256",
            },
            "provider_response": {
                "exact_top_level_keys": [
                    "requested_model", "reported_model", "stop_reason", "usage",
                    "response_id", "raw_payload",
                ],
                "top_level_to_raw_payload": {
                    "reported_model": "model",
                    "stop_reason": "stop_reason",
                    "usage": "usage",
                    "response_id": "id",
                },
                "requested_model_binding": "sealed_synthesis_envelope.model",
                "raw_payload_persisted_and_fsynced_before_parse": True,
                "raw_payload_sha256_binding": "generation_chain.raw_payload_sha256",
            },
            "render": {
                "parts_hash": "sha256_canonical_json(parts)",
                "parts_sha256_required": True,
                "source_answer_sha256_binding": "answer_sha256",
                "complete_source_rendered": True,
                "no_part_over_telegram_limit": 4096,
                "recompute_exactly_with": "src.bot.response_formatter.format_telegram_messages(answer)",
            },
            "visual_assets": {
                "derived_from": "target_semantic_config.generation.visual_assets_registry",
                "off_contract": "not_executed_with_empty_lookup_receipts_and_selected_assets",
                "on_contract": "evaluated_even_when_eligible_pages_is_empty",
                "on_relation": "public.document_visual_assets",
                "on_rest_method": "GET",
                "lookup_and_selection_hash_lineage_required": True,
            },
            "physical_call_envelope": {
                "exact_keys": [
                    "call_key", "provider", "model", "request",
                    "run_genesis_sha256", "lineage_input_sha256",
                    "input_tokens_upper_bound", "max_output_tokens", "max_retries",
                    "prompt_cache", "inference_geo", "service_tier",
                ],
                "common_request_exact_keys": [
                    "replica_key", "operation", "model", "run_genesis_sha256",
                    "lineage_input_sha256", "physical_payload",
                    "physical_payload_sha256",
                    "input_tokens_upper_bound", "max_output_tokens",
                ],
                "physical_payload_operation_specific": True,
                "physical_payload_hash_required": True,
                "max_retries": 0,
                "prompt_cache": False,
                "inference_geo": "global",
                "service_tier": "standard_sync",
                "input_bound_derivation": "len(canonical_json_bytes(physical_payload))+512",
                "provider_token_overhead_reserve": 512,
                "derived_bound_must_not_exceed": "cost.operations.<operation>.max_input_tokens",
                "output_bound_source": "cost.operations.<operation>.max_output_tokens",
                "reported_usage_must_be_present_nonnegative_and_within_bounds": True,
                "request_sha256_binding": "wal.RESERVED_FSYNCED.request_sha256",
                "post_prepare_pre_send_guards_exact": [
                    "fresh_runtime_identity",
                    "canonical_lease_ownership",
                    "reserved_request_sha256_unchanged",
                ],
                "fingerprint_and_fence_boundary_inputs_json_safe_deep_copied": True,
                "offline_gate_reopens_all_wal_physical_artifacts": True,
                "canonical_provider_response_path": "provider_responses/{sha256(call_key)}.json",
                "canonical_fence_watch_path": "fence_watches/{sha256(call_key)}.json",
                "physical_directories_exact_no_missing_or_extra": True,
                "offline_cross_binding": "replica.call_requests_and_observed_responses_to_WAL_and_physical_files",
                "offline_gate_revalidates_all_27_replica_receipts": True,
                "run_validation_snapshot": {
                    "materialization": "embedded_in_canonical_run_genesis_json",
                    "exact_components": [
                        "models", "input_contract", "budget_plan",
                        "implementation_hashes",
                    ],
                    "component_hashes_and_snapshot_hash_required": True,
                    "bound_in_result": [
                        "validation_snapshot_sha256",
                        "implementation_hashes_sha256",
                    ],
                },
                "score_finalize_current_implementation_must_equal_run_snapshot": True,
            },
            "replica_manifest": {
                "exact_order": "population.replica_order",
                "entry_exact_keys": ["replica_key", "path", "sha256"],
                "physical_file_sha256_required": True,
                "missing_extra_or_reordered": "HOLD_REPLICA_MANIFEST_DRIFT",
                "result_body_sealed_by_result_sha256": True,
            },
        },
        "cost": {
            "currency": "USD",
            "list_price_cap": 10.0,
            "free_tier_discount": False,
            "pricing_observed_on": "2026-07-20",
            "rates_per_million_tokens": {
                "claude_sonnet_4_6_input": 3.0,
                "claude_sonnet_4_6_output": 15.0,
                "voyage_4_large": 0.12,
                "voyage_rerank_2_5_if_selected": 0.05,
            },
            "official_urls": [
                "https://platform.claude.com/docs/en/about-claude/pricing",
                "https://docs.voyageai.com/docs/pricing",
            ],
            "static_bound_required_before_first_call": True,
            "prompt_cache_allowed": False,
            "inference_geo": "global",
            "service_tier": "standard_sync",
            "canary_budget_included": False,
            "adversarial_review_budget_included": False,
            "operations": budget_operations,
            "calls_per_operation": {"embedding": 27, "rerank": 27, "synthesis": 27},
            "static_worst_case_usd": "6.777",
            "replica_plan_sha256": replica_plan_sha256,
            "call_plan_sha256": call_plan_sha256,
            "invariant": "actual_observed + unknown_reservations + worst_case_remaining <= 10.00",
        },
        "corpus_fence": {
            "operator_identity_separate_from_runner": True,
            "runner_service_role_forbidden": True,
            "declared_surface_hashes_are_live_attestation": False,
            "live_rpc_signature_index_config_manifest_materialized": True,
            "product_cli_stop_line": None,
            "runner_identity": "p1_readonly",
            "persistent_session_postgres_not_transaction_pooler": True,
            "operator_ipc_boundary": "credential_free_append_only_single_use",
            "abort_protocol": "explicit_ipc_rollback_confirmed_or_ambiguous",
            "postgrest_guard": {
                "principal": "p1_readonly",
                "identity_rpc_bound_to_exact_jwt_sha256": True,
                "exact_get_rpc_allowlist": True,
                "write_methods_forbidden": True,
                "redirects_forbidden": True,
                "request_receipts_bound_per_replica": True,
            },
            "protocol": [
                "BEGIN_READ_COMMITTED_READ_ONLY",
                "SHARE_LOCKS_CANONICAL_ORDER_NOWAIT",
                "LIVE_MANIFEST_PRE",
                "INITIAL_FINGERPRINT",
                "27_REPLICAS_WITH_LIVE_MANIFEST_WATCH",
                "LIVE_MANIFEST_POST",
                "FINAL_FINGERPRINT_UNDER_LOCK",
                "COMMIT",
            ],
            "max_window_minutes": 45,
            "heartbeat_max_age_seconds": 30,
            "lock_mode": "ShareLock",
            "locks_granted_required": True,
            "relations_and_locks_order": "canonical_exact_same_open_close",
            "incompatible_waiters_required": [],
            "watch_immediately_inside_provider_boundary_before_prepare_and_send": True,
            "watch_absolute_heartbeat_age_required": "now-last_heartbeat_at<=heartbeat_max_age_seconds",
            "persisted_watch_historical_validation_at_score_finalize": True,
            "strong_watch_receipt_persisted_before_each_physical_send": True,
            "fingerprint_expiry_rechecked_before_each_provider_prepare": True,
            "base_relations_exact": [
                "public.chunks_v2", "public.chunks_v2_enunciados",
                "public.chunks_v2_hyq", "public.documents",
            ],
            "base_rpc_allowlist_exact": [
                "match_chunks_v2", "search_chunks_text_v2",
                "match_chunks_v2_enunciados", "match_hyq",
            ],
            "base_rest_get_allowlist_exact": [
                "public.chunks_v2", "public.documents",
            ],
            "visual_on_surface_extension": {
                "relation": "public.document_visual_assets",
                "rest_get": "public.document_visual_assets",
            },
            "query_logs_excluded": True,
            "function": "public.corpus_fingerprint_v1()",
            "audit_sql_sha256_lf": "285dd74a1463bb71a21ab9bfb5ea4053789d606ede9b90b640c14008c676dbda",
            "pg_get_functiondef_sha256": "1f280e0852158b63501aad2843a7e946ab9fac5a4c64a17851d6d63ed0e8ebca",
            "open_receipt_required_fields": [
                "schema", "status", "release_config_sha256", "initial_fingerprint",
                "persistent_session", "transaction_pooler", "backend_pid", "txid",
                "fence_owner", "opened_at", "last_heartbeat_at",
                "heartbeat_max_age_seconds", "deadline_at", "relations", "locks",
                "incompatible_waiters", "rpc_manifest_sha256",
                "physical_manifest_sha256", "live_manifest_contract_sha256",
            ],
            "close_receipt_required_fields": [
                "schema", "status", "release_config_sha256", "backend_pid", "txid",
                "fence_owner", "initial_fingerprint", "final_fingerprint",
                "verified_under_lock", "last_heartbeat_at",
                "final_fingerprint_taken_at", "relations", "locks",
                "incompatible_waiters", "rpc_manifest_sha256",
                "physical_manifest_sha256", "live_manifest_contract_sha256",
                "live_manifest_post_capture_sha256",
                "closed_at",
            ],
            "close_invariants": {
                "verified_under_lock": True,
                "final_fingerprint_equals_initial": True,
                "final_fingerprint_taken_before_or_at_closed_at": True,
                "heartbeat_fresh_at_final_fingerprint": True,
                "same_backend_txid_owner_relations_locks_and_manifests_as_open": True,
                "post_manifest_capture_hash_bound_to_close_receipt": True,
                "run_completed_before_close": True,
            },
            "loss_or_drift": "HOLD_CORPUS_FENCE_LOST",
        },
        "semantic_runtime_contract": {
            "schema_version": "s277_c1_semantic_runtime_contract_v1",
            "semantic_projection_schema": "s277_c1_semantic_effective_config_v1",
            "snapshot_freshness": {
                "max_age_seconds": SNAPSHOT_MAX_AGE_SECONDS,
                "future_skew_seconds": SNAPSHOT_FUTURE_SKEW_SECONDS,
                "validated_at": "every_preflight_and_immediately_before_first_paid_call",
            },
            "required_raw_env": SEMANTIC_ENV_CONSTS,
            "required_target_off_env": {
                name: "off" for name in TARGET_OFF_ENV_FLAGS
            },
            "code_bound_defaults_if_absent_from_raw_env": {
                **SEMANTIC_DEFAULT_ENV_CONSTS,
                "RETRIEVAL_TOP_K": 50,
                "LLM_MODEL": "claude-sonnet-4-6",
                "EMBEDDING_MODEL": "voyage-4-large",
            },
            "preserved_dynamic_env": {
                "VISUAL_ASSETS_REGISTRY": {
                    "allowed_raw_values": ["on", "off"],
                    "semantic_type": "boolean",
                    "bootstrap_policy": "preserve_exact",
                    "target_policy": "preserve_exact",
                },
            },
            "semantic_projection_exact_top_level_keys": [
                "schema", "corpus", "retrieval", "generation", "embedding", "coverage",
            ],
            "semantic_projection_exact_sections": {
                "corpus": ["chunks_table"],
                "retrieval": [
                    "retrieval_top_k", "rerank_top_k", "reranker_backend",
                    "reranker_model", "rerank_preview_chars", "merge_strategy",
                    "hyde_enabled", "enunciados_multivector", "hyq_table",
                    "hyq_pilot_file", "identity_resolve", "identity_resolve_policy",
                ],
                "generation": [
                    "model", "max_tokens", "temperature", "prompt_cache",
                    "prompt_variant", "selection_block", "must_preserve_contract",
                    "visual_assets_registry",
                ],
                "embedding": ["model"],
                "coverage": [
                    "release_profile", "post_rerank_coverage",
                    "structural_neighbor_coverage", "mandatory_callout",
                    "mandatory_verb_trigger",
                ],
            },
            "cross_field_equalities": [
                "live_snapshot.CHUNKS_TABLE == retrieval.chunks_table == semantic.corpus.chunks_table",
                "int(live_snapshot.RERANK_TOP_K) == retrieval.rerank_top_k == semantic.retrieval.rerank_top_k",
                "int(live_snapshot.LLM_MAX_TOKENS) == models.max_tokens == cost.operations.synthesis.max_output_tokens == semantic.generation.max_tokens",
                "effective(RERANKER_BACKEND,llm) == retrieval.reranker_backend == semantic.retrieval.reranker_backend",
                "retrieval.hyde_enabled == semantic.retrieval.hyde_enabled == false == strict_false(live_snapshot.HYDE_ENABLED)",
                "models.generator == semantic.generation.model == cost.operations.synthesis.model",
                "models.reranker == semantic.retrieval.reranker_model == cost.operations.rerank.model",
                "models.embedding == semantic.embedding.model == cost.operations.embedding.model",
                "models.temperature == semantic.generation.temperature == anthropic_request.temperature",
                "models.prompt_cache == semantic.generation.prompt_cache == physical_call_envelope.prompt_cache",
                "models.inference_geo == physical_call_envelope.inference_geo == cost.inference_geo",
                "models.service_tier == physical_call_envelope.service_tier == cost.service_tier",
            ],
            "raw_effective_hashes_preserved": True,
            "semantic_hashes_required": [
                "bootstrap_semantic_config_sha256",
                "target_semantic_config_sha256",
            ],
        },
        "release_identity": {
            "bootstrap_profile": "off",
            "p1_target_profile": "coverage_c1_v1",
            "only_activation_transition": "COVERAGE_RELEASE_PROFILE:off->coverage_c1_v1",
            "legacy_flags_to_delete": ["POST_RERANK_COVERAGE", "STRUCTURAL_NEIGHBOR_COVERAGE", "COVERAGE_MANDATORY_CALLOUT", "MP_MANDATORY_VERB_TRIGGER"],
            "preserved_orthogonal_flags": {
                "VISUAL_ASSETS_REGISTRY": {
                    "allowed_values": ["on", "off"],
                    "source_path": "railway.live_snapshot.VISUAL_ASSETS_REGISTRY",
                    "bootstrap_policy": "preserve_exact",
                    "target_policy": "preserve_exact",
                    "profile_owned": False,
                },
            },
            "target_invariants": {"MUST_PRESERVE_CONTRACT": "on", "HYDE_ENABLED": "false", "only_structural_coverage_lane": True},
            "ttl_hours": 6,
            "squash_or_rebase_without_tested_lineage": "EXPIRE_P1",
            "different_merge_commit_allowed_only_with_same_tree_manifest_and_lineage": True,
        },
        "scoring": {
            "fact_contract_base_count": 43,
            "hp017_target_separate": True,
            "other_qids_required": "2/2 per applicable fact",
            "hp017_required": "3/3 base facts + compound target + no menu conflict",
            "hp013_guard_required_despite_zero_facts": True,
            "all_response_citations_syntax_range_identity_valid": True,
            "factual_entailment_scope": "protected_packet_guards_registered_conflicts_and_hp017_target_only",
            "states": ["PASS", "FAIL", "REVIEW", "INSTRUMENT_ERROR"],
            "review_blocks_go": True,
            "finalize_review_only_with_blind_hash_bound_human_adjudication": True,
        },
        "known_prepaid_hold": {
            "code": "HOLD_PREPAID_KNOWN_CONFLICT_RISK",
            "conflict_id": "conf_26f63590494f",
            "zero_usd_stored_control_first": True,
            "later_permit_must_explicitly_accept_prior_to_measure": True,
            "recommended_resolution": "fix_or_disclose_menu_source_conflict_before_paid_measurement",
        },
        "go": {
            "complete_generations": "27/27",
            "base_facts": "all applicable rows in every replica",
            "hp017_target": "3/3 exact compound warnings with local citations",
            "unresolved_review": 0,
            "invalid_citations": 0,
            "truncations": 0,
            "orphan_calls": 0,
            "claim": "NO_OBSERVED_PROTECTED_LOSS_IN_P1_RUNS",
        },
        "current_stop_lines": [
            "HOLD_RELEASE_CONFIG_NOT_MATERIALIZED",
            "HOLD_P1_READONLY_IDENTITY_NOT_PROVISIONED",
            "HOLD_CORPUS_FENCE_OPERATOR_NOT_AUTHORIZED",
            "HOLD_LIVE_MANIFEST_NOT_CAPTURED",
            "HOLD_PREPAID_KNOWN_CONFLICT_RISK",
            "HOLD_PAID_EXECUTION_NOT_AUTHORIZED",
        ],
    }


def write_outputs() -> None:
    contract = build_fact_contract()
    fact_path = EVALS / "s277_c1_p1_fact_contract_v1.json"
    fact_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    release_schema = build_release_config_schema()
    schema_path = EVALS / "s277_c1_p1_release_config_schema_v1.json"
    schema_path.write_text(json.dumps(release_schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    prereg = build_prereg(contract, release_schema)
    prereg_path = EVALS / "s277_c1_p1_prereg_v1.yaml"
    prereg_path.write_text(
        yaml.safe_dump(prereg, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8", newline="\n",
    )


if __name__ == "__main__":
    write_outputs()
