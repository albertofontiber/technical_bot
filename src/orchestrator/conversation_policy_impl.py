"""Deterministic conversational policy — MT-1a (S281 / Phase 1).

This is the concrete ``ConversationPolicy`` the frozen interface
(``conversation_policy.py``) declares. It is a **deterministic router in cascade**
with a traceable rationale per decision; the economical rewriter
(``rewriter.py``) is invoked ONLY on the narrow anaphora slice the router cannot
resolve by re-attaching the last product. Everything else is $0.

THE CASCADE (order matters — first match wins):

  A. EXPLICIT PRODUCT in this turn (``turn_models`` minus ``NON_PRODUCT_CODES``
     and normative/standards codes) -> STANDALONE. The explicit product WINS over
     working state (design §5); a self-correction ("me refería a la X") therefore
     REPLACES the state, never unions it.
  B. BRAND named (no in-corpus model resolved) -> deterministic split:
       * SAME manufacturer as the state -> not a switch, fall through to C/D.
       * brand + model-type token (e.g. "la Bosch Avenar FPA-1200") -> STANDALONE,
         target=() (new product, drop stale state; downstream admits).
       * brand alone, in-window (e.g. "¿es compatible con Hochiki?") -> CARRY_FORWARD
         (a compatibility follow-up about the state product).
       * brand alone, no usable state -> STANDALONE, target=() (new topic).
     Catalog-aware brand gate (vara §7.3, DEC-069 dependency).
  C. OUT-OF-DOMAIN lexicon (conservative gas-outside-fire gate, S99) -> DECLINE.
     Runs AFTER A/B and ONLY when NOT an in-window continuation, so neither an
     in-corpus gas *detector* (DGD-600, branch A) nor an in-window follow-up that
     mentions gas (a boiler-cutoff maneuver from a fire panel) is ever declined.
  D. IN-WINDOW STATE present (product-less follow-up within 1h) -> continuation:
       E. family umbrella + question on the family's DIVERGENT axis (real
          divergence, catalog/GT-anchored) and NOT an invariant attribute
          -> CLARIFY (s79/s80: clarify ONLY on real divergence; an invariant
          answer is ``answer``, never a reflexive clarify).
       F. content anaphora ("ese aviso" / "esos avisos" / "este módulo") the
          re-attach cannot resolve -> REWRITE (requires_llm_rewrite=True). With
          ``rewrite=None`` (contract mode) it DEFERS (rewritten_query=None, no
          fabrication). With a rewriter injected it calls it; a fail-closed
          rewrite (None) falls back to CLARIFY of the antecedent (not
          carry_forward: the cascade already judged the re-attach insufficient,
          so retrieving on the ambiguous query is unsafe; $-spent, declared).
       G. else -> CARRY_FORWARD ($0): the raw query is preserved VERBATIM and a
          model hint is APPENDED (never substituted).
  H. NO in-window state (empty or expired) + a dependency signal (dangling
     pronoun/ellipsis, e.g. the 70-min "¿y cuál es su tensión?") -> CLARIFY.
  I. NO in-window state + genuinely self-contained (no dependency signal)
     -> STANDALONE (let retrieval + generator handle it; avoids clarify-indebido).

The composition seam ``resolve_conversational_turn`` wires
``extract_product_models`` + this policy into ``(TurnResolution, new WorkingState)``
— what the bot activation (MT-0d, orchestrator + Alberto) will drive. This module
performs NO I/O and NO LLM call itself; the rewriter is the injected callable.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from .conversation_policy import (
    NON_PRODUCT_CODES,
    PolicyRoute,
    RewriteFn,
    TurnIdentity,
    TurnResolution,
    WorkingState,
)
# (s332 §2) La primitiva de asunción vive en `contracts`, que desde E1-s332 NO
# importa nada de la política (su `TurnIdentity` es anotación diferida): este
# import no añade aristas al SCC permitido `conversation_policy ↔ _impl` y
# `test_import_contract` lo vigila. (El razonamiento original de este comentario
# —«contracts importa la interfaz, sin ciclo»— era falso: el analizador cuenta
# también los imports lazy y la arista contracts→policy SÍ cerraba ciclo; la
# corrección de raíz fue cortarla en contracts.)
from .contracts import Asuncion

WINDOW_SECONDS = 3600  # carry-forward-1h (telegram_bot SESSION_TIMEOUT); design §8


# ---------------------------------------------------------------------------
# (s331 §3.C.1) F1_MENTION_PRECEDENCE — precedencia de mención + gramática
# ---------------------------------------------------------------------------
def mention_precedence_enabled() -> bool:
    """Flag propio de la rama de precedencia de mención (default off = byte-idéntico).
    Su único call-site vive en la composición F1, así que no necesita interlock con
    la política (si F1 no corre, la rama no existe); y NO exige F1_RESOLVE_GOVERNED
    — G1c mide C-solo con A apagado (atribución por brazo, v6 §4)."""
    raw = (os.getenv("F1_MENTION_PRECEDENCE", "") or "").strip().lower()
    if raw not in ("", "0", "false", "no", "off", "1", "true", "yes", "on"):
        raise RuntimeError(
            f"F1_MENTION_PRECEDENCE={raw!r} no reconocido (on|off) — fail-fast")
    return raw in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# (s332 §4/§5) F1_MARCA_CORRECCION — la RED: rama de corrección de marca
# ---------------------------------------------------------------------------
def correction_enabled() -> bool:
    """Lever `F1_MARCA_CORRECCION` (s332 §5): gatea la rama de corrección de marca,
    su `state_query_override` y el sufijo de asunción. Default off = conducta servida
    byte-idéntica (sin la rama, «me refería a Kidde» cae en `new_brand_no_state`,
    exactamente como hoy).

    Se lee en CADA llamada, SIN caché de módulo: un flip en Railway togglea sin
    restart (patrón `asr_avisos_on`/`mismatch_answer_activo`). Parser ESTRICTO: un
    typo no puede dejar el lever a medias EN SILENCIO."""
    raw = (os.getenv("F1_MARCA_CORRECCION", "") or "").strip().lower()
    if raw in ("", "off"):
        return False
    if raw == "on":
        return True
    raise RuntimeError(
        f"F1_MARCA_CORRECCION={raw!r} no reconocido (on|off) — fail-fast")


_CONFIRMATION_LEXICON_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "confirmation_lexicon_v1.yaml"
)
_confirmation_cache: "tuple[tuple[str, ...], tuple[str, ...]] | None" = None


def _confirmation_lists() -> "tuple[tuple[str, ...], tuple[str, ...]]":
    """(afirmaciones, negaciones) del léxico gobernado, minúsculas, cacheadas a nivel
    de módulo. Fail-open a listas vacías con warning (la gramática degrada a la regla
    4 «cambio de tema» — jamás rompe el turno), igual que los léxicos del detector."""
    global _confirmation_cache
    if _confirmation_cache is not None:
        return _confirmation_cache
    try:
        import yaml

        data = yaml.safe_load(_CONFIRMATION_LEXICON_PATH.read_text(encoding="utf-8")) or {}
        af = tuple(str(x).strip().lower() for x in (data.get("afirmacion") or []) if str(x).strip())
        ng = tuple(str(x).strip().lower() for x in (data.get("negacion") or []) if str(x).strip())
        _confirmation_cache = (af, ng)
    except Exception:  # pragma: no cover - IO/formato
        logger.warning("confirmation_lexicon_v1.yaml no legible — gramática degradada a "
                       "cambio-de-tema (fail-open declarado s331)")
        _confirmation_cache = ((), ())
    return _confirmation_cache


def _match_phrase(ql: str, phrases: "tuple[str, ...]") -> bool:
    """Frase completa por token-boundary sobre la query en minúscula."""
    for p in phrases:
        if re.search(rf"(?<![a-záéíóúüñ0-9]){re.escape(p)}(?![a-záéíóúüñ0-9])", ql):
            return True
    return False


_CORRECTION_LEXICON_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "correction_lexicon_v1.yaml"
)
_correction_cache: "tuple[str, ...] | None" = None


def _correction_lexicon() -> "tuple[str, ...]":
    """(s332 §4) Cues de corrección de marca del léxico gobernado, minúsculas,
    cacheados a nivel de módulo. Fail-open a tupla vacía con warning (la rama no
    dispara y la cascada sigue: statu quo, jamás rompe el turno), patrón EXACTO de
    `_confirmation_lists`."""
    global _correction_cache
    if _correction_cache is not None:
        return _correction_cache
    try:
        import yaml

        data = yaml.safe_load(_CORRECTION_LEXICON_PATH.read_text(encoding="utf-8")) or {}
        _correction_cache = tuple(
            str(x).strip().lower() for x in (data.get("correccion") or []) if str(x).strip()
        )
    except Exception:  # pragma: no cover - IO/formato
        logger.warning("correction_lexicon_v1.yaml no legible — rama de corrección de "
                       "marca inerte (fail-open declarado s332)")
        _correction_cache = ()
    return _correction_cache


_CLAUSE_CUTS = ",.;:¿?¡!"
_NEGATION_CUES = frozenset({"no", "not", "nope"})


def _build_turn_identity(models, models_prov: str, *, mention: str | None = None,
                         route_cut: bool = False):
    """(s331 §3.D) Construye la identidad del turno o None si no hay NADA que
    declarar (invariante «no se construye vacía»). La mención solo con su
    procedencia this_turn (puerta 1); route_cut exige mención."""
    models_t = tuple(models or ())
    if not models_t and not mention:
        return None
    return TurnIdentity(
        resolved_models=models_t,
        models_provenance=models_prov if models_t else "none",
        mention=mention,
        mention_provenance="this_turn" if mention else "none",
        route_cut=bool(route_cut and mention),
    )


def _token_negated(query: str, token: str) -> bool:
    """(B1 §11 v6, Sol-1 r-v6) ¿Está el token NEGADO en su cláusula? Un cue de
    negación a ≤4 palabras por delante SIN puntuación entre medias niega el token:
    «No es la 2X-AF1-S» ⇒ negado; «No, es la CAD-150» ⇒ la coma corta el alcance y
    CAD-150 NO está negado (la corrección común bindea). Con varias ocurrencias, el
    token cuenta como negado solo si TODAS lo están (dirección segura)."""
    ql, tl = query.lower(), token.lower()
    i = ql.find(tl)
    if i == -1:
        return False
    while i != -1:
        prev = ql[:i]
        cut = max((prev.rfind(c) for c in _CLAUSE_CUTS), default=-1)
        clause_words = re.findall(r"[a-záéíóúüñ0-9-]+", prev[cut + 1:])
        if not any(w in _NEGATION_CUES for w in clause_words[-4:]):
            return False  # esta ocurrencia NO está negada ⇒ el token vive
        i = ql.find(tl, i + 1)
    return True


# ---------------------------------------------------------------------------
# Seed tables (data-anchored; the durable versions read the governed catalog,
# DEC-069 2-stage entity linking — declared dependencies, not invented here)
# ---------------------------------------------------------------------------
# Brand/manufacturer name tokens (served + a seed of common unserved PCI brands).
# When a turn names a brand but ``extract_product_models`` resolved no in-corpus
# model, the turn MAY be introducing a NEW product (possibly out of corpus). The
# gate is a deterministic split (see ``resolve`` branch B): brand + model-type
# token => product switch; brand alone in-window => compatibility follow-up
# (carry-forward); brand of the SAME manufacturer as the state => exempt.
# Anchored to config/manufacturers (governed source) UNIONED with a seed of the
# M&A 30+-brand universe (MT-1a S99 fix; mt05b Bosch FPA-1200 is the pinned case).
_SEED_BRAND_TOKENS: frozenset[str] = frozenset(
    {
        # served
        "detnov", "notifier", "morley", "honeywell",
        # common unserved fire-alarm brands (seed)
        "bosch", "siemens", "kilsen", "cofem", "aguilera", "esser", "hochiki",
        "gst", "kidde", "aritech", "ziton", "apollo", "inim", "teletek",
    }
)


def _config_brand_tokens() -> frozenset[str]:
    """Primary brand word of every ``config/manufacturers/*.yaml`` (the governed
    source): Detnov, Morley, Notifier, Argus, Pepperl, Securiton, Spectrex,
    Xtralis... Best-effort + import-light (a small yaml read); on any failure the
    seed alone stands. The durable version also unions the model catalog's brand
    set (heavier — declared extension, not loaded here)."""
    tokens: set[str] = set()
    try:  # pragma: no cover - trivial IO guard
        import yaml  # local: not needed unless deriving brands

        cfg_dir = Path(__file__).resolve().parents[2] / "config" / "manufacturers"
        for p in sorted(cfg_dir.glob("*.yaml")):
            if p.name.startswith("_"):
                continue
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            name = str(data.get("manufacturer") or "")
            # Primary word only (avoids generic suffixes like "Security"/"Fuchs").
            for w in re.split(r"[^A-Za-zÀ-ÿ0-9]+", name.lower()):
                if len(w) >= 3:
                    tokens.add(w)
                    break
    except Exception:
        pass
    return frozenset(tokens)


BRAND_TOKENS: frozenset[str] = _SEED_BRAND_TOKENS | _config_brand_tokens()

# Brand-word -> canonical manufacturer, for the SAME-manufacturer exemption in the
# brand gate (naming the state's own brand is not a product switch). Only served
# manufacturers matter here (the working-state model is always in-corpus); unserved
# brands fall through as "different manufacturer" and are never exempt.
_BRAND_TO_MANUFACTURER: dict[str, str] = {
    "detnov": "Detnov",
    "notifier": "Notifier",
    "morley": "Morley",
    "honeywell": "Honeywell",
}

# A model-type token (vendor code with digits: FPA-1200, AM-2000, IDX3000). When a
# brand is named ALONGSIDE such a token the turn introduces a concrete product =>
# switch (drop stale state). A brand with NO model-type token in-window is a
# compatibility follow-up (carry-forward). Normative/non-product codes are excluded
# so "EN-54"/"NFPA-72" beside a brand never read as a model.
_MODEL_TYPE_TOKEN_RE = re.compile(
    r"\b[A-Za-z]{2,}-\d{2,}\b"        # FPA-1200, AM-2000, CAD-250
    r"|\b[A-Za-z]{2,}\d{3,}\b",       # FPA1200, IDX3000 (no hyphen)
    re.IGNORECASE,
)

# Normative/standards codes (NFPA 72, EN 54, UNE 23007, UL 864, CEA 4040, ISO
# 7240). They look like product codes to the detector but are NEVER a product ->
# filtered alongside NON_PRODUCT_CODES (S99 / sol-S6). Hyphen or space separator.
_NORMATIVE_CODE_RE = re.compile(
    r"\b(?:NFPA|EN|UNE|UL|CEA|ISO)[-\s]?\d+", re.IGNORECASE
)


# (s321 E4) `_FamilySpec` retirado con el seed: la spec de familia vive en el
# campo `clarify` de las umbrellas del catálogo gobernado (ver _clarify_specs).


# s321 E4 (DEC-215, dúo r26): el seed hardcoded FAMILY_REGISTRY se RETIRÓ —
# la promesa de su propio comentario («the durable version reads the catalog's
# variant table», DEC-069) se cumple: el clarify-por-divergencia lee el campo
# `clarify` ADJUDICABLE de las umbrellas del catálogo gobernado, vía la
# instancia ÚNICA del proceso (catalog_resolver.catalogo_cargado — r26: nada
# de segunda caché). Las VARIANTES no se re-declaran: se DERIVAN de los
# canonical_model de los miembros (prefijo/sufijo común fuera → 1/2/5).
# Fail-open DECLARADO como divergencia con el seed (que nunca fallaba): sin
# catálogo → sin clarify de familia, con warning una vez.
_clarify_specs_cache: dict | None = None
_clarify_warned = False


def _clarify_specs() -> dict[str, dict]:
    """{TOKEN_UPPER: {"eje": [...], "variantes": "1/2/5", "ids": [...]}}."""
    global _clarify_specs_cache, _clarify_warned
    if _clarify_specs_cache is not None:
        return _clarify_specs_cache
    try:
        from ..rag.catalog_resolver import catalogo_cargado

        cat = catalogo_cargado()
        assert cat is not None
        specs: dict[str, dict] = {}
        for u in cat.umbrellas:
            cl = u.get("clarify")
            if not cl or u.get("candidate"):
                continue
            canonicos = [
                (cat.products.get(cat.follow_redirect(i)) or {})
                .get("canonical_model", "") for i in u.get("ids", ())]
            canonicos = [c for c in canonicos if c]
            specs[str(u["termino"]).upper()] = {
                "eje": tuple(cl["eje_terminos"]),
                "variantes": _variantes_de_miembros(canonicos),
                "ids": tuple(u.get("ids", ())),
            }
        _clarify_specs_cache = specs
    except Exception as exc:                     # noqa: BLE001
        if not _clarify_warned:
            logger.warning(
                "clarify gobernado: catálogo no disponible (%s) — familia "
                "sin clarify este proceso (divergencia declarada con el seed)",
                type(exc).__name__)
            _clarify_warned = True
        _clarify_specs_cache = {}
    return _clarify_specs_cache


def _variantes_de_miembros(canonicos: list[str]) -> str:
    """«ZX1e/ZX2e/ZX5e» → «1/2/5»: quita el prefijo y sufijo comunes de los
    canonical_model de los miembros; el core que queda ES la variante. Si el
    stripping degenera (core vacío), cae a los canónicos completos — jamás a
    una lista hardcoded (r26: el fallback «1/2/5/10» era una tercera copia)."""
    if not canonicos:
        return ""
    if len(canonicos) == 1:
        return canonicos[0]
    pre = 0
    while all(len(c) > pre and c[pre].lower() == canonicos[0][pre].lower()
              for c in canonicos):
        pre += 1
    suf = 0
    while all(len(c) > pre + suf
              and c[-1 - suf].lower() == canonicos[0][-1 - suf].lower()
              for c in canonicos):
        suf += 1
    cores = [c[pre:len(c) - suf] if suf else c[pre:] for c in canonicos]
    if any(not c for c in cores):
        return "/".join(canonicos)
    return "/".join(cores)

# Attributes that are INVARIANT across a family's variants -> never clarify on
# them (DEC-092: end-of-line resistance is family-generic in the e-series). A
# defensive negative guard alongside the specific divergent-axis phrases.
_INVARIANT_ATTRS: tuple[str, ...] = (
    "fin de línea", "fin de linea", "resistencia de fin", "eol", "rfl",
)

# Demonstrative determiners (gendered forms only). ``ese/esa/esos/esas`` and
# ``este/esta/estos/estas`` — the plural/singular masculine+feminine set. The
# NEUTER singulars ``eso``/``esto`` are deliberately EXCLUDED (they are discourse
# fillers — "eso, ¿cómo...?" — handled by carry_forward, not content anaphora).
_DEMONSTRATIVE = r"(?:ese|esa|esos|esas|este|esta|estos|estas)"

# Content-anaphora: a demonstrative determiner + a following noun points at
# specific prior CONTENT that re-attaching the model cannot resolve ("ese aviso"
# = the Earth-Fault notice; "esos avisos" = the batch of notices; "este módulo"
# = the loop module). (Matches the sunk-S99v2 slice; extended to the full
# demonstrative set — the old ``es[ae]s?`` missed "esos"/"este..." — sol/F6.)
_CONTENT_ANAPHOR_RE = re.compile(rf"\b{_DEMONSTRATIVE}\s+\w+", re.IGNORECASE)

# Dependency signal for the NO-STATE case: a leading continuation conjunction, a
# possessive/anaphoric pronoun, or a demonstrative + noun => the turn NEEDS an
# antecedent. Used only to split clarify (dangling) vs standalone (self-contained)
# when there is no usable state. The Spanish ARTICLES (le|lo|la|los|las) were
# REMOVED (S99 / orq+sol-S3 + F1x5): they fire on almost every self-contained
# question, mis-routing standalone turns to clarify. Declared safe degradation: a
# rare true object clitic ("¿cómo lo borro?") now falls to STANDALONE (retrieval +
# generator handle it) instead of a reflexive clarify.
_DEPENDENCY_RE = re.compile(
    r"^\s*¿?\s*y\b"                              # "¿y ...", "y ..."
    r"|\b(su|sus|dicho|dicha|mismo|misma)\b"     # possessive / anaphoric pronouns
    rf"|\b{_DEMONSTRATIVE}\s+\w+\b"              # demonstrative + noun
    r"|\bes[eo]\b",                              # bare "ese"/"eso"
    re.IGNORECASE,
)

# Conservative OUT-OF-DOMAIN lexicon (S99 gas gate). Deliberately narrow: it must
# never fire on the served fire-adjacent gas detectors (DGD-600 etc.), which are
# handled by the explicit-product branch A before this gate is reached. No gold
# exercises DECLINE (declared gap, vara); this keeps the route genuine + safe.
_OUT_OF_DOMAIN_LEXICON: tuple[str, ...] = (
    "caldera de gas", "cocina de gas", "gas natural", "gas ciudad",
    "bombona de butano", "estufa de gas", "calentador de gas",
)


# ---------------------------------------------------------------------------
# Detection (composes extract_product_models — never duplicates it)
# ---------------------------------------------------------------------------
def detect_turn_signals(query: str) -> tuple[list[str], list[str] | None]:
    """``(turn_models, available_models)`` — mirrors telegram_bot steps 1a/2b, $0.

    ``turn_models`` = ``extract_product_models(query)`` (the existing detector,
    composed). ``available_models`` = category-detected option set (for CLARIFY)
    or None. Imports are local so the module has no import-time DB/config cost
    beyond the detector's own (pure regex)."""
    from src.rag.retriever import (
        CATEGORY_TERMS,
        extract_product_models,
        get_category_models,
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
                    # Fail-open: un fallo del lookup de categoría (DB caída,
                    # entorno sin credenciales) no puede tumbar el turno — la
                    # categoría solo alimenta las opciones de CLARIFY.
                    available = None
                break
    return turn_models, available


# ---------------------------------------------------------------------------
# The policy
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DeterministicConversationPolicy:
    """MT-1a's concrete policy. Deterministic cascade; the injected ``rewrite``
    callable is used ONLY on the REWRITE route (and only when supplied)."""

    IS_STUB: bool = field(default=False, init=False)
    window_seconds: int = WINDOW_SECONDS

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _matched_brands(ql: str) -> list[str]:
        return [b for b in BRAND_TOKENS if re.search(rf"\b{re.escape(b)}\b", ql)]

    @staticmethod
    def _correction_rebuild(ql: str, query: str,
                            matched_brands: Sequence[str]) -> str | None:
        """(s332 §4) ¿Es el turno ENTERO una corrección de marca —«{cue} [artículo]
        {marca}» y nada más— ? Devuelve la forma SUPERFICIAL de la marca tal como el
        usuario la escribió (para que «Kidde» conserve su grafía), o None.

        Regla de PLANTILLA CERRADA, sin léxico de stopwords: el ancla `^…$` ES el
        criterio de «turno solo-corrección» (nada de contar tokens residuales, que
        exigiría un léxico de funcionales por cue). Dos consecuencias DECLARADAS y
        testeadas: «no me refería a Kidde» NO casa (el `^` no admite el «no» previo) y
        «me refería a Kidde, ¿y el lazo?» tampoco (la coma y la sustancia extra quedan
        fuera de la cola de puntuación).

        Cabeza opcional (57b8d482, la respuesta real a la invitación del aviso ASR:
        «sí, dije Kidde»): se admite UN token del léxico GOBERNADO de confirmación
        delante del cue — afirmación con separador libre; negación SOLO con corte de
        cláusula `[,:]` (la polaridad s331: «no, dije Kidde» corrige, «no dije Kidde»
        y «no me refería a Kidde» siguen sin casar porque la negación pega al cue en
        la misma cláusula)."""
        af, ng = _confirmation_lists()
        cabezas = [rf"{re.escape(a)}[\s:,]+" for a in af]
        # La negación pelada («no,») viene de _NEGATION_CUES —la fuente de polaridad
        # s331—, NO del léxico de confirmación: añadir «no» a ESA lista cambiaría la
        # regla 3 de la gramática de pending (negación⇒etiqueta), que hoy manda el
        # «no» a secas a cambio-de-tema. Aquí el corte [,:] es OBLIGATORIO.
        cabezas += [rf"{re.escape(n)}\s*[,:]\s*"
                    for n in tuple(ng) + tuple(sorted(_NEGATION_CUES))]
        cabeza_opcional = rf"(?:(?:{'|'.join(cabezas)}))?" if cabezas else ""
        for cue in _correction_lexicon():
            for marca in matched_brands:
                patron = (rf"^[\s¡¿]*{cabeza_opcional}{re.escape(cue)}[\s:,]+"
                          rf"(?:la\s+|el\s+|los\s+|las\s+)?{re.escape(marca)}"
                          rf"[\s.!?¡¿]*$")
                if not re.match(patron, ql):
                    continue
                # La forma superficial se lee de la query ORIGINAL (case-insensible):
                # `marca` es el token del catálogo de marcas y viene en minúscula.
                m = re.search(rf"\b{re.escape(marca)}\b", query, re.IGNORECASE)
                superficial = (m.group(0) if m else marca).strip(" .,;:!?¡¿«»\"'")
                return superficial or marca
        return None

    @staticmethod
    def _is_out_of_domain(ql: str) -> bool:
        return any(term in ql for term in _OUT_OF_DOMAIN_LEXICON)

    @staticmethod
    def _is_normative_code(model: str) -> bool:
        return bool(_NORMATIVE_CODE_RE.fullmatch(model.strip()))

    @staticmethod
    def _has_model_type_token(ql: str) -> bool:
        """A concrete vendor model code (with digits) is present — excluding
        normative/non-product codes so they never read as a model."""
        np_codes = {c.upper() for c in NON_PRODUCT_CODES}
        for m in _MODEL_TYPE_TOKEN_RE.finditer(ql):
            tok = m.group(0)
            norm = tok.upper().replace(" ", "")
            if norm in np_codes or _NORMATIVE_CODE_RE.fullmatch(tok):
                continue
            return True
        return False

    @staticmethod
    def _same_manufacturer(matched_brands: Sequence[str], state_models: Sequence[str]) -> bool:
        """True when a named brand is the SAME manufacturer as the working-state
        product (naming your own brand is not a switch). Catalog-first classifier
        (file-backed, $0/no DB); Honeywell collapses to its Notifier/Morley
        sub-brands."""
        if not matched_brands or not state_models:
            return False
        from src.rag.retriever import classify_model_manufacturer

        state_mfrs = {classify_model_manufacturer(m) for m in state_models}
        state_mfrs.discard(None)
        if not state_mfrs:
            return False
        for b in matched_brands:
            bm = _BRAND_TO_MANUFACTURER.get(b)
            if not bm:
                continue
            if bm in state_mfrs:
                return True
            if bm == "Honeywell" and state_mfrs & {"Notifier", "Morley"}:
                return True
        return False

    def _intent_brand_switch(self, query, matched_brands, working_state,
                             intent, avail):
        """Rama del lever (v2 §2-§4). None => sigue la cascada (carry de hoy).

        Exención de MISMA MARCA por palabra PRIMARIA (F able r10, verificado:
        `classify_model_manufacturer` devuelve el nombre COMPLETO -- 'Argus Security' --
        y el token de la rama es la palabra primaria -- 'argus'; 8/26 fabricantes son
        multi-palabra y la comparación directa fallaba). Multi-modelo: exime si el
        token casa con CUALQUIERA de las marcas del estado. Tokens de
        `_MARCAS_AMBIGUAS` ('fuego') NO disparan el juicio (la clase FUEGO de s316b).
        Si ninguna marca del estado resuelve -> None (sin base de comparación: carry
        de hoy, fail-open declarado). El error del LLM JAMÁS rompe el turno.
        """
        from .conversation_policy import _MARCAS_AMBIGUAS

        tokens = [b for b in matched_brands if b not in _MARCAS_AMBIGUAS]
        if not tokens:
            return None
        from ..rag.retriever import classify_model_manufacturer

        marcas_estado = set()
        for m in working_state.last_target_models:
            mfr = classify_model_manufacturer(m)
            if mfr:
                # MISMA tokenizacion que _config_brand_tokens: primer tramo
                # alfanumerico. (Fable r11, probado: 'Pepperl-Fuchs'.split()[0] daba
                # 'pepperl-fuchs' vs token 'pepperl' -> el unico fabricante con guion
                # NO eximia y un switch erroneo borraba estado de la MISMA marca.)
                primario = re.split(r"[^a-z0-9]+", mfr.lower())
                if primario and primario[0]:
                    marcas_estado.add(primario[0])
        if not marcas_estado:
            return None
        # Exencion SOLO si TODAS las marcas mencionadas son las del estado (Sol r11
        # C1: con any(), 'los Detnov fallan, dime el de Morley' quedaba exento y el
        # caso que el gate midio como SWITCH jamas llegaba al LLM en serving —
        # paridad gate<->serving rota). Marca ajena presente => juzga el clasificador.
        if all(tok in marcas_estado for tok in tokens):
            return None                      # solo la(s) marca(s) propia(s): $0
        try:
            decision = intent(query, working_state)
        except Exception:                    # noqa: BLE001 -- fail-open total
            decision = None
        if decision == "switch":
            return TurnResolution(
                route=PolicyRoute.STANDALONE,
                query_for_retrieval=query,
                target_models=(),
                available_models=avail,
                rationale="new_brand_topic_switch_llm",
            )
        if decision == "compat":
            return self._carry_forward(
                query, working_state.last_target_models, "brand_compat_confirmed_llm")
        return self._carry_forward(
            query, working_state.last_target_models, "brand_compat_failopen_llm")

    @staticmethod
    def _family_divergence(models: Sequence[str], ql: str) -> bool:
        """True when a state model is a known family AND the question hits its
        divergent axis AND does not ask about an invariant attribute."""
        if any(term in ql for term in _INVARIANT_ATTRS):
            return False
        specs = _clarify_specs()
        for m in models:
            spec = specs.get(m)
            if spec and any(term in ql for term in spec["eje"]):
                return True
        return False

    def _carry_forward(self, query: str, models: tuple[str, ...], why: str,
                       mention: str | None = None) -> TurnResolution:
        hint = ", ".join(models)
        # Raw query preserved byte-verbatim; model hint APPENDED (design invariant).
        qfr = f"{query} (contexto: {hint})" if hint else query
        return TurnResolution(
            route=PolicyRoute.CARRY_FORWARD,
            query_for_retrieval=qfr,
            target_models=models,
            # (s331 §3.D — cazado por G1a: sin esto, GENERATOR_NO_REASK jamás
            # dispara en el flujo principal) Identidad del turno también en el
            # CARRY: canónicos arrastrados + mención de puerta-1 si la hay (el
            # estado MIXTO de Sol-3 r-v2). None si no hay nada que declarar.
            turn_identity=_build_turn_identity(
                models, "carried", mention=mention),
            rationale=f"carry_forward:{why}",
        )

    # -- the router ---------------------------------------------------------
    def resolve(
        self,
        *,
        query: str,
        turn_models: Sequence[str],
        available_models: Sequence[str] | None,
        working_state: WorkingState,
        now: datetime,
        rewrite: RewriteFn | None = None,
        intent=None,
        unresolved_mention: str | None = None,
    ) -> TurnResolution:
        ql = query.lower()
        # A-filter: drop bus/protocol (NON_PRODUCT_CODES) AND normative/standards
        # codes (NFPA/EN/UNE/UL/CEA/ISO) — neither is a product (sol-S6).
        real = tuple(
            m for m in turn_models
            if m not in NON_PRODUCT_CODES and not self._is_normative_code(m)
        )
        avail = tuple(available_models) if available_models else None

        # in_window is computed HERE (before B/C) so a brand/out-of-domain gate can
        # never override an in-window continuation (gas-gate S99 / F4).
        in_window = bool(working_state.last_target_models) and working_state.within_window(
            now, self.window_seconds
        )

        # (s331 §3.C.1) GRAMÁTICA de confirmación — solo con mención PENDIENTE viva
        # (el turno siguiente a un CLARIFY-de-mención). POLARIDAD delante (B1 §11 v6):
        # un token resoluble NEGADO en su cláusula JAMÁS bindea. El CLEAR/CONSUME del
        # pending es ESTRUCTURAL en advance_working_state (toda ruta lo limpia salvo
        # el SET) — «ciclo máximo 1» por construcción.
        pending_live = (
            mention_precedence_enabled()
            and working_state.pending_within_window(now, self.window_seconds)
        )

        def _label_request() -> TurnResolution:
            return TurnResolution(
                route=PolicyRoute.CLARIFY,
                query_for_retrieval=query,
                clarify_question=(
                    "Entendido, ese no es. ¿Puedes escribirme el modelo exacto tal "
                    "como aparece en la etiqueta del panel?"),
                available_models=avail,
                rationale="pending_negated_label_request",
            )

        if pending_live and real:
            vivos = tuple(m for m in real if not _token_negated(query, m))
            if not vivos:
                return _label_request()    # regla 1b: todos negados ⇒ UNA etiqueta
            real = vivos                   # regla 1: bindean SOLO los no-negados
        elif pending_live and not real:
            af, ng = _confirmation_lists()
            pending_str = working_state.pending_mention or ""
            if _match_phrase(ql, af):
                # regla 2: afirmación sin token ⇒ FAMILIA gobernada del término
                # extendido (`pending_derived`) — sin re-preguntar. DESVIACIÓN
                # DECLARADA de v6 (que pedía «re-intento de binding» primero): el
                # SET exigió puerta 2 = NO-resoluble, el catálogo no muta a mitad
                # de hilo, y el re-intento vía resolve_query aceptaba un match
                # PARCIAL del prefijo como binding falso (medido en G0-g). Si el
                # catálogo mutara, el siguiente turno con el código resuelve por A.
                # La pregunta a responder es la del turno de la mención (guardada
                # en last_query por el SET); la ruta es STANDALONE reconstruida —
                # el invariante byte-verbatim del CARRY es HARD (lo pinea el eval)
                # y aquí la query es solo «sí».
                from ..rag.catalog_resolver import mention_governed_base
                models: tuple[str, ...] = ()
                prov = "pending_derived"
                base = mention_governed_base(pending_str)
                if base is not None:
                    models = (base,)
                if models:
                    pregunta = working_state.last_query or query
                    hint = ", ".join(models)
                    return TurnResolution(
                        route=PolicyRoute.STANDALONE,
                        query_for_retrieval=f"{pregunta} (contexto: {hint})",
                        target_models=models,
                        available_models=avail,
                        turn_identity=TurnIdentity(
                            resolved_models=models,
                            models_provenance=prov,
                            mention=pending_str,
                            mention_provenance="pending_carried",
                        ),
                        rationale="pending_confirmed_family",
                    )
                # pendiente roto (el SET exigió puerta 2; degradación declarada):
                # cae a la cascada y el pending se limpia estructuralmente.
            elif _match_phrase(ql, ng):
                return _label_request()    # regla 3: negación sin token ⇒ UNA etiqueta
            # regla 4: cambio de tema ⇒ cascada normal (pending se limpia).

        # A. Explicit product in THIS turn wins over history.
        if real:
            return TurnResolution(
                route=PolicyRoute.STANDALONE,
                query_for_retrieval=query,
                target_models=real,
                available_models=avail,
                # (s331 §3.D — cazado por G1a) Identidad RESUELTA este turno;
                # con mención de puerta-1 co-presente = estado mixto declarado.
                turn_identity=_build_turn_identity(
                    real, "resolved_this_turn", mention=unresolved_mention),
                rationale="explicit_product",
            )

        # (s331 §3.C.1) PRECEDENCIA DE MENCIÓN (puerta 2) — una mención con forma de
        # variante de FAMILIA GOBERNADA, nueva en ESTE turno y distinta del estado,
        # corta el carry-forward ANTES de la rama de marca: sin esto, F1 respondería
        # del producto VIEJO callando la mención nueva (Sol-3 r-v2), o la marca
        # co-presente arrastraría el estado. Gate: in_window (la clase protegida es
        # el carry equivocado; sin estado, la conducta de hoy queda intacta).
        if (
            unresolved_mention
            and mention_precedence_enabled()
            and in_window
        ):
            from src.rag import catalog_store as _cstore
            from ..rag.catalog_resolver import (
                mention_governed_base,
                mention_route_cut_eligible,
            )
            _nk = _cstore.norm_token(unresolved_mention)
            _state_nks = {
                _cstore.norm_token(m) for m in working_state.last_target_models
            }
            if _nk not in _state_nks and mention_route_cut_eligible(unresolved_mention):
                base = mention_governed_base(unresolved_mention)
                familia = f" ¿Es de la familia {base}?" if base else ""
                return TurnResolution(
                    route=PolicyRoute.CLARIFY,
                    query_for_retrieval=query,
                    clarify_question=(
                        f"No encuentro «{unresolved_mention}» en mi documentación."
                        f"{familia} Confírmame el modelo exacto de la etiqueta y sigo."),
                    available_models=avail,
                    turn_identity=TurnIdentity(
                        mention=unresolved_mention,
                        mention_provenance="this_turn",
                        route_cut=True,
                    ),
                    rationale="mention_route_cut_clarify",
                )

        # B. Brand gate (deterministic split — S99 / fable-F3 + sol-S7).
        matched_brands = self._matched_brands(ql)
        if matched_brands:
            # (s332 §4) NIVEL 2, la RED: recupera las confusiones de marca que la
            # tabla ASR aún NO tiene tabuladas («me refería a Kidde» tras un turno que
            # respondió de otra marca). El nivel 1 —la tabla— previene las tabuladas
            # ya en T1; esta rama recupera las que se escapan y deja la observación.
            # PRECEDENCIA por ORDEN, no por re-chequeos: la gramática de pending ya
            # corrió arriba (si había pending vivo, resolvió o lo limpió) y la rama A
            # ya retornó si el turno traía modelo explícito — de ahí que `not real`
            # sea una guarda DECLARADA, no un empate que decidir aquí.
            if (correction_enabled() and not real
                    and working_state.last_query
                    and working_state.within_window(now, self.window_seconds)):
                marca = self._correction_rebuild(ql, query, matched_brands)
                if marca:
                    # La base es la pregunta ORIGINAL, y viaja en
                    # `state_query_override` para que una SEGUNDA corrección
                    # reconstruya desde ELLA — nunca desde la meta-frase ni desde la
                    # query ya anotada (Sol-3).
                    base = working_state.last_query
                    return TurnResolution(
                        route=PolicyRoute.STANDALONE,
                        query_for_retrieval=(
                            f"{base} (el usuario corrige: la marca es {marca})"),
                        target_models=(),
                        available_models=avail,
                        asunciones=(Asuncion(kind="marca_corregida", detectado=marca,
                                             asumido=marca, modo="reescrito"),),
                        state_query_override=base,
                        rationale="brand_correction_rebuild",
                    )
            same_mfr = in_window and self._same_manufacturer(
                matched_brands, working_state.last_target_models
            )
            if same_mfr:
                # (Sol r11 C1) same_mfr=True con marca AJENA co-presente («los Detnov
                # fallan, mejor dime el de Morley»): el lever debe juzgar — sin esto,
                # el fall-through conserva la marca vieja y el caso que el gate midió
                # como SWITCH nunca llega al clasificador. Con intent=None (OFF):
                # conducta histórica byte-idéntica.
                if intent is not None and in_window:
                    via_llm = self._intent_brand_switch(
                        query, matched_brands, working_state, intent, avail)
                    if via_llm is not None:
                        return via_llm
                pass  # naming your OWN brand is not a switch -> fall through to C/D.
            elif self._has_model_type_token(ql):
                # Brand + concrete model code -> new product -> switch, drop state.
                return TurnResolution(
                    route=PolicyRoute.STANDALONE,
                    query_for_retrieval=query,
                    target_models=(),
                    available_models=avail,
                    rationale="new_brand_switch_model_token",
                )
            elif in_window:
                # (s316g lever INTENT_LLM, DEC-203) La conflacion de esta rama es la
                # causa (2) de #70: "marca sola + in-window" NO siempre es
                # compatibilidad ("¿y en Morley cómo se hace el reset?" es cambio de
                # tema). Con `intent` inyectado (flag ON), un clasificador decide; con
                # None (flag OFF / modo contrato / $0) el camino es BYTE-IDÉNTICO a
                # hoy. 5 rondas de dúo establecieron que las reglas de vocabulario no
                # convergen aquí; el gate de juicio (cohorte v1.1, GO adjudicado por
                # Alberto) estableció que sonnet-4-6 sí: 40/40, 0 falsos SWITCH.
                if intent is not None:
                    via_llm = self._intent_brand_switch(
                        query, matched_brands, working_state, intent, avail)
                    if via_llm is not None:
                        return via_llm
                # Brand alone, in-window -> compatibility follow-up about the state
                # product (e.g. "¿es compatible con Hochiki?") -> carry-forward.
                return self._carry_forward(
                    query, working_state.last_target_models,
                    "brand_compatibility_in_window", mention=unresolved_mention,
                )
            else:
                # Brand named, no usable state -> new topic (possibly out-of-corpus).
                return TurnResolution(
                    route=PolicyRoute.STANDALONE,
                    query_for_retrieval=query,
                    target_models=(),
                    available_models=avail,
                    rationale="new_brand_no_state",
                )

        # C. Out-of-domain (conservative gas-outside-fire gate). Runs AFTER A/B and
        #    ONLY when NOT an in-window continuation: an in-window follow-up (even
        #    one mentioning gas, e.g. a boiler-cutoff maneuver from a fire panel) is
        #    never hard-declined (F4). A fresh out-of-domain turn still declines.
        if not in_window and self._is_out_of_domain(ql):
            return TurnResolution(
                route=PolicyRoute.DECLINE,
                query_for_retrieval=query,
                decline_reason="fuera_de_dominio_pci_fuego",
                rationale="out_of_domain_gas",
            )

        # D. In-window state -> continuation.
        if in_window:
            models = working_state.last_target_models

            # E. Family umbrella + divergent-axis question -> clarify (real divergence).
            # (s321 E4) La spec viene del CATÁLOGO; _family_divergence ya
            # garantizó que hay umbrella con eje disparado — sin fallback
            # hardcoded (r26: el «1/2/5/10» era una tercera copia; retirado).
            if self._family_divergence(models, ql):
                specs = _clarify_specs()
                umbrella = next((m for m in models if m in specs), models[0])
                spec = specs.get(umbrella)
                variants = spec["variantes"] if spec else ""
                return TurnResolution(
                    route=PolicyRoute.CLARIFY,
                    query_for_retrieval=query,
                    target_models=models,
                    available_models=working_state.available_models or avail,
                    clarify_question=(
                        f"La {umbrella} tiene variantes por número de lazos "
                        f"({variants}) y ese dato cambia entre ellas. ¿Con qué "
                        f"variante estás trabajando?"
                    ),
                    rationale="divergent_variant",
                )

            # F. Content anaphora -> rewrite (defers in $0 mode; clarify if invalid).
            if _CONTENT_ANAPHOR_RE.search(query):
                if rewrite is None:
                    return TurnResolution(
                        route=PolicyRoute.REWRITE,
                        query_for_retrieval=query,  # raw fallback; --e2e supplies text
                        target_models=models,
                        available_models=avail,
                        requires_llm_rewrite=True,
                        rewritten_query=None,  # deferred: never fabricate
                        rationale="content_anaphor:deferred($0)",
                    )
                rewritten = rewrite(query, working_state)
                if rewritten is None:
                    # Fail-CLOSED: the cascade already judged re-attaching the model
                    # INSUFFICIENT (that is why it chose rewrite), so a carry-forward
                    # fallback would retrieve on an ambiguous query. Ask which
                    # element/notice instead. The $ was spent (declared).
                    return TurnResolution(
                        route=PolicyRoute.CLARIFY,
                        query_for_retrieval=query,
                        target_models=models,
                        available_models=avail,
                        clarify_question=(
                            "¿A qué aviso o elemento concreto te refieres? Necesito "
                            "precisarlo para darte la respuesta correcta."
                        ),
                        rationale="content_anaphor:rewrite_failed_clarify($-spent)",
                    )
                return TurnResolution(
                    route=PolicyRoute.REWRITE,
                    query_for_retrieval=rewritten,
                    target_models=models,
                    available_models=avail,
                    requires_llm_rewrite=True,
                    rewritten_query=rewritten,
                    rationale="content_anaphor:rewritten",
                )

            # G. Simple within-window follow-up -> deterministic carry-forward, $0.
            return self._carry_forward(query, models, "within_window_followup",
                                       mention=unresolved_mention)

        # H/I. No usable state (empty or expired).
        if self._depends_on_context(query):
            # Dangling anaphora with no antecedent -> clarify (ask for the model).
            # The text is conditional: a genuine FIRST message never had a prior
            # context, so it must not claim "time has passed" (F8).
            if working_state.is_empty:
                clarify_q = (
                    "¿De qué central o detector (modelo) estamos hablando? Necesito "
                    "el modelo para responder con precisión."
                )
            else:
                clarify_q = (
                    "¿De qué central o detector (modelo) estamos hablando? Ha pasado "
                    "un rato y necesito el modelo para responder con precisión."
                )
            return TurnResolution(
                route=PolicyRoute.CLARIFY,
                query_for_retrieval=query,
                target_models=(),  # never leak an expired product (mt07b)
                available_models=avail,
                clarify_question=clarify_q,
                rationale="dangling_no_antecedent",
            )
        # Genuinely standalone product-less turn -> let retrieval/generator handle it.
        return TurnResolution(
            route=PolicyRoute.STANDALONE,
            query_for_retrieval=query,
            target_models=(),
            available_models=avail,
            rationale="standalone_no_product",
        )

    @staticmethod
    def _depends_on_context(query: str) -> bool:
        return bool(_DEPENDENCY_RE.search(query))


# ---------------------------------------------------------------------------
# Composition seam (what MT-0d / activation wires to the bot; also the paid
# --e2e path). Mirrors the MT-1b harness's detect -> resolve -> advance loop so
# the bot behaves byte-identically to the eval.
# ---------------------------------------------------------------------------
def resolve_conversational_turn(
    query: str,
    working_state: WorkingState,
    now: datetime,
    rewrite: RewriteFn | None = None,
    intent=None,
    resolved_model: str | None = None,
) -> tuple[TurnResolution, WorkingState]:
    """Compose ``extract_product_models`` + the policy into a resolved turn.

    Returns ``(resolution, new_working_state)``. The new state is advanced from
    the resolution WITHOUT the answer excerpt (unknown pre-retrieval); the bot
    backfills the excerpt post-generation via ``advance_working_state`` if it
    wants the rewriter to see prior answer text on the next turn.

    ``resolved_model`` (s324e — DEC-224 §B / DEC-226): el modelo que el PLAN DE
    TURNO ya resolvió y sobre el que se construyó el preámbulo de corrección. Sin
    él, este seam RE-DETECTA con ``detect_turn_signals`` y el trabajo del plan se
    pierde: el crítico de Sol sobre la v2 del diseño (un ``target_models_override``
    quedaba INERTE en producción porque F1 volvía a resolver después). Con él, el
    modelo servido ES —por construcción, no por coincidencia— el mismo del que
    habla el preámbulo. ``available_models`` queda en ``None``, que es exactamente
    lo que ``detect_turn_signals`` devuelve cuando hay modelo en el turno (solo
    calcula opciones de categoría si NO hay ninguno): la vía explícita no inventa
    un estado que la vía implícita no produciría.

    TODO(MT-0d activation — sol-S8, by DESIGN not a defect): the bot does NOT yet
    consume this policy (activation is MT-0d + Alberto, out of the MT-1a brief).
    When it is wired, the handler MUST call ``advance_working_state`` a SECOND time
    after generation, passing ``answer_excerpt=<generated answer>``, so the durable
    ``last_answer_excerpt`` is populated and the rewriter can resolve content
    anaphora ("ese aviso") against the prior answer text on the next turn. This
    one-line composition seam intentionally passes ``None`` (pre-retrieval)."""
    if resolved_model:
        turn_models, available = [resolved_model], None
    else:
        turn_models, available = detect_turn_signals(query)
    # (s331 §3.A) Seam de COMPOSICIÓN: la resolución gobernada corre DESPUÉS de ambas
    # ramas — cubre también resolved_model (Fable-1 r-v5: esa rama bypasea la detección)
    # y deja detect_turn_signals intacta. Flag off ⇒ passthrough byte-idéntico. En la
    # rama del plan es canonicalize_only: jamás re-escanea la query (autoridad del plan
    # preservada, B2 §11). El RuntimeError del interlock NO se silencia: es un error de
    # despliegue que el chequeo de boot debe haber parado antes.
    from ..rag.catalog_resolver import resolve_for_turn
    turn_models, _turn_resolve_info = resolve_for_turn(
        query, list(turn_models), canonicalize_only=bool(resolved_model)
    )
    # (s331 §3.C.1, B4 §11) La MENCIÓN no-resuelta se detecta EN COMPOSICIÓN —
    # detect_turn_signals queda intacta (contrato 2-tupla) y la política la recibe
    # como argumento (Sol-2 r-v3). Flag off ⇒ None ⇒ byte-idéntico.
    unresolved_mention: str | None = None
    if mention_precedence_enabled():
        from ..rag.catalog_resolver import detect_unresolved_mentions
        _mentions = detect_unresolved_mentions(query, list(turn_models))
        unresolved_mention = _mentions[0] if _mentions else None
    policy = DeterministicConversationPolicy()
    resolution = policy.resolve(
        query=query,
        turn_models=turn_models,
        available_models=available,
        working_state=working_state,
        now=now,
        rewrite=rewrite,
        intent=intent,
        unresolved_mention=unresolved_mention,
    )
    new_state = advance_working_state(
        working_state, resolution, query, None, now, available
    )
    return resolution, new_state


def advance_working_state(
    ws: WorkingState,
    resolution: TurnResolution,
    query: str,
    answer_excerpt: str | None,
    now: datetime,
    available: Sequence[str] | None,
) -> WorkingState:
    """Durable state after a resolved turn. CLARIFY/DECLINE do NOT fix a model
    (the user has not disambiguated) AND return the prior state INTACT — crucially
    WITHOUT refreshing ``last_turn_at``. Refreshing it would RESURRECT an expired
    product: a clarify at 70 min followed by another dangling turn would find the
    (stale) model back "in window" and carry it forward (S99 / sol-S4 + F2). An
    expired context stays expired until the user re-establishes a model. Mirrors
    the MT-1b harness ``update_working_state`` so production and eval stay in
    lock-step."""
    if resolution.route in (PolicyRoute.CLARIFY, PolicyRoute.DECLINE):
        ti = resolution.turn_identity
        if ti is not None and ti.route_cut and ti.mention:
            # (s331 B3/Fable-2 r-v4, punto de mutación 1) SET del pending: copia del
            # estado prior con SOLO pending_mention/pending_at/last_query — modelos y
            # last_turn_at INTACTOS (el invariante anti-resurrección S99 se preserva:
            # la ventana del carry no se renueva). last_query SÍ se actualiza: guarda
            # la PREGUNTA del turno de la mención, que la regla 2 de la gramática
            # necesita para responder tras la confirmación («sí» no contiene la
            # pregunta). Es descriptivo — no gobierna ninguna ventana.
            return replace(ws, pending_mention=ti.mention, pending_at=now,
                           last_query=query)
        if ws.pending_mention is not None:
            # (s331 B3, Sol-3 r-v6) CLEAR EXPLÍCITO también en las rutas CLARIFY/
            # DECLINE no-mención (negación→etiqueta, cambio-de-tema→decline…): sin
            # esto el pending sobreviviría y «ciclo máximo 1» sería falso. El resto
            # del estado sigue INTACTO (semántica histórica).
            return replace(ws, pending_mention=None, pending_at=None)
        return ws
    avail_tuple = tuple(available) if available else None
    models = tuple(resolution.target_models or ())
    # (s331 B3, punto de mutación 2) Las rutas de RESPUESTA reconstruyen el estado:
    # el CONSUME/CLEAR del pending es transición EXPLÍCITA, no omisión implícita.
    return WorkingState(
        last_target_models=models,
        # (s332 §4, Sol-3) El override gana a la query literal: una meta-frase de
        # corrección jamás queda como base de futuros rebuilds.
        last_query=resolution.state_query_override or query,
        last_answer_excerpt=(answer_excerpt or "")[:500] or None,
        last_turn_at=now,
        available_models=avail_tuple,
        pending_mention=None,
        pending_at=None,
    )


# ---------------------------------------------------------------------------
# Activation gate for default_policy() (design philosophy: Phase-1 activation is
# flag-gated / default-OFF — the orchestrator + Alberto flip it, like
# ORCHESTRATOR_PATH / CONVO_SHADOW). Read at RUNTIME so an A/B can toggle in one
# process. ``conversation_policy.default_policy()`` calls this.
# ---------------------------------------------------------------------------
def conversation_policy_active() -> bool:
    """True when ``CONVERSATION_POLICY=impl``. s319 PR-C (DEC-211): default
    ``impl`` — la política F1 ES producción desde su ship verificado; el
    régimen stub queda disponible por env EXPLÍCITO (``CONVERSATION_POLICY=
    stub``) para el instrumento MT y los tests de contrato congelados.

    Parser ESTRICTO (r19, Sol M1): un typo en Railway degradaba al stub EN
    SILENCIO — un cambio de conducta servida sin señal. Enum cerrado
    impl|stub; cualquier otro valor revienta RUIDOSO (espejo del precedente
    HYQ/_guard_estricto)."""
    raw = os.getenv("CONVERSATION_POLICY", "impl").strip().lower()
    if raw == "impl":
        return True
    if raw == "stub":
        return False
    raise RuntimeError(
        f"CONVERSATION_POLICY={raw!r} no reconocido (impl|stub) — fail-fast")


__all__ = [
    "WINDOW_SECONDS",
    "BRAND_TOKENS",
    "DeterministicConversationPolicy",
    "detect_turn_signals",
    "resolve_conversational_turn",
    "advance_working_state",
    "conversation_policy_active",
]
