"""Catálogo de modelos dirigido por dato — reemplaza la enumeración hardcoded
de MODEL_PATTERN.

Carga el snapshot curado ``data/model_catalog.json`` (lo construye offline
``scripts/build_model_catalog.py`` desde CHUNKS_TABLE) y expone:

  - extract_models(query)      → códigos de modelo presentes en la query
  - model_manufacturer(model)  → fabricante de un modelo detectado, o None
  - catalog_available()        → False si el snapshot falta/corrupto (el caller
                                 debe caer al seed MODEL_PATTERN como fail-safe)

La semántica de matching replica la del MODEL_PATTERN probado (word-boundary +
guard de extensión de dígito ``(?!\\d)`` + separadores opcionales), pero la
alternancia se GENERA desde el corpus en vez de escribirse a mano, y el match es
insensible a acentos (``MINILÁSER25`` almacenado matchea una query
"minilaser 25"). El detector devuelve la forma CANÓNICA almacenada para que el
matching posterior contra la BD (``model_to_imatch_pattern`` → ``imatch`` sobre
``product_model``) acierte el valor con acento.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "model_catalog.json"

_loaded = False
_pattern: re.Pattern | None = None
_normkey_to_model: dict[str, str] = {}
_model_to_mfr: dict[str, str] = {}
_model_count: dict[str, int] = {}


def _fold(s: str) -> str:
    """Minúsculas + sin diacríticos, conservando separadores/espacios."""
    nfkd = unicodedata.normalize("NFKD", s)
    no_acc = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_acc.lower()


def _normkey(s: str) -> str:
    """Fold + sin separadores → clave canónica de lookup."""
    return re.sub(r"[-\s/]+", "", _fold(s))


def normkey(s: str) -> str:
    """Clave canónica pública (fold + sin separadores), para dedup en callers
    que mezclan resultados del catálogo y del seed pattern."""
    return _normkey(s)


# Separador opcional entre segmentos de un código: cero o más caracteres de
# separación REALES (-, espacio, /, ., +). Excluye coma y demás puntuación que
# marca fin de palabra → evita que "clase s, 20" matchee el modelo "S20".
_SEP = r"[-\s/.+]*"


def _segments(folded: str) -> list[str]:
    """Runs maximales de letras o de dígitos (ignora separadores)."""
    return re.findall(r"[a-z]+|\d+", folded)


def _core(model: str) -> str:
    """Modelo → core regex separador-insensible. Segmenta por transición
    letra/dígito y por separadores, uniéndolos con _SEP opcional, de modo que
    'MS-5210UD' matchee 'ms 5210 ud', 'ms-5210ud' y 'ms5210ud'."""
    segs = _segments(_fold(model))
    if not segs:
        return ""
    return _SEP.join(re.escape(s) for s in segs)


def _base_aliases(model: str) -> list[str]:
    """Familia base de un modelo con sufijo de variante: 'CAD-150-8' → ['CAD-150'].
    Permite que una query a nivel de familia recupere las variantes (el imatch
    sobre product_model las cubre). Solo si la base conserva un dígito."""
    parts = [p for p in re.split(r"[-\s/]+", model) if p]
    if len(parts) >= 3:
        base = "-".join(parts[:-1])
        if any(c.isdigit() for c in base):
            return [base]
    return []


def _load() -> None:
    global _loaded, _pattern
    _loaded = True
    if not _SNAPSHOT_PATH.is_file():
        return
    try:
        data = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    models = data.get("models", [])
    if not models:
        return

    # Modelos reales primero, alias de familia después → con setdefault el real
    # tiene precedencia sobre un alias que colisione en la misma normkey.
    # Cada entrada lleva su chunk_count (los alias heredan el del padre).
    entries: list[tuple[str, str | None, int]] = [
        (m["model"], m.get("manufacturer"), m.get("chunk_count", 0)) for m in models]
    for m in models:
        for base in _base_aliases(m["model"]):
            entries.append((base, m.get("manufacturer"), m.get("chunk_count", 0)))

    cores: list[str] = []
    for canonical, mfr, cnt in entries:
        nk = _normkey(canonical)
        if not nk:
            continue
        _normkey_to_model.setdefault(nk, canonical)
        _model_count[nk] = max(_model_count.get(nk, 0), cnt)
        if mfr and mfr != "unknown":
            _model_to_mfr.setdefault(nk, mfr)
        core = _core(canonical)
        if core:
            cores.append(core)

    # Core más largo primero: 'cad-150-8' tiene prioridad sobre 'cad-150'.
    cores.sort(key=len, reverse=True)
    seen: set[str] = set()
    alts: list[str] = []
    for core in cores:
        if core not in seen:
            seen.add(core)
            alts.append(core)
    if not alts:
        return
    # query y cores ya van folded (lowercase) → no hace falta IGNORECASE.
    _pattern = re.compile(r"\b(" + "|".join(alts) + r")(?!\d)")


def _ensure() -> None:
    if not _loaded:
        _load()


def catalog_available() -> bool:
    _ensure()
    return _pattern is not None


def extract_models(query: str) -> list[str]:
    """Devuelve los modelos canónicos del catálogo presentes en la query,
    en orden de aparición y deduplicados. [] si el catálogo no está disponible."""
    _ensure()
    if _pattern is None:
        return []
    folded = _fold(query)
    out: list[str] = []
    seen: set[str] = set()
    for match in _pattern.findall(folded):
        canonical = _normkey_to_model.get(_normkey(match))
        if canonical and canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out


def all_models() -> list[str]:
    """Todas las formas canónicas del catálogo (fuente única de modelos).
    La consume el vocabulario de Whisper (src/bot/whisper_vocabulary.py) para
    no mantener una lista de modelos aparte. Ordenado por frecuencia (chunk_count
    desc) → los consumidores con límite de longitud (Whisper) cubren primero los
    modelos más comunes. [] si no hay snapshot."""
    _ensure()
    uniq = set(_normkey_to_model.values())
    return sorted(uniq, key=lambda mdl: (-_model_count.get(_normkey(mdl), 0), mdl))


def model_manufacturer(model: str) -> str | None:
    """Fabricante de un modelo (vía dict en memoria, sin roundtrip a BD).
    None si el modelo no está en el catálogo o tiene fabricante unknown."""
    _ensure()
    return _model_to_mfr.get(_normkey(model))


def reload_snapshot() -> None:
    """Fuerza recarga del snapshot (tests / refresh tras regenerar el JSON)."""
    global _loaded, _pattern, _normkey_to_model, _model_to_mfr, _model_count
    _loaded = False
    _pattern = None
    _normkey_to_model = {}
    _model_to_mfr = {}
    _model_count = {}
    _ensure()
