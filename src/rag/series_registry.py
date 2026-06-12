"""Registry de series producto↔familia para retrieval (ciclo A s63 — DEC-043, TECH_DEBT #43).

El mecanismo que arregla (medido, audit #43): `_filter_to_query_models` matchea por
SUBSTRING direccional ("am8200" ⊂ "am8200g") → (d1) la query de un producto BASE
arrastra a sus HERMANOS de serie (cat012: las fórmulas §11 de AM-8200G/N expulsan
del top-5 la tabla del producto correcto), y (d2) la query de una VARIANTE no
alcanza los docs compartidos de su serie (CAD-201 nunca ve el MC-380, etiquetado
CAD-250).

Principio (diseño FINAL s63, post-dúo r1+r2): la REGLA vive aquí; el CONOCIMIENTO
vive en `config/manufacturers/*.yaml` (seam s55, clave `series:` que el loader de
ingesta ignora). El substring histórico se MANTIENE como base; el registry solo
añade (i) VETOS de hermanos declarados y (ii) APERTURAS de docs-compartidos
declarados. Sin entrada de registry → comportamiento histórico intacto.

Esquema yaml (por fabricante):

    series:
      - name: Vesta
        members: [CAD-171, CAD-201, CAD-250]
        evidence: "DEC-032 + inventario s63"
        shared_docs:
          - source_file: "CAD-250_Manual-Configuracion-MC-380-es-2026-c"   # EXACTO
            evidence: "manual de configuración de la serie — edición vigente"

Contratos:
- `source_file` de shared_docs es EXACTO (literal contra el campo source_file del
  chunk; el match in-memory es case-insensitive defensivo). Sin substring: evita
  capturar ediciones/docs no curados (r2 Z4/R13).
- `evidence` obligatorio por entrada — la validación DURA vive en tests
  (tests/test_series_registry.py); el runtime es fail-open con warning.
- Ownership por CONJUNTO con maximal-munch por ocurrencia (r2 R3): un member es
  owner del product_model si su core matchea en alguna posición donde ningún core
  MÁS LARGO de la serie empieza en esa misma posición. Resuelve el anidamiento
  ("am8200g" pertenece a G, no al base) sin romper docs conjuntos de dos members
  (pm "M700KAC + M700KACI" → owners ambos).
- Runtime NUNCA raise (fail-open, patrón catalog.py — NO el import-raise de
  manufacturer_registry.py, que es correcto para CLI de ingesta y fatal en bot):
  yaml ilegible → skip fichero; entrada malformada → skip entrada; colisión de
  member entre dos series → se descartan AMBAS series. Siempre con warning.
- `SERIES_REGISTRY_ENABLED=false` → registry vacío → nivel-1 puro (toggle del
  brazo control del A/B y kill-switch de rollback en prod, precedente CHUNKS_TABLE).
- Observabilidad (r2 Z5): log con N series / members / shared al cargar +
  `registry_fingerprint()` para estampar en manifests de eval (evita "evaluar
  tratamiento" con registry silenciosamente vacío).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Monkeypatchable en tests (tmp_path); en producción apunta al seam s55.
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "manufacturers"


def series_enabled() -> bool:
    """Flag de activación. Default ON; `SERIES_REGISTRY_ENABLED=false` lo apaga
    (registry vacío = comportamiento histórico exacto)."""
    return os.getenv("SERIES_REGISTRY_ENABLED", "true").strip().lower() not in (
        "false", "0", "no", "off",
    )


def normalize_model(s: str) -> str:
    """LA normalización canónica del subsistema filtro+series (idéntica a la
    histórica de `_filter_to_query_models`: quita '-'/espacio, lowercase).
    catalog.py (detección) mantiene la suya — aquí solo retrieval-filtrado."""
    return re.sub(r"[- ]", "", s or "").lower()


class Series:
    """Una serie declarada: members (productos hermanos) + shared_docs (docs de
    familia, por source_file exacto)."""

    __slots__ = ("name", "manufacturer", "members", "member_cores",
                 "shared_sources", "_shared_lower")

    def __init__(self, name: str, manufacturer: str | None, members: list[str],
                 shared_sources: list[str]):
        self.name = name
        self.manufacturer = manufacturer
        self.members = members
        self.member_cores = {normalize_model(m) for m in members if normalize_model(m)}
        self.shared_sources = shared_sources                 # forma EXACTA del yaml
        self._shared_lower = {s.lower() for s in shared_sources}

    def is_shared_source(self, source_file: str | None) -> bool:
        return bool(source_file) and source_file.lower() in self._shared_lower

    def owners(self, pm_norm: str) -> set[str]:
        """Cores de los members que 'ownean' este product_model normalizado.
        Maximal-munch por ocurrencia: un core gana en una posición solo si ningún
        core más largo de la serie empieza en esa misma posición. Conjunto vacío =
        el pm no pertenece a ningún member identificable (la serie no opina)."""
        if not pm_norm:
            return set()
        found: set[str] = set()
        for core in self.member_cores:
            start = pm_norm.find(core)
            while start != -1:
                if not any(
                    len(other) > len(core) and pm_norm.startswith(other, start)
                    for other in self.member_cores
                ):
                    found.add(core)
                    break
                start = pm_norm.find(core, start + 1)
        return found


class _Registry:
    def __init__(self) -> None:
        self.by_member_core: dict[str, Series] = {}
        self.series: list[Series] = []
        self.fingerprint: str = "empty"

    @property
    def stats(self) -> tuple[int, int, int]:
        n_members = sum(len(s.member_cores) for s in self.series)
        n_shared = sum(len(s.shared_sources) for s in self.series)
        return (len(self.series), n_members, n_shared)


def _parse_series(raw: object, manufacturer: str | None, filename: str) -> Series | None:
    """Valida una entrada `series:` del yaml. Fail-open: None + warning si está
    malformada. La validación estricta (evidence, resolución contra corpus) vive
    en tests — aquí solo lo que impediría operar."""
    if not isinstance(raw, dict):
        logger.warning("series_registry: entrada no-dict en %s — ignorada", filename)
        return None
    name = raw.get("name")
    members = raw.get("members") or []
    if not name or not isinstance(members, list) or not members:
        logger.warning("series_registry: serie sin name/members en %s — ignorada", filename)
        return None
    members = [str(m) for m in members if m and normalize_model(str(m))]
    if not members:
        logger.warning("series_registry: serie '%s' sin members válidos (%s) — ignorada",
                       name, filename)
        return None
    shared: list[str] = []
    for item in raw.get("shared_docs") or []:
        if not isinstance(item, dict) or not item.get("source_file"):
            logger.warning("series_registry: shared_doc sin source_file en serie '%s' (%s)"
                           " — ignorado", name, filename)
            continue
        if not item.get("evidence"):
            logger.warning("series_registry: shared_doc '%s' sin evidence en serie '%s' (%s)",
                           item.get("source_file"), name, filename)
        shared.append(str(item["source_file"]))
    if not raw.get("evidence"):
        logger.warning("series_registry: serie '%s' sin evidence (%s)", name, filename)
    if len(members) < 2 and not shared:
        # Anti-degeneración: sin hermanos que vetar NI docs que abrir, la entrada
        # no hace nada — mejor señalarla que cargarla muerta.
        logger.warning("series_registry: serie '%s' (1 member, 0 shared) no hace nada"
                       " (%s) — ignorada", name, filename)
        return None
    return Series(str(name), manufacturer, members, shared)


def _load() -> _Registry:
    reg = _Registry()
    if not series_enabled():
        reg.fingerprint = "disabled"
        logger.info("series_registry: DESACTIVADO por SERIES_REGISTRY_ENABLED")
        return reg
    candidates: list[Series] = []
    if _CONFIG_DIR.is_dir():
        for path in sorted(_CONFIG_DIR.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                logger.warning("series_registry: yaml ilegible %s (%s) — ignorado"
                               " (fail-open)", path.name, exc)
                continue
            if not isinstance(data, dict):
                continue
            mfr = data.get("manufacturer")
            for raw in data.get("series") or []:
                s = _parse_series(raw, mfr, path.name)
                if s is not None:
                    candidates.append(s)

    # Colisión de member entre DOS series → descartar AMBAS (degradan a nivel-1;
    # el test duro lo impide llegar a main — aquí solo protegemos el runtime).
    core_owners: dict[str, list[Series]] = {}
    for s in candidates:
        for core in s.member_cores:
            core_owners.setdefault(core, []).append(s)
    dropped: set[int] = set()
    for core, series_l in core_owners.items():
        if len({id(s) for s in series_l}) > 1:
            names = sorted({s.name for s in series_l})
            logger.warning("series_registry: member '%s' declarado en series %s — TODAS"
                           " descartadas (fail-open a nivel-1)", core, names)
            dropped.update(id(s) for s in series_l)

    reg.series = [s for s in candidates if id(s) not in dropped]
    for s in reg.series:
        for core in s.member_cores:
            reg.by_member_core[core] = s

    if reg.series:
        canon = sorted(
            (
                {
                    "name": s.name,
                    "manufacturer": s.manufacturer,
                    "members": sorted(s.member_cores),
                    "shared": sorted(x.lower() for x in s.shared_sources),
                }
                for s in reg.series
            ),
            key=lambda d: d["name"],
        )
        reg.fingerprint = hashlib.sha256(
            json.dumps(canon, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
    n_series, n_members, n_shared = reg.stats
    logger.info("series_registry: %d series / %d members / %d shared_docs"
                " (fingerprint %s)", n_series, n_members, n_shared, reg.fingerprint)
    return reg


_REG: _Registry | None = None


def _get() -> _Registry:
    # Carga lazy al primer uso (patrón catalog.py). Race benigna si dos hilos
    # cargan a la vez: el resultado es idéntico e idempotente.
    global _REG
    if _REG is None:
        _REG = _load()
    return _REG


def reset_registry_cache() -> None:
    """Para tests (recargar tras monkeypatch de _CONFIG_DIR o del flag)."""
    global _REG
    _REG = None


# --------------------------------------------------------------------------
# API que consume el retriever
# --------------------------------------------------------------------------

def series_for(model: str) -> Series | None:
    """Serie a la que pertenece un modelo de query (por normkey de member).
    None → el registry no opina sobre ese modelo (nivel-1)."""
    return _get().by_member_core.get(normalize_model(model))


def any_series(models: list[str]) -> bool:
    """¿Algún modelo de la query tiene entrada de serie? (decide nivel 1 vs 2)."""
    return any(series_for(m) is not None for m in models or [])


def shared_sources_for(models: list[str]) -> list[str]:
    """source_files EXACTOS (forma yaml) de los shared_docs de las series de la
    query, dedupe con orden estable. Para el descubrimiento de diversify (d2)."""
    out: list[str] = []
    seen: set[str] = set()
    for m in models or []:
        s = series_for(m)
        if s is None:
            continue
        for sf in s.shared_sources:
            key = sf.lower()
            if key not in seen:
                seen.add(key)
                out.append(sf)
    return out


def passes_nivel2(chunk: dict, models: list[str]) -> bool:
    """El predicado ÚNICO del nivel 2 (lo usan el filtro Y diversify — r2 R4/Z1:
    una sola fuente de verdad, unión por modelo de la query).

    Un chunk pasa si para ALGÚN modelo m de la query:
      (a) pasa el substring histórico Y no es un hermano vetado de la serie de m, o
      (b) su source_file es un doc compartido declarado de la serie de m.
    """
    pm_norm = normalize_model(chunk.get("product_model", ""))
    source_file = chunk.get("source_file") or ""
    for m in models or []:
        core = normalize_model(m)
        if not core:
            continue
        s = series_for(m)
        if core in pm_norm:
            if s is None:
                return True
            if s.is_shared_source(source_file):
                return True
            own = s.owners(pm_norm)
            if not own or core in own:
                return True
        elif s is not None and s.is_shared_source(source_file):
            return True
    return False


def registry_fingerprint() -> str:
    """Hash estable del contenido efectivo cargado ('empty' sin series,
    'disabled' con el flag off). Se estampa en manifests de eval (r2 Z5/R2d)."""
    return _get().fingerprint


def registry_stats() -> tuple[int, int, int]:
    """(n_series, n_members, n_shared_docs) — para logs/reportes de gate."""
    return _get().stats
