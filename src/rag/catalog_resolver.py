"""(s91 F2-S1 · flag IDENTITY_RESOLVE=off|shadow|on, default off) Resolución query-side del
CATÁLOGO CANÓNICO GOBERNADO (data/catalog/*.jsonl vía catalog_store, D1 repo-first).

Plan canónico: evals/s91_f2_plan_propuesta.md v2.2 (dúo ×2 rondas) + contrato
IDENTITY_CATALOG_CONTRACT §5.1 ENMENDADO s91 (✅ Alberto): F2 = EXPAND-ONLY — la conducta
answer/clarify del bot queda intacta; clarify conduct-level va en fase posterior por-pregunta.

Mecanismo (NADA aditivo al pool — DEC-069):
  seam 1  la resolución alimenta la lista `models` de extract_product_models (patrón LEVER2,
          pero data-driven). Política por brazo (IDENTITY_RESOLVE_POLICY=add|replace, default
          add): REPLACE es el brazo MEDIDO (hp018 4/4 + regresión hp009); ADD es la hipótesis
          anti-regresión — la famtie arbitra (v2.2 §mecanismo).
  seam 2  expone `allowed_sources` (source_files vía doc_map de los ids resueltos) para el
          whitelist SUSTRACTIVO de _filter_to_query_models (patrón IDENTITY_MAP, fail-open ≥3).

Detección: regex GENERADA de los términos resolubles del catálogo (mismo approach probado que
src/rag/catalog.py::_core — separador-insensible, multi-palabra, longest-first, \\b + (?!\\d)).
Pre-exclusión SOLO normkeys digit-only ('808'/'816' — FP a priori); los alfanuméricos cortos
('zxe') PASAN: excluir ≤3 chars mataría el caso central hp018 (bomba cazada dúo r2). NUNCA fuzzy
(DEC-074: texto-libre = −2 hp011).

Fail-fast de flags (v2.1a): IDENTITY_RESOLVE≠off + cualquier flag legacy de identidad ON ⇒
RuntimeError al primer uso — sin precedencia silenciosa (doble expansión = medición sucia).

Shadow (F2.5 del contrato): en modo `shadow` NO muta nada; loggea a Supabase
(identity_resolve_shadow, non-blocking, patrón logging_db) qué habría cambiado + stamp del
catálogo-commit (freeze-contract; posible por el fix D1 s91).
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from src.rag import catalog as C

ROOT = Path(__file__).resolve().parents[2]
# catalog_store es LA puerta (D1) y vive en scripts/ — se importa por path; graduarlo a paquete
# instalable es parte del retiro F4 (plan v2.2 §anti-dos-copias), no se duplica su lógica aquí.
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import catalog_store  # noqa: E402

logger = logging.getLogger(__name__)

LEGACY_FLAGS = ("LEVER2_IDENTITY", "LEVER2_PM_RESCUE", "IDENTITY_MAP")
_MODES = ("off", "shadow", "on")

_loaded = False
_pattern = None                     # regex compilada de términos resolubles
_cat: "catalog_store.Catalog | None" = None
_docs_by_id: dict[str, frozenset[str]] = {}   # id canónico -> source_files (doc_map)
_catalog_commit: str | None = None


def mode() -> str:
    """Modo del flag + FAIL-FAST contra flags legacy (v2.1a: error, no precedencia)."""
    m = (os.getenv("IDENTITY_RESOLVE", "") or "off").strip().lower() or "off"
    if m not in _MODES:
        raise RuntimeError(f"IDENTITY_RESOLVE={m!r} inválido (off|shadow|on)")
    if m != "off":
        on_legacy = [f for f in LEGACY_FLAGS
                     if os.getenv(f, "").strip().lower() in ("1", "true", "yes", "on")]
        if on_legacy:
            raise RuntimeError(
                f"IDENTITY_RESOLVE={m} es EXCLUYENTE con las vías legacy de identidad "
                f"({', '.join(on_legacy)} ON) — apaga una (plan v2.2 v2.1a, anti doble-expansión)")
    return m


def catalog_commit() -> str:
    """Stamp del commit del catálogo (freeze-contract, v2.1b). 'uncommitted' si hay diff local."""
    global _catalog_commit
    if _catalog_commit is None:
        try:
            h = subprocess.run(["git", "-C", str(ROOT), "log", "-n1", "--format=%h",
                                "--", "data/catalog"], capture_output=True, text=True,
                               timeout=10).stdout.strip()
            dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain",
                                    "data/catalog"], capture_output=True, text=True,
                                   timeout=10).stdout.strip()
            _catalog_commit = f"{h}+dirty" if dirty else (h or "unknown")
        except Exception:
            _catalog_commit = "unknown"
    return _catalog_commit


def _resolvable_terms(cat: "catalog_store.Catalog") -> dict[str, str]:
    """normkey -> término almacenado, de TODO lo que resolve() puede responder:
    canonical de consumibles + alias con destino consumible + paraguas no-candidate +
    términos de homónimo (el homónimo DEBE detectarse para poder fail-open/prefer)."""
    terms: dict[str, str] = {}

    import re as _re

    def _add(t: str) -> None:
        nk = C.normkey(t)
        if not nk:
            return
        # pre-exclusión SOLO digit-only (v2.2: '≤3 chars' mataba zxe) — a nivel de SEGMENTOS:
        # 'normkey' conserva '+'/'.' y dejaba pasar alias tipo '2+' cuyo core regex matchea un
        # '2' suelto ("2 lazos") — el smoke S1 lo cazó
        segs = "".join(_re.findall(r"[a-z]+|\d+", C._fold(t)))
        if not segs or segs.isdigit():
            return
        terms.setdefault(nk, t)

    for pid, p in cat.products.items():
        if p.get("estado") == "activo" and not p.get("candidate"):
            _add(p["canonical_model"])
    for a in cat.aliases:
        if not a.get("candidate") and cat._consumable(a["id"]):
            _add(a["alias"])
    for u in cat.umbrellas:
        if not u.get("candidate"):
            _add(u["termino"])
    for h in cat.homonyms:
        _add(h["termino"])
    return terms


def _build() -> None:
    global _loaded, _pattern, _cat, _docs_by_id
    _loaded = True
    try:
        cat = catalog_store.load()
    except Exception as e:                      # catálogo ausente/roto → resolver inerte
        logger.warning(f"catalog_resolver: catálogo no cargable ({e}) — fail-open total")
        return
    _cat = cat
    docs: dict[str, set[str]] = {}
    for dm in cat.doc_map:
        src = dm.get("source_file") or ""
        if not src:
            continue
        for e in dm.get("entries") or []:
            docs.setdefault(cat.follow_redirect(e["id"]), set()).add(src)
    _docs_by_id = {k: frozenset(v) for k, v in docs.items()}

    import re
    cores = []
    for nk, term in _resolvable_terms(cat).items():
        core = C._core(term)                    # mismo builder probado que el catálogo legacy
        if core:
            cores.append(core)
    cores.sort(key=len, reverse=True)           # longest-first: 'zx2se' antes que 'zx'
    seen: set[str] = set()
    alts = [c for c in cores if not (c in seen or seen.add(c))]
    if alts:
        # boundary trasero (?![a-z0-9]) — sin él, 'dimensiones' dispara el paraguas
        # 'Dimension' (reproducido por el dúo build-S1); (?!\d) solo no basta
        _pattern = re.compile(r"\b(" + "|".join(alts) + r")(?![a-z0-9])")


def _ensure() -> None:
    if not _loaded:
        _build()


def detect(query: str) -> list[str]:
    """Tokens del catálogo presentes en la query (match exacto word-boundary, folded)."""
    _ensure()
    if _pattern is None:
        return []
    folded = C._fold(query)
    out, seen = [], set()
    for m in _pattern.findall(folded):
        nk = C.normkey(m)
        if nk and nk not in seen:
            seen.add(nk)
            out.append(m)
    return out


def resolve_query(query: str) -> dict:
    """Detecta + resuelve por la puerta. Devuelve el registro completo (para seams y shadow):
    {detected, records[{token, via, politica, expand, ids}], add_models, drop_tokens,
     allowed_sources}. expand=False (clarify/candidate/unknown) NO aporta expansión ni
    allowed_sources — el contrato `expand` del resolve() se respeta literal (anti-hp011)."""
    _ensure()
    detected = detect(query)
    records, add_models, drop_tokens = [], [], []
    allowed: set[str] = set()
    if _cat is None:
        return {"detected": detected, "records": [], "add_models": [],
                "drop_tokens": [], "allowed_sources": frozenset()}
    for tok in detected:
        r = _cat.resolve(tok)
        if r is None:
            records.append({"token": tok, "via": None, "expand": False, "ids": []})
            continue
        rec = {"token": tok, "via": r.get("via"), "politica": r.get("politica"),
               "expand": bool(r.get("expand")), "ids": r.get("ids", [])}
        records.append(rec)
        if rec["expand"]:
            for pid in rec["ids"]:
                p = _cat.products.get(pid)
                if p and p.get("canonical_model"):
                    add_models.append(p["canonical_model"])
                allowed |= _docs_by_id.get(pid, frozenset())
            # solo paraguas/alias/homónimo-prefer REEMPLAZAN el token original en el brazo
            # replace (exact ya ES el canonical — reemplazarlo sería un no-op)
            if rec["via"] in ("paraguas", "alias", "homonimo"):
                drop_tokens.append(tok)
    return {"detected": detected, "records": records, "add_models": add_models,
            "drop_tokens": drop_tokens, "allowed_sources": frozenset(allowed)}


def apply_to_models(models: list[str], res: dict) -> list[str]:
    """Aplica la resolución a la lista `models` (seam 1). Brazo por env
    IDENTITY_RESOLVE_POLICY: 'add' (default; hipótesis anti-hp009) mantiene el token
    original Y añade variantes; 'replace' (el brazo MEDIDO de LEVER2) retira el token
    paraguas/alias resuelto. Dedup por normkey, orden estable."""
    # keying por catalog_store.norm_token (no C.normkey): C.normkey conserva '+'/'.', y un
    # match 'zx.2e' resolvería bien pero el drop fallaría silencioso (replace→add) — dúo #8
    policy = (os.getenv("IDENTITY_RESOLVE_POLICY", "") or "add").strip().lower()
    nt = catalog_store.norm_token
    drop = {nt(t) for t in res["drop_tokens"]} if policy == "replace" else set()
    out, seen = [], set()
    for m in models:
        nk = nt(m)
        if nk in drop or nk in seen:
            continue
        seen.add(nk)
        out.append(m)
    for m in res["add_models"]:
        nk = nt(m)
        if nk not in seen:
            seen.add(nk)
            out.append(m)
    return out


def _shadow_log(query: str, models_before: list[str], models_after: list[str],
                res: dict, applied: bool) -> None:
    """Log non-blocking a Supabase (tabla identity_resolve_shadow) — F2.5. Nunca rompe el path."""
    row = {
        "query": query[:1000],
        "mode": "on" if applied else "shadow",
        "policy": (os.getenv("IDENTITY_RESOLVE_POLICY", "") or "add").strip().lower(),
        "detected": res["detected"],
        "records": json.dumps(res["records"], ensure_ascii=False)[:4000],
        "models_before": models_before,
        "models_after": models_after,
        "allowed_sources_n": len(res["allowed_sources"]),
        "catalog_commit": catalog_commit(),
    }
    def _post() -> None:
        try:
            import httpx

            from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL
            headers = {"apikey": SUPABASE_SERVICE_KEY,
                       "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                       "Content-Type": "application/json", "Prefer": "return=minimal"}
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(f"{SUPABASE_URL}/rest/v1/identity_resolve_shadow",
                                   headers=headers, json=row)
                if resp.status_code >= 400:
                    logger.warning(f"identity_resolve_shadow no disponible ({resp.status_code}) "
                                   f"— S2 pierde su artefacto; registro local: "
                                   f"{json.dumps(row, ensure_ascii=False)[:500]}")
        except Exception as e:
            logger.warning(f"shadow-log fallback ({e}): {json.dumps(row, ensure_ascii=False)[:500]}")

    # fire-and-forget (dúo #5): el POST corre ANTES del vector search — 5s de timeout
    # síncrono en el path de cada query con token sería latencia real
    import threading
    threading.Thread(target=_post, daemon=True).start()


def resolve_for_retrieval(query: str, models: list[str]) -> tuple[list[str], dict | None]:
    """Punto de entrada ÚNICO del retriever (retrieve_chunks, una vez por query).
    off → passthrough exacto. shadow → passthrough + log de lo que HABRÍA cambiado.
    on → seam 1 aplicado; devuelve la resolución para el seam 2 (allowed_sources)."""
    m = mode()
    if m == "off":
        return models, None
    res = resolve_query(query)
    if not res["detected"]:
        return models, None
    models_after = apply_to_models(models, res)
    _shadow_log(query, models, models_after, res, applied=(m == "on"))
    if m == "shadow":
        return models, None
    return models_after, res
