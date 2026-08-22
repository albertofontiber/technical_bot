"""El packet es un fichero GENERADO sobre el que Alberto ANOTA.

Regenerarlo sin conservar sus marcas y sus correcciones de dominio las destruye
—y eso es conocimiento que el catálogo no tiene: «este también sirve para el
MAD-401», «hay uno más actual en la web, pon éste superseded»—. La v1 del lector
perdió 10 de 11 notas y 4 de 8 casillas por dos fallos que estos tests fijan:

  · la nota va en la ÚLTIMA celda de la fila y él NO cierra la fila con `|`,
    así que es `celdas[-1]`, no `celdas[-2]`;
  · dos manuales pueden compartir nombre TRUNCADO (las filas 16 y 17 son las dos
    `55347200 …MAD-472 ES `), así que un dict pisa la nota de la primera;
  · «tocada» no es sólo `[X]`: también escribir en el hueco sin marcar nada.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "s337", RAIZ / "scripts/s337_packet_revision_alberto.py")
s337 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s337)

PACKET = """# Revisión

### 1.1 — `unresolved:id50` → `notifier:id-50`  ·  **12 manual(es)**

  - [X] OK  ·  [ ] otra cosa: ______

### 1.2 — `unresolved:tg` → `notifier:tg`  ·  **2 manual(es)**

  - [ ] OK  ·  [ ] otra cosa: OK a lo que propone, pero es software

### 1.5 — `unresolved:x` → `notifier:x`  ·  **1 manual(es)**

  - [ ] OK  ·  [ ] otra cosa: ______

| # | manual | producto | evidencia |
|---|---|---|---|
| 16 | `55347200 Manual Sirena` | MAD-472 | FICHERO | Alberto: sirve para el MAD-473
| 17 | `55347200 Manual Sirena` | MAD-472 | FICHERO | Alberto: ver fila 16.
"""


@pytest.fixture()
def leido(tmp_path: Path):
    f = tmp_path / "packet.md"
    f.write_text(PACKET, "utf-8")
    return s337.anotaciones_previas(f)


def test_conserva_la_casilla_marcada(leido):
    por_seccion, _ = leido
    clave = "1.1 — `unresolved:id50` → `notifier:id-50`  ·  **12 manual(es)**"
    assert "[X]" in por_seccion[clave]


def test_conserva_el_texto_escrito_aunque_no_marque_casilla(leido):
    """El fallo real: Alberto escribió «OK a lo que propone» SIN marcar `[X]`,
    y la v1 lo tiraba por exigir la marca."""
    por_seccion, _ = leido
    clave = "1.2 — `unresolved:tg` → `notifier:tg`  ·  **2 manual(es)**"
    assert "OK a lo que propone" in por_seccion[clave]


def test_no_conserva_lo_que_no_tocó(leido):
    """Control negativo: una decisión intacta NO debe conservarse, o el packet
    dejaría de reflejar cambios de la propia generación."""
    por_seccion, _ = leido
    assert not any(k.startswith("1.5 ") for k in por_seccion)


def test_dos_filas_con_el_mismo_nombre_truncado_conservan_LAS_DOS(leido):
    """Las filas 16 y 17 comparten clave; con un dict, la segunda pisaba la
    nota larga de la primera."""
    _, por_manual = leido
    notas = por_manual["55347200 Manual Sirena"]
    assert len(notas) == 2
    assert "MAD-473" in notas[0]
    assert "ver fila 16" in notas[1]


def test_la_nota_es_la_ultima_celda_no_la_penultima(leido):
    """La v1 se traía «FICHERO» —la celda de evidencia— y tiraba la nota."""
    _, por_manual = leido
    assert all(not n.startswith("FICHERO") for n in por_manual["55347200 Manual Sirena"])
