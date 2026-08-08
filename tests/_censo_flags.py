"""s311/L2b — el CENSO de lecturas de entorno en `src/`, fuente ÚNICA (v5).

Lo usan el test de completitud Y el generador del registro — un solo escáner, cero
deriva entre ambos. Historia de versiones (cada patrón nuevo = un hueco cazado):
  v3  getenv/"environ"/_strict_on_off(1-arg)         (censo inicial)
  v4  +environ.get, +_strict_on_off(2-args), +_mp_flag, +const-indirecto
      (los destapó el pin fantasma de DEMO_FLAGS)
  v5  +comillas SIMPLES en todos los patrones (deep_lookup usaba
      `os.getenv('CHUNKS_TABLE'...)` y la clase entera era invisible — Sol s311),
      +PROFILE_OWNED_FLAGS por IMPORT del propio constante (bucle con nombre
      dinámico en release_profiles:161 — crítico de Sol),
      +flags data-driven de config/manufacturers/*.yaml (series_registry hace
      `os.getenv(str(flag))` — Sol s311), +normalización de comillas en defaults
      (la divergencia tipográfica no es divergencia).

Alcance honesto (sin cambios): completitud NOMINAL de call-sites conocidos; una vía
de lectura NUEVA exige su patrón aquí (y este docstring exige contar de dónde salió).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_Q = "[\"']"          # ambas comillas — la lección deep_lookup
_VIAS_MECANICAS = {"profile-owned-loop"}      # + las series-registry-yaml:* por prefijo


def _norm_default(default: str) -> str:
    """'x' y "x" son EL MISMO default — la comparación es semántica, no tipográfica."""
    d = default.strip()
    if len(d) >= 2 and d[0] == "'" and d[-1] == "'":
        d = '"' + d[1:-1] + '"'
    return d


def escanear() -> dict[str, dict]:
    """nombre -> {"defaults": set, "defaults_codigo": set, "lectores": set, "vias": set}

    `defaults_codigo` excluye los placeholders mecánicos de las vías data-driven/loop
    (yaml→None, profile-owned→"off"): la DIVERGENCIA se computa solo sobre elecciones
    reales de lectores de código.
    """
    out: dict[str, dict] = {}

    def add(nombre, default, fichero, via):
        d = _norm_default(default)
        e = out.setdefault(nombre, {"defaults": set(), "defaults_codigo": set(),
                                    "lectores": set(), "vias": set()})
        e["defaults"].add(d)
        mecanica = via in _VIAS_MECANICAS or via.startswith("series-registry-yaml")
        if not mecanica:
            e["defaults_codigo"].add(d)
        e["lectores"].add(fichero)
        e["vias"].add(via)

    for f in (REPO / "src").rglob("*.py"):
        t = f.read_text(encoding="utf-8")
        rel = f.relative_to(REPO).as_posix()
        for m in re.finditer(
                rf'os\.getenv\(\s*{_Q}([A-Z_0-9]+){_Q}\s*(?:,\s*([^)]+?))?\s*\)', t):
            add(m.group(1), (m.group(2) or "None").strip(), rel, "getenv")
        for m in re.finditer(rf'os\.environ\.get\(\s*{_Q}([A-Z_0-9]+){_Q}', t):
            add(m.group(1), "None", rel, "environ.get")
        for m in re.finditer(rf'os\.environ\[\s*{_Q}([A-Z_0-9]+){_Q}\s*\]', t):
            add(m.group(1), "(REQUERIDA)", rel, "environ")
        for m in re.finditer(rf'_strict_on_off\(\s*{_Q}([A-Z_0-9]+){_Q}', t):
            d = re.search(
                rf'_strict_on_off\(\s*{_Q}{m.group(1)}{_Q}\s*,\s*{_Q}(\w+){_Q}', t)
            add(m.group(1), f'"{d.group(1)}"' if d else '"off"', rel, "strict_on_off")
        for m in re.finditer(rf'_mp_flag\(\s*{_Q}([A-Z_0-9]+){_Q}', t):
            add(m.group(1), '"off"', rel, "mp_flag")
        for c in re.finditer(rf'^(\w+)\s*=\s*{_Q}([A-Z_0-9]+){_Q}\s*$', t, re.M):
            if re.search(rf'os\.getenv\(\s*{c.group(1)}\b', t):
                add(c.group(2), "None", rel, "getenv-indirecto")
            if re.search(rf'\.get\(\s*{c.group(1)}\b', t):
                add(c.group(2), "None", rel, "mapping.get-indirecto")

    # PROFILE_OWNED_FLAGS: el modo legacy las lee TODAS en bucle con nombre dinámico
    # (release_profiles:159-161) — el propio constante es la fuente, no un regex.
    from src.release_profiles import PROFILE_OWNED_FLAGS
    for nombre in PROFILE_OWNED_FLAGS:
        add(nombre, '"off"', "src/release_profiles.py", "profile-owned-loop")

    # Flags data-driven: series_registry hace os.getenv(str(flag)) con el nombre
    # venido de config/manufacturers/*.yaml (`flag: NOMBRE`).
    for y in (REPO / "config" / "manufacturers").glob("*.yaml"):
        for m in re.finditer(r'^\s*flag:\s*([A-Z_0-9]+)\s*$',
                             y.read_text(encoding="utf-8"), re.M):
            add(m.group(1), "None", "src/rag/series_registry.py",
                f"series-registry-yaml:{y.name}")

    return out


def divergencias(censo: dict[str, dict]) -> set[str]:
    """Flags con defaults DISTINTOS entre lectores DE CÓDIGO (los placeholders
    mecánicos no cuentan)."""
    return {n for n, e in censo.items() if len(e["defaults_codigo"]) > 1}
