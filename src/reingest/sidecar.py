"""Provenance del portal firesecurityproducts (Capa B del seam de Fase 2).

Los lotes del portal se descargan a `Manuales_<Canal>/` con un sidecar
`_metadata.json` (lista de `{local_filename, equipo, series, skus, ...}`). Para
esos docs la identidad del producto sale del SIDECAR (`equipo` = modelo real del
PIM), NO de un regex sobre el filename — que para marcas nuevas producía basura
(`HASTA-256`, `REV-005`, `EN-54-20`).

El FABRICANTE es el canal (la carpeta), corregido por los OEM overrides de
`config/portal.yaml` (p.ej. la serie 2X-A es Aritech aunque se baje por el canal
Kidde). El `distributor` se deriva del canal cuando difiere del fabricante.

Restringido a los canales declarados en `config/portal.yaml`: el corpus viejo
(Morley_Guias tiene un `_metadata.json` de formato distinto — `marca`/`familia`/
`titulo`) NO se ve afectado.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PORTAL_CONFIG = os.path.join(_ROOT, "config", "portal.yaml")


@lru_cache(maxsize=1)
def _config() -> dict:
    if not os.path.isfile(_PORTAL_CONFIG):
        return {"channels": [], "oem_overrides": []}
    with open(_PORTAL_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=64)
def _sidecar_index(folder_abs: str) -> dict:
    """{local_filename.lower(): entry} del _metadata.json de una carpeta, o {}."""
    path = os.path.join(folder_abs, "_metadata.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    out = {}
    for e in data if isinstance(data, list) else []:
        fn = e.get("local_filename") if isinstance(e, dict) else None
        if fn:
            out[fn.lower()] = e
    return out


def _channel_and_folder(source_path: str) -> tuple[str | None, str | None]:
    """(canal, carpeta_abs) si el doc está en un canal del portal; (None, None) si no.

    Robusto a `source_path` relativo (al repo) o absoluto: usa la carpeta
    CONTENEDORA (`Manuales_<canal>`) directamente, no una reconstrucción desde
    _ROOT — un path absoluto reconstruido bajo _ROOT daba una ruta falsa y
    desactivaba Capa B en silencio (hallazgo del revisor cross-model)."""
    folder = os.path.dirname(source_path.replace("\\", "/"))
    channel_dir = os.path.basename(folder)
    if not channel_dir.startswith("Manuales_"):
        return None, None
    channel = channel_dir[len("Manuales_"):]
    if channel not in (_config().get("channels", []) or []):
        return None, None
    abs_folder = folder if os.path.isabs(folder) else os.path.join(_ROOT, folder)
    return channel, abs_folder


def is_portal_channel(source_path: str) -> bool:
    """True si el doc vive en un canal del portal declarado (con o sin entrada en
    el sidecar). Lo usa B5 para alarmar el fallo-abierto: un doc de canal portal
    SIN entrada cae al regex viejo = reaparece la basura que Capa B erradica."""
    return _channel_and_folder(source_path)[0] is not None


def lookup(source_path: str) -> dict | None:
    """Entrada del sidecar del portal para este doc, o None si no es del portal."""
    _channel, folder = _channel_and_folder(source_path)
    if not folder:
        return None
    return _sidecar_index(folder).get(os.path.basename(source_path).lower())


def channel_manufacturer(source_path: str, equipo: str | None
                         ) -> tuple[str | None, str | None]:
    """(manufacturer, distributor) de un doc del portal cuando NINGÚN patrón de
    marca específico (Securiton/Pfannenberg/...) lo resolvió por filename.

    Aplica los OEM overrides (por prefijo de `equipo`); el distributor se deriva
    del canal cuando difiere del fabricante. Para el canal genérico "Otros" sin
    override → (None, None): la marca queda sin resolver (mejor que inventarla).
    """
    channel, _folder = _channel_and_folder(source_path)
    if not channel:
        return None, None
    eq = (equipo or "").upper()
    for ov in _config().get("oem_overrides", []) or []:
        prefix = str(ov.get("equipo_prefix", "")).strip().upper()
        # Un prefix vacío casaría TODO (toda cadena .startswith("")) → se ignora:
        # un typo en el YAML no debe contaminar el fabricante de un lote entero.
        if prefix and eq.startswith(prefix):
            mfr = ov.get("manufacturer")
            return mfr, (channel if channel != mfr else None)
    if channel == "Otros":
        return None, None
    return channel, None


def reload() -> None:
    """Limpia las caches (tests / tras editar config/portal.yaml o un sidecar)."""
    _config.cache_clear()
    _sidecar_index.cache_clear()
