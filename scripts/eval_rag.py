"""
RAG Evaluation Framework for Technical Bot PCI.

Runs a structured set of test queries against the retrieval + generation pipeline
and measures quality metrics by manufacturer, category, and query type.

Usage:
    python -m scripts.eval_rag                    # Run full eval
    python -m scripts.eval_rag --retrieval-only   # Skip LLM generation (faster, cheaper)
    python -m scripts.eval_rag --category "Centrales de incendios"  # Filter by category
    python -m scripts.eval_rag --manufacturer Detnov                # Filter by manufacturer
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.retriever import retrieve_chunks, extract_product_models
from src.rag.reranker import rerank_chunks
from src.rag.generator import generate_answer

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Test case definition
# ---------------------------------------------------------------------------

@dataclass
class EvalCase:
    """A single evaluation test case."""
    id: str
    query: str
    # Expected outcomes
    expected_manufacturer: str | None = None      # "Detnov", "Notifier", or None (any)
    expected_model: str | None = None              # e.g. "CAD-150-8"
    expected_category: str | None = None           # e.g. "Centrales de incendios"
    expected_content_type: str | None = None       # e.g. "specification", "wiring"
    expected_keywords: list[str] = field(default_factory=list)  # Keywords that MUST appear in answer
    forbidden_keywords: list[str] = field(default_factory=list)  # Keywords that must NOT appear
    # Document-management refactor (Phase 6):
    must_cite_source: bool = True                  # Answer MUST contain a "Fuente:" line
    forbidden_source_files: list[str] = field(default_factory=list)
        # Source files that MUST NOT appear in cited sources (used for supersede
        # trap questions — once two revisions of a doc exist, a question targeting
        # that doc should never cite the superseded rev).
    expected_revision: str | None = None
        # Optional: the exact revision string that should be cited. Use sparingly,
        # only for trap questions where we know the expected answer lives in a
        # specific revision of a specific manual.
    # Metadata
    query_type: str = "general"                    # specs | installation | troubleshooting | comparison | generic | error_handling | supersede_trap
    manufacturer_scope: str = "single"             # single | multi | any
    notes: str = ""


@dataclass
class EvalResult:
    """Result of evaluating a single test case."""
    case_id: str
    query: str
    query_type: str
    # Retrieval metrics
    retrieval_hit: bool = False           # At least one chunk from expected model/manufacturer
    category_correct: bool = False        # Top chunk has expected category
    manufacturer_correct: bool = False    # Top chunk has expected manufacturer
    model_correct: bool = False           # Top chunk has expected model
    content_type_match: bool = False      # At least one chunk has expected content_type
    num_chunks_retrieved: int = 0
    num_manufacturers_in_results: int = 0
    top_similarity: float = 0.0
    # Generation metrics (optional)
    keywords_found: list[str] = field(default_factory=list)
    keywords_missing: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    answer_length: int = 0
    # Document-management checks (Phase 6)
    has_citation: bool = False                   # Answer has a "Fuente:" line
    cited_sources: list[str] = field(default_factory=list)  # Files mentioned in citation
    forbidden_sources_cited: list[str] = field(default_factory=list)
    revision_cited: bool = False                 # Citation includes a rev/Iss/date token
    expected_revision_found: bool = False        # If expected_revision set, was it cited
    # Timing
    retrieval_ms: int = 0
    total_ms: int = 0
    # Raw data for debugging
    top_chunks_summary: list[str] = field(default_factory=list)
    answer_preview: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

EVAL_CASES: list[EvalCase] = [
    # ==========================================
    # DETNOV — Model-specific queries
    # ==========================================
    EvalCase(
        id="D-01",
        query="¿Cuál es la tensión de alimentación del CAD-150-8?",
        expected_manufacturer="Detnov",
        expected_model="CAD-150-8",
        expected_category="Centrales de incendios",
        expected_content_type="specification",
        expected_keywords=["tensión", "V"],
        query_type="specs",
    ),
    EvalCase(
        id="D-02",
        query="¿Cómo se conecta el módulo MAD-472 al lazo?",
        expected_manufacturer="Detnov",
        expected_model="MAD-472",
        expected_category="Módulos de lazo",
        expected_content_type="wiring",
        expected_keywords=["conexión", "lazo"],
        query_type="installation",
    ),
    EvalCase(
        id="D-03",
        query="El detector DGD-600 parpadea en rojo, ¿qué significa?",
        expected_manufacturer="Detnov",
        expected_model="DGD-600",
        expected_category="Detectores puntuales",
        expected_content_type="troubleshooting",
        expected_keywords=["LED", "rojo"],
        query_type="troubleshooting",
    ),
    EvalCase(
        id="D-04",
        query="¿Qué resistencia de final de línea usa la CAD-150?",
        expected_manufacturer="Detnov",
        expected_model="CAD-150-8",
        expected_category="Centrales de incendios",
        expected_keywords=["resistencia"],
        query_type="specs",
    ),
    EvalCase(
        id="D-05",
        query="¿Cuántos dispositivos soporta un lazo de la CAD-150-8?",
        expected_manufacturer="Detnov",
        expected_model="CAD-150-8",
        expected_category="Centrales de incendios",
        expected_keywords=["dispositivo", "lazo"],
        query_type="specs",
    ),
    EvalCase(
        id="D-06",
        query="Procedimiento de mantenimiento del MAD-461",
        expected_manufacturer="Detnov",
        expected_model="MAD-461",
        expected_category="Módulos de lazo",
        query_type="installation",
    ),
    EvalCase(
        id="D-07",
        query="Especificaciones de la fuente FAD-905",
        expected_manufacturer="Detnov",
        expected_model="FAD-905",
        expected_category="Fuentes de alimentación",
        expected_content_type="specification",
        query_type="specs",
    ),

    # ==========================================
    # NOTIFIER — Model-specific queries
    # ==========================================
    EvalCase(
        id="N-01",
        query="¿Cuáles son las especificaciones técnicas de la central NFS Supra?",
        expected_manufacturer="Notifier",
        expected_model="NFS Supra",
        expected_category="Centrales de incendios",
        expected_content_type="specification",
        query_type="specs",
    ),
    EvalCase(
        id="N-02",
        query="¿Cómo se instala el detector SMART 3?",
        expected_manufacturer="Notifier",
        expected_model="SMART 3",
        expected_category="Detectores puntuales",
        expected_keywords=["instalación"],
        query_type="installation",
    ),
    EvalCase(
        id="N-03",
        query="Configuración de sensibilidad del FAAST XM",
        expected_manufacturer="Notifier",
        expected_model="FAAST XM",
        expected_category="Detectores de aspiración",
        expected_keywords=["sensibilidad"],
        query_type="installation",
    ),
    EvalCase(
        id="N-04",
        query="¿Qué detectores lineales tiene Notifier? Necesito el FS24X",
        expected_manufacturer="Notifier",
        expected_model="FS24X",
        expected_category="Detectores lineales",
        query_type="specs",
    ),
    EvalCase(
        id="N-05",
        query="Conexionado del detector VESDA VLF-500",
        expected_manufacturer="Notifier",
        expected_model="VESDA VLF-500",
        expected_category="Detectores de aspiración",
        expected_content_type="wiring",
        query_type="installation",
    ),
    EvalCase(
        id="N-06",
        query="Fallo en el SMART 3G, LED ámbar fijo",
        expected_manufacturer="Notifier",
        expected_model="SMART 3G",
        expected_category="Detectores puntuales",
        query_type="troubleshooting",
    ),

    # ==========================================
    # MORLEY — Model-specific queries
    # ==========================================
    EvalCase(
        id="M-01",
        query="¿Cómo se configura un bucle en la central DXc?",
        expected_manufacturer="Morley",
        expected_model="DXc",
        expected_category="Centrales de incendios",
        expected_keywords=["bucle", "configura"],
        query_type="installation",
        notes="DXc = central direccionable Morley (Honeywell)",
    ),
    EvalCase(
        id="M-02",
        query="¿Qué distancia máxima cubre el detector de haz óptico F5000?",
        expected_manufacturer="Morley",
        expected_model="F5000",
        expected_category="Detectores lineales",
        expected_keywords=["distancia", "metros"],
        query_type="specs",
    ),
    EvalCase(
        id="M-03",
        query="Diferencia entre las centrales ZXe y ZXSe de Morley",
        expected_manufacturer="Morley",
        expected_category="Centrales de incendios",
        expected_keywords=["ZXe", "ZXSe"],
        query_type="comparison",
        notes="ZXe convencional vs ZXSe, ambas Morley",
    ),

    # ==========================================
    # GENERIC — Category queries (multi-manufacturer)
    # ==========================================
    EvalCase(
        id="G-01",
        query="¿Qué detectores de aspiración tenéis?",
        expected_category="Detectores de aspiración",
        query_type="generic",
        manufacturer_scope="multi",
        notes="Should list models from both Detnov and Notifier",
    ),
    EvalCase(
        id="G-02",
        query="Necesito información sobre sirenas de alarma",
        expected_category="Sirenas y balizas",
        query_type="generic",
        manufacturer_scope="multi",
    ),
    EvalCase(
        id="G-03",
        query="¿Qué centrales de incendio tenéis disponibles?",
        expected_category="Centrales de incendios",
        query_type="generic",
        manufacturer_scope="multi",
    ),
    EvalCase(
        id="G-04",
        query="Módulos aisladores disponibles",
        expected_category="Módulos de lazo",
        query_type="generic",
        manufacturer_scope="multi",
    ),
    EvalCase(
        id="G-05",
        query="¿Cómo se instala un detector de humo?",
        expected_category="Detectores puntuales",
        query_type="generic",
        manufacturer_scope="any",
    ),

    # ==========================================
    # COMPARISON — Cross-manufacturer
    # ==========================================
    EvalCase(
        id="C-01",
        query="¿Qué diferencias hay entre el CAD-150-8 y la NFS Supra?",
        expected_category="Centrales de incendios",
        expected_keywords=["CAD-150", "NFS Supra"],
        query_type="comparison",
        manufacturer_scope="multi",
    ),
    EvalCase(
        id="C-02",
        query="Comparar detectores de aspiración Detnov ASD533 y Notifier FAAST XM",
        expected_category="Detectores de aspiración",
        expected_keywords=["ASD533", "FAAST"],
        query_type="comparison",
        manufacturer_scope="multi",
    ),

    # ==========================================
    # ERROR HANDLING — Edge cases
    # ==========================================
    EvalCase(
        id="E-01",
        query="Especificaciones del MAD-472 de Notifier",
        expected_manufacturer="Detnov",
        expected_model="MAD-472",
        notes="MAD-472 is Detnov, not Notifier — bot should correct",
        query_type="error_handling",
    ),
    EvalCase(
        id="E-02",
        query="¿Tenéis manuales de Siemens?",
        notes="Siemens not in DB — bot should list available manufacturers",
        query_type="error_handling",
        forbidden_keywords=["especificaciones", "se instala"],
    ),
    EvalCase(
        id="E-03",
        query="detector",
        notes="Ultra-vague query — bot should ask for model/context",
        query_type="error_handling",
    ),
    EvalCase(
        id="E-04",
        query="¿Cómo instalo el XYZ-999?",
        notes="Non-existent model — bot should say not found + offer alternatives",
        query_type="error_handling",
        forbidden_keywords=["se instala conectando", "procedimiento de instalación"],
    ),

    # ==========================================
    # URGENCY
    # ==========================================
    EvalCase(
        id="U-01",
        query="La sirena no para de sonar, ¿cómo la silencio? Es una CAD-150-8",
        expected_manufacturer="Detnov",
        expected_model="CAD-150-8",
        expected_keywords=["silenciar"],
        query_type="troubleshooting",
        notes="Urgent — should give immediate action first",
    ),

    # ==========================================
    # SUPERSEDE TRAPS (Phase 6 of document-management refactor)
    # ==========================================
    # These are PLACEHOLDER examples documenting how to write supersede-trap
    # test cases. They will only fire meaningfully when two revisions of the
    # same document exist in the `documents` table — one 'active' and one
    # 'superseded'. Enable/update them as supersede chains populate.
    #
    # HOW TO WRITE A TRAP QUESTION:
    #   1. Identify a manual that has two or more revisions in the DB
    #      (e.g. AM-8200N rev 3 AND rev 4).
    #   2. Pick a spec or procedure that EXISTS in both revs but with
    #      different wording/values, OR that only exists in the newer rev.
    #   3. Write a query that targets that spec.
    #   4. Set `forbidden_source_files=["OLD_FILENAME.pdf"]` so the eval
    #      asserts the cited source is NOT the old rev.
    #   5. Optionally set `expected_revision="Rev 4"` to demand the exact
    #      revision label in the citation.
    #
    # Example (commented out until AM-8200N has 2 revs in DB):
    # EvalCase(
    #     id="T-01",
    #     query="¿Cuál es el consumo en reposo del AM-8200N?",
    #     expected_manufacturer="Notifier",
    #     expected_model="AM-8200N",
    #     query_type="supersede_trap",
    #     must_cite_source=True,
    #     expected_revision="4",
    #     forbidden_source_files=["AM-8200N manual instalacion RV 3"],
    #     notes="Must cite rev 4 (active), not rev 3 (superseded).",
    # ),
]


# ---------------------------------------------------------------------------
# Evaluation engine
# ---------------------------------------------------------------------------

def evaluate_case(case: EvalCase, retrieval_only: bool = False) -> EvalResult:
    """Run a single evaluation case and measure metrics."""
    result = EvalResult(
        case_id=case.id,
        query=case.query,
        query_type=case.query_type,
    )

    try:
        # Step 1: Retrieval
        t0 = time.time()
        chunks = retrieve_chunks(case.query, top_k=15)
        t_retrieval = time.time()
        result.retrieval_ms = int((t_retrieval - t0) * 1000)
        result.num_chunks_retrieved = len(chunks)

        if not chunks:
            result.error = "No chunks retrieved"
            result.total_ms = result.retrieval_ms
            return result

        # Retrieval metrics
        manufacturers_in_results = set(c.get("manufacturer", "") for c in chunks)
        result.num_manufacturers_in_results = len(manufacturers_in_results - {""})
        result.top_similarity = chunks[0].get("similarity", 0)

        # Top chunk checks
        top = chunks[0]
        if case.expected_category:
            result.category_correct = top.get("category") == case.expected_category
        else:
            result.category_correct = True  # No expectation

        if case.expected_manufacturer:
            result.manufacturer_correct = top.get("manufacturer") == case.expected_manufacturer
            result.retrieval_hit = any(
                c.get("manufacturer") == case.expected_manufacturer for c in chunks
            )
        else:
            result.manufacturer_correct = True
            result.retrieval_hit = True

        if case.expected_model:
            result.model_correct = any(
                c.get("product_model") == case.expected_model for c in chunks[:5]
            )
        else:
            result.model_correct = True

        if case.expected_content_type:
            result.content_type_match = any(
                c.get("content_type") == case.expected_content_type for c in chunks
            )
        else:
            result.content_type_match = True

        # Top chunks summary for debugging
        for c in chunks[:5]:
            result.top_chunks_summary.append(
                f"[{c.get('similarity', 0):.2f}] {c.get('manufacturer', '?')} | "
                f"{c.get('product_model', '?')} | {c.get('category', '?')} | "
                f"{c.get('content_type', '?')}"
            )

        if retrieval_only:
            result.total_ms = result.retrieval_ms
            return result

        # Step 2: Rerank
        models = extract_product_models(case.query)
        reranked = rerank_chunks(case.query, chunks, top_k=5, target_models=models)

        # Step 3: Generate
        gen_result = generate_answer(case.query, reranked)
        t_total = time.time()
        result.total_ms = int((t_total - t0) * 1000)

        answer = gen_result.get("answer", "")
        result.answer_length = len(answer)
        result.answer_preview = answer[:300]

        # Keyword checks
        answer_lower = answer.lower()
        for kw in case.expected_keywords:
            if kw.lower() in answer_lower:
                result.keywords_found.append(kw)
            else:
                result.keywords_missing.append(kw)

        for kw in case.forbidden_keywords:
            if kw.lower() in answer_lower:
                result.forbidden_found.append(kw)

        # --- Citation checks (Phase 6 of document-management refactor) ---
        # The generator prompt mandates a "Fuente:" (or "Fuentes:") line at the
        # end of every technical answer, including the manual name and
        # (when available) the revision / date.
        import re as _re_cite
        citation_match = _re_cite.search(
            r"Fuentes?:\s*(.+?)(?:\n\n|\Z)", answer, _re_cite.DOTALL
        )
        if citation_match:
            result.has_citation = True
            citation_text = citation_match.group(1).strip()
            # Revision token heuristic: "rev.", "Rev", "Iss", or a 4-digit year
            if _re_cite.search(r"(?:rev\.|Rev |Iss |20\d{2})", citation_text, _re_cite.I):
                result.revision_cited = True
            # Extract plausible source-file mentions for the forbidden check
            # (anything between "Fuente:" and "(" or end-of-segment).
            for piece in _re_cite.split(r"[;\n]", citation_text):
                cleaned = _re_cite.sub(r"\(.+?\)", "", piece).strip()
                if cleaned:
                    result.cited_sources.append(cleaned)
            # Forbidden source files (supersede trap)
            for fs in case.forbidden_source_files:
                if fs.lower() in citation_text.lower():
                    result.forbidden_sources_cited.append(fs)
            # Expected revision match (optional)
            if case.expected_revision:
                if case.expected_revision.lower() in citation_text.lower():
                    result.expected_revision_found = True

    except Exception as e:
        result.error = str(e)
        logger.error(f"Case {case.id} failed: {e}")

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(results: list[EvalResult], cases: list[EvalCase]):
    """Print a summary report of eval results."""
    total = len(results)
    if total == 0:
        print("No results.")
        return

    # Overall metrics
    retrieval_hits = sum(1 for r in results if r.retrieval_hit)
    category_correct = sum(1 for r in results if r.category_correct)
    manufacturer_correct = sum(1 for r in results if r.manufacturer_correct)
    model_correct = sum(1 for r in results if r.model_correct)
    content_type_match = sum(1 for r in results if r.content_type_match)
    errors = sum(1 for r in results if r.error)

    print("\n" + "=" * 70)
    print("RAG EVALUATION REPORT")
    print("=" * 70)

    print(f"\nOverall ({total} cases):")
    print(f"  Retrieval hit rate:     {retrieval_hits}/{total} ({retrieval_hits/total*100:.0f}%)")
    print(f"  Category accuracy:      {category_correct}/{total} ({category_correct/total*100:.0f}%)")
    print(f"  Manufacturer accuracy:  {manufacturer_correct}/{total} ({manufacturer_correct/total*100:.0f}%)")
    print(f"  Model accuracy:         {model_correct}/{total} ({model_correct/total*100:.0f}%)")
    print(f"  Content type match:     {content_type_match}/{total} ({content_type_match/total*100:.0f}%)")
    print(f"  Errors:                 {errors}/{total}")

    # Timing
    retrieval_times = [r.retrieval_ms for r in results if not r.error]
    total_times = [r.total_ms for r in results if not r.error and r.total_ms > 0]
    if retrieval_times:
        print(f"\n  Retrieval latency:  avg={sum(retrieval_times)//len(retrieval_times)}ms  "
              f"p95={sorted(retrieval_times)[int(len(retrieval_times)*0.95)]}ms")
    if total_times:
        print(f"  Total latency:      avg={sum(total_times)//len(total_times)}ms  "
              f"p95={sorted(total_times)[int(len(total_times)*0.95)]}ms")

    # By query type
    print("\nBy query type:")
    query_types = set(r.query_type for r in results)
    for qt in sorted(query_types):
        qt_results = [r for r in results if r.query_type == qt]
        qt_hits = sum(1 for r in qt_results if r.retrieval_hit)
        qt_cat = sum(1 for r in qt_results if r.category_correct)
        qt_mfr = sum(1 for r in qt_results if r.manufacturer_correct)
        n = len(qt_results)
        print(f"  {qt:20s}  hit={qt_hits}/{n}  cat={qt_cat}/{n}  mfr={qt_mfr}/{n}")

    # By manufacturer
    print("\nBy expected manufacturer:")
    for mfr in ["Detnov", "Notifier", "Morley", None]:
        mfr_cases = [c for c in cases if c.expected_manufacturer == mfr]
        mfr_ids = {c.id for c in mfr_cases}
        mfr_results = [r for r in results if r.case_id in mfr_ids]
        if mfr_results:
            n = len(mfr_results)
            hits = sum(1 for r in mfr_results if r.retrieval_hit)
            cats = sum(1 for r in mfr_results if r.category_correct)
            label = mfr or "Any/Multi"
            print(f"  {label:20s}  hit={hits}/{n}  cat={cats}/{n}")

    # Multi-manufacturer diversity
    multi_cases = [c for c in cases if c.manufacturer_scope == "multi"]
    multi_ids = {c.id for c in multi_cases}
    multi_results = [r for r in results if r.case_id in multi_ids]
    if multi_results:
        multi_diverse = sum(1 for r in multi_results if r.num_manufacturers_in_results >= 2)
        n = len(multi_results)
        print(f"\nMulti-manufacturer diversity: {multi_diverse}/{n} queries returned 2+ manufacturers")

    # Failures detail
    failures = [r for r in results if not r.retrieval_hit or not r.category_correct or r.error]
    if failures:
        print(f"\n{'='*70}")
        print("FAILURES & ISSUES:")
        print("=" * 70)
        for r in failures:
            issues = []
            if not r.retrieval_hit:
                issues.append("NO_HIT")
            if not r.category_correct:
                issues.append("WRONG_CAT")
            if not r.manufacturer_correct:
                issues.append("WRONG_MFR")
            if not r.model_correct:
                issues.append("WRONG_MODEL")
            if r.error:
                issues.append(f"ERROR: {r.error[:80]}")
            if r.keywords_missing:
                issues.append(f"MISSING_KW: {r.keywords_missing}")
            if r.forbidden_found:
                issues.append(f"FORBIDDEN: {r.forbidden_found}")

            print(f"\n  [{r.case_id}] {r.query}")
            print(f"    Issues: {', '.join(issues)}")
            if r.top_chunks_summary:
                print(f"    Top chunk: {r.top_chunks_summary[0]}")

    # Generation quality (if available)
    gen_results = [r for r in results if r.answer_length > 0]
    if gen_results:
        print(f"\n{'='*70}")
        print("GENERATION QUALITY:")
        print("=" * 70)
        kw_cases = [r for r in gen_results if r.keywords_found or r.keywords_missing]
        if kw_cases:
            total_kw = sum(len(r.keywords_found) + len(r.keywords_missing) for r in kw_cases)
            found_kw = sum(len(r.keywords_found) for r in kw_cases)
            print(f"  Keywords found: {found_kw}/{total_kw} ({found_kw/total_kw*100:.0f}%)")
        forbidden_violations = [r for r in gen_results if r.forbidden_found]
        if forbidden_violations:
            print(f"  Forbidden keyword violations: {len(forbidden_violations)}")
            for r in forbidden_violations:
                print(f"    [{r.case_id}] Found: {r.forbidden_found}")

        avg_len = sum(r.answer_length for r in gen_results) // len(gen_results)
        print(f"  Average answer length: {avg_len} chars")

        # Citation / document-management checks (Phase 6)
        print(f"\n{'='*70}")
        print("CITATION & DOCUMENT LIFECYCLE:")
        print("=" * 70)
        cite_cases = [
            r for r in gen_results
            if next((c for c in cases if c.id == r.case_id), None) is not None
            and next(c for c in cases if c.id == r.case_id).must_cite_source
        ]
        if cite_cases:
            with_cite = sum(1 for r in cite_cases if r.has_citation)
            with_rev = sum(1 for r in cite_cases if r.revision_cited)
            print(
                f"  Answers with 'Fuente:' line: "
                f"{with_cite}/{len(cite_cases)} ({with_cite/len(cite_cases)*100:.0f}%)"
            )
            print(
                f"  Citations including revision:  "
                f"{with_rev}/{len(cite_cases)} ({with_rev/len(cite_cases)*100:.0f}%)"
            )
            missing_cite = [r for r in cite_cases if not r.has_citation]
            if missing_cite:
                print(f"  ⚠ {len(missing_cite)} answer(s) missing Fuente: line:")
                for r in missing_cite[:5]:
                    print(f"    [{r.case_id}] {r.query[:70]}")

        # Supersede trap: forbidden sources cited
        trap_violations = [r for r in gen_results if r.forbidden_sources_cited]
        if trap_violations:
            print(f"\n  ⚠ SUPERSEDE TRAP VIOLATIONS ({len(trap_violations)}):")
            print("  These answers cited a superseded/forbidden source — lifecycle")
            print("  filtering is NOT working correctly. Investigate documents table.")
            for r in trap_violations:
                print(f"    [{r.case_id}] cited: {r.forbidden_sources_cited}")

        # Expected-revision trap
        exp_rev_cases = [
            r for r in gen_results
            if next((c for c in cases if c.id == r.case_id and c.expected_revision), None)
        ]
        if exp_rev_cases:
            exp_rev_hit = sum(1 for r in exp_rev_cases if r.expected_revision_found)
            print(
                f"\n  Expected-revision citations: "
                f"{exp_rev_hit}/{len(exp_rev_cases)} correct"
            )


def save_results(results: list[EvalResult], output_path: str):
    """Save detailed results to JSON for further analysis."""
    data = [asdict(r) for r in results]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Results saved to {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Framework")
    parser.add_argument("--retrieval-only", action="store_true",
                        help="Only test retrieval, skip LLM generation (faster, cheaper)")
    parser.add_argument("--category", type=str, default=None,
                        help="Filter test cases by expected category")
    parser.add_argument("--manufacturer", type=str, default=None,
                        help="Filter test cases by expected manufacturer")
    parser.add_argument("--case", type=str, default=None,
                        help="Run a single case by ID (e.g. D-01)")
    parser.add_argument("--output", type=str, default="eval_results.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    # Filter cases
    cases = EVAL_CASES
    if args.case:
        cases = [c for c in cases if c.id == args.case]
    if args.category:
        cases = [c for c in cases if c.expected_category and args.category.lower() in c.expected_category.lower()]
    if args.manufacturer:
        cases = [c for c in cases if c.expected_manufacturer and args.manufacturer.lower() in c.expected_manufacturer.lower()]

    if not cases:
        print("No matching test cases found.")
        return

    mode = "RETRIEVAL ONLY" if args.retrieval_only else "FULL (retrieval + rerank + generation)"
    print(f"Running {len(cases)} eval cases — mode: {mode}")
    print("-" * 70)

    results = []
    for i, case in enumerate(cases):
        logger.info(f"[{i+1}/{len(cases)}] {case.id}: {case.query[:60]}...")
        result = evaluate_case(case, retrieval_only=args.retrieval_only)
        results.append(result)

        # Quick status
        status = "OK" if (result.retrieval_hit and result.category_correct and not result.error) else "FAIL"
        logger.info(f"  → {status} | hit={result.retrieval_hit} cat={result.category_correct} "
                     f"mfr={result.manufacturer_correct} model={result.model_correct} "
                     f"| {result.retrieval_ms}ms")

    # Report
    print_report(results, cases)

    # Save detailed results
    save_results(results, args.output)


if __name__ == "__main__":
    main()
