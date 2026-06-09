"""Registro de identidad de marca dirigido por datos (Capa A — seam de Fase 2).

Externaliza las tablas de detección de marca/modelo que vivían hardcodeadas en
`metadata.py` a `config/manufacturers/*.yaml`. Cada archivo = UNA marca con sus
señales (todas mapean a esa marca + su distribuidor). `_global.yaml` lleva lo
transversal: códigos no-producto (normas/certs) y el regex de modelo genérico.

**Por qué un registry y no 30 ediciones de código (PLAN_RAG_2026 §Fase 2):** añadir
un fabricante = añadir un YAML, sin tocar lógica. Las 28 marcas vivas no regresan
porque el contenido es idéntico (test de equivalencia en `tests/test_manufacturer_registry.py`).

**El ORDEN importa y NO depende del filesystem** (corrección del revisor cross-model):
en `_detect_brand` los `brand_patterns` se evalúan en secuencia y el primer match gana,
así que el orden es SEMÁNTICO. Se preserva con la clave `eval_order` de cada marca, no
por orden de carga de archivos. Los demás (prefijos, letter-models = dict lookup;
folder-hints = needles disjuntos) son orden-insensibles.
"""
from __future__ import annotations

import glob as _glob
import os
import re

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_DIR = os.path.join(_ROOT, "config", "manufacturers")
_GLOBAL_FILE = "_global.yaml"


class _Registry:
    def __init__(self) -> None:
        self.brand_patterns: list[tuple[re.Pattern, str, str | None]] = []
        self.filename_only_patterns: list[tuple[re.Pattern, str, str | None]] = []
        self.letter_models: dict[str, tuple[str, str | None]] = {}
        self.main_mfr_by_prefix: dict[str, str] = {}
        self.folder_hints: list[tuple[str, str, str | None]] = []
        self.non_product_codes: set[str] = set()
        self.generic_model_re: re.Pattern | None = None


def _load() -> _Registry:
    reg = _Registry()
    if not os.path.isdir(_CONFIG_DIR):
        raise FileNotFoundError(f"No existe el registro de fabricantes: {_CONFIG_DIR}")

    brand_entries: list[tuple[int, int, str, str, str | None]] = []
    for path in sorted(_glob.glob(os.path.join(_CONFIG_DIR, "*.yaml"))):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if os.path.basename(path) == _GLOBAL_FILE:
            reg.non_product_codes = set(data.get("non_product_codes", []) or [])
            rx = data.get("generic_model_regex")
            if rx:
                reg.generic_model_re = re.compile(rx)
            continue

        mfr = data.get("manufacturer")
        distr = data.get("distributor")
        order = data.get("eval_order", 10**6)  # sin eval_order → al final, estable
        # brand_patterns: se difieren para ordenarlos globalmente por eval_order.
        for i, pat in enumerate(data.get("brand_patterns", []) or []):
            brand_entries.append((order, i, pat, mfr, distr))
        for pat in data.get("filename_patterns", []) or []:
            reg.filename_only_patterns.append((re.compile(pat, re.IGNORECASE), mfr, distr))
        # letter_models / model_prefixes son dict lookups (orden-insensibles), PERO
        # una colisión entre dos YAML con marcas distintas se pisaría en silencio
        # (esperable con OEM/relabeling a 30+ marcas) → fallar fuerte (cross-model).
        for model in data.get("letter_models", []) or []:
            prev = reg.letter_models.get(model)
            if prev is not None and prev != (mfr, distr):
                raise ValueError(
                    f"letter_model '{model}' en conflicto: {prev} vs {(mfr, distr)} ({path})")
            reg.letter_models[model] = (mfr, distr)
        for prefix in data.get("model_prefixes", []) or []:
            prev = reg.main_mfr_by_prefix.get(prefix)
            if prev is not None and prev != mfr:
                raise ValueError(
                    f"model_prefix '{prefix}' en conflicto: {prev} vs {mfr} ({path})")
            reg.main_mfr_by_prefix[prefix] = mfr
        for needle in data.get("folder_hints", []) or []:
            reg.folder_hints.append((needle, mfr, distr))

    # Orden SEMÁNTICO de brand_patterns: por eval_order de marca, luego orden local.
    brand_entries.sort(key=lambda e: (e[0], e[1]))
    reg.brand_patterns = [(re.compile(pat, re.IGNORECASE), mfr, distr)
                          for _, _, pat, mfr, distr in brand_entries]
    return reg


_REGISTRY = _load()

# Estructuras a nivel-módulo (contrato estable que consume metadata.py).
BRAND_PATTERNS = _REGISTRY.brand_patterns
FILENAME_ONLY_PATTERNS = _REGISTRY.filename_only_patterns
LETTER_MODELS = _REGISTRY.letter_models
MAIN_MFR_BY_PREFIX = _REGISTRY.main_mfr_by_prefix
FOLDER_HINTS = _REGISTRY.folder_hints
NON_PRODUCT_CODES = _REGISTRY.non_product_codes
GENERIC_MODEL_RE = _REGISTRY.generic_model_re


def reload() -> None:
    """Recarga el registro desde disco (tests / tras editar YAML)."""
    global _REGISTRY, BRAND_PATTERNS, FILENAME_ONLY_PATTERNS, LETTER_MODELS
    global MAIN_MFR_BY_PREFIX, FOLDER_HINTS, NON_PRODUCT_CODES, GENERIC_MODEL_RE
    _REGISTRY = _load()
    BRAND_PATTERNS = _REGISTRY.brand_patterns
    FILENAME_ONLY_PATTERNS = _REGISTRY.filename_only_patterns
    LETTER_MODELS = _REGISTRY.letter_models
    MAIN_MFR_BY_PREFIX = _REGISTRY.main_mfr_by_prefix
    FOLDER_HINTS = _REGISTRY.folder_hints
    NON_PRODUCT_CODES = _REGISTRY.non_product_codes
    GENERIC_MODEL_RE = _REGISTRY.generic_model_re
