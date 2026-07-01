"""(s86 B2 · flag IDENTITY_MAP, default OFF = prod inerte) Consumo FILTER-BASED del registro
canónico data-driven (activo DEC-067). Resuelve el query-model a docs-de-familia vía el
`family_scope` del `s83_document_identity_final.jsonl` (identidad por-doc: umbrella + familia +
brand + OEM) y expone el set de source_files permitidos. El model-filter lo consume SUBTRACTIVO
(limpia el wrong-family que el substring del tag DB no separa) — NO aditivo (DEC-069 = NO-OP).

Por qué `family_scope` y no el índice model-keyed s84: el índice está keyed por modelo real
(zx2e/zx5e) y NO tiene el paraguas "ZXe" → un query "ZXe" no matchea (smoke s86). El `family_scope`
SÍ tiene el umbrella ("ZXe (ZX1e/ZX2e/ZX5e)") Y separa familias (ZXe vs ZXAE/ZXEE; RP1r-Supra vs
RP1r vs VSN) → resolución de identidad data-driven SIN curar YAML por-familia (el valor de escala).

Matching robusto a near-colisiones: tokeniza `family_scope` en espacios/`/`/`()`/`,` → `catalog.normkey`
cada token (strips -, espacio, /). Así el query-model normkey debe igualar un token ENTERO del scope:
'zxe'≠'zxae'/'zxee', 'afp400'≠'afp4000', 'rp1rsupra'≠'rp1r'. NO substring (que colisionaba).

Ship: el jsonl vive en `evals/` (branch-local) → relocalizar + rebuild pipeline. Flag-gated hasta medir + dúo.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from src.rag import catalog as C

_JSONL_PATH = Path(__file__).resolve().parents[2] / "evals" / "s83_document_identity_final.jsonl"
_SPLIT = re.compile(r"[\s/(),;|]+")
_FAM: dict[str, frozenset[str]] | None = None   # source_file -> {token-normkeys del family_scope}


def _scope_tokens(scope: str) -> frozenset[str]:
    toks = {C.normkey(t) for t in _SPLIT.split(scope or "") if t.strip()}
    return frozenset(t for t in toks if t)


def _load() -> dict[str, frozenset[str]]:
    global _FAM
    if _FAM is None:
        fam: dict[str, frozenset[str]] = {}
        try:
            for line in _JSONL_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                sf = d.get("source_file")
                if sf:
                    fam[sf] = _scope_tokens(d.get("family_scope"))
        except Exception:
            fam = {}
        _FAM = fam
    return _FAM


def allowed_sources(models: list[str]) -> frozenset[str]:
    """source_files cuyo family_scope contiene (como token entero) algún query-model normkey.
    frozenset() vacío = sin cobertura → el caller hace fail-open."""
    query_nk = {C.normkey(m) for m in (models or []) if m}
    query_nk.discard("")
    if not query_nk:
        return frozenset()
    fam = _load()
    return frozenset(sf for sf, toks in fam.items() if toks & query_nk)
