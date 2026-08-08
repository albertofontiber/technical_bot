"""L2a/s310 — traducción de rutas CONGELADAS de la isla a su ubicación VIVA.

Los permisos/preregs de s114-s212 pinan `{path, sha256}` de módulos que L2a movió a
`harness/`. El YAML/JSON congelado es REGISTRO y no se toca (precedente s274: el
prereg histórico queda intacto; el TEST re-ancla el fichero vivo). Los renames son
BYTE-PUROS, así que el sha congelado sigue verificando contra el fichero movido —
esta traducción solo dice DÓNDE vive ahora cada byte pineado.
"""
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_MOVIDOS = {p.stem for p in (_REPO / "harness").glob("*.py")} - {"__init__"}


def ruta_viva(path: str) -> Path:
    p = Path(path)
    if (len(p.parts) == 3 and p.parts[0] == "src"
            and p.parts[1] in ("rag", "reingest") and p.stem in _MOVIDOS):
        return _REPO / "harness" / p.name
    return _REPO / path
