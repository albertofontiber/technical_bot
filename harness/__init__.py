"""harness/ — la isla de instrumentos de eval/gates, FUERA de `src/` (L2a, s310).

Estos módulos solo los importan `scripts/` y `tests/` (censo s300, contrato L0). El
producto NO puede importarlos: la regla de raíces prohibidas del contrato de imports
(`src/` no importa `harness.*`) nació cerrada ANTES de que este paquete existiera.

Quedan 2 módulos de la isla ANCLADOS en `src/rag/` (`visual_gold`,
`omission_correction`): el probe sellado s270 los importa function-local y el gate C1
rechaza rutas fuera de `scripts/`|`src/` — se mudarán si el probe se re-sella o el
gate se retira (trigger declarado en el blueprint §4-L2a).

── EL PUENTE DE IMPORTS, y por qué existe ─────────────────────────────────────────
Los 33 módulos movidos son RENAMES BYTE-PUROS a propósito: un ecosistema de permisos
y preregs congelados (s114/s115/s117/s210…) pina `sha256` de sus bytes — «version,
don't relax» (DEC-147) exige que esos sellos sigan VERIFICANDO, así que su contenido
no se toca NI para actualizar imports internos. La consecuencia: sus imports
absolutos (`src.rag.X`) y relativos (`from .chunk import`) apuntan a rutas que ya no
existen o resuelven al paquete equivocado. Este finder los redirige BAJO DEMANDA:

  · `src.rag.<m>` / `src.reingest.<m>`  → `harness.<m>`   (para los 33 movidos)
  · `harness.chunk`                     → `src.reingest.chunk`  (único destino
    relativo externo, escaneado — `chunk` es producto y se queda en src/)

Solo se redirigen esos nombres exactos: ninguno existe ya en su lado origen, así que
no hay sombra posible sobre producto. `importlib` está prohibido en `src/` por el
contrato; `harness/` está fuera y este uso ES el mecanismo del paquete.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from pathlib import Path

_REINGEST = {"chunk_provenance", "extraction_derivation", "retrieval_policy",
             "superscript_overlay"}
_MOVIDOS = {p.stem for p in Path(__file__).parent.glob("*.py")} - {"__init__"}


class _PuenteIsla(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Redirige los nombres del puente cargando el módulo REAL y registrando el alias."""

    def _destino(self, fullname: str) -> str | None:
        partes = fullname.split(".")
        if (len(partes) == 3 and partes[0] == "src"
                and partes[1] in ("rag", "reingest") and partes[2] in _MOVIDOS):
            pkg = "reingest" if partes[2] in _REINGEST else "rag"
            if partes[1] != pkg:
                return None                      # src.rag.chunk_provenance NO existe
            return f"harness.{partes[2]}"
        if fullname == "harness.chunk":
            return "src.reingest.chunk"
        return None

    def find_spec(self, fullname, path=None, target=None):
        if self._destino(fullname) is None:
            return None
        return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        real = importlib.import_module(self._destino(spec.name))
        sys.modules[spec.name] = real            # alias directo al módulo real
        return real

    def exec_module(self, module):               # ya ejecutado por el import real
        return None


if not any(isinstance(f, _PuenteIsla) for f in sys.meta_path):
    sys.meta_path.insert(0, _PuenteIsla())
