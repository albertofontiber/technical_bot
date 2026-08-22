"""El ledger dice citar a Alberto — que lo demuestre.

`s339_ledger_alberto.py` separa lo mecánico (lo que él escribió) de lo interpretado
(lo que yo entendí), y cada lectura mía lleva un campo `cita` con el fragmento del
que sale. Ese campo es la ÚNICA razón por la que la interpretación es auditable:
si una cita no está literalmente en el packet, el rastro es ficción y la lectura
deja de ser verificable — que es exactamente el fallo que el packet existe para
evitar (que «lo que Alberto dijo» y «lo que yo entendí» acaben siendo la misma celda).
"""
from __future__ import annotations

import importlib.util
import re
import unicodedata
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PACKET = RAIZ / "docs" / "REVISION_ALBERTO_HUERFANOS.md"


def _mod():
    spec = importlib.util.spec_from_file_location(
        "s339", RAIZ / "scripts" / "s339_ledger_alberto.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _norm(s: str) -> str:
    """Comparación tolerante a lo que NO cambia el sentido: acentos, mayúsculas,
    espacios y las comillas tipográficas que introduce el editor. Nada más — el
    contenido de la cita tiene que ser suyo."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')
    s = s.replace("’", "'").replace("`", "")
    return re.sub(r"\s+", " ", s).strip()


@pytest.fixture(scope="module")
def packet() -> str:
    if not PACKET.exists():
        pytest.skip("el packet no está en el árbol")
    return _norm(PACKET.read_text("utf-8"))


def _citas(mod):
    """Toda cita del ledger, con su ref, incluidas las de §7 y las del suelo."""
    for sec, lec in mod.LECTURA.items():
        if lec.get("cita"):
            yield f"§{sec}", lec["cita"]
        for pid, fila in (lec.get("filas") or {}).items():
            if fila.get("cita"):
                yield f"§{sec}:{pid}", fila["cita"]
    for man, lec in mod.LECTURA_SUELO.items():
        if lec.get("cita"):
            yield f"suelo:{man}", lec["cita"]


def test_toda_cita_es_literal_del_packet(packet):
    """Ninguna cita puede ser una paráfrasis mía: tiene que estar en el fichero.

    Se permite ELIDIR con «…» una anotación larga —él escribe párrafos y la cita
    recoge lo que decide—, pero cada tramo entre elipsis tiene que ser literal suyo.
    Elidir conserva la auditabilidad; reescribir la destruye, y eso incluye
    «arreglarle» las erratas: si él escribió «sfotware», la cita dice «sfotware».
    """
    fallos = []
    for ref, cita in _citas(_mod()):
        for tramo in re.split(r"…|\.\.\.", cita):
            if tramo.strip() and _norm(tramo) not in packet:
                fallos.append((ref, tramo.strip()))
    assert not fallos, "citas que NO aparecen literalmente en el packet:\n" + "\n".join(
        f"  {ref}: {cita!r}" for ref, cita in fallos)


def test_el_test_detecta_una_cita_inventada(packet):
    """Control negativo: si el test pasara con cualquier texto, no valdría nada."""
    assert _norm("Alberto: fusiona los dos y no preguntes") not in packet


def test_toda_seccion_decidida_tiene_lectura():
    """Una sección que él marcó y yo no leí es trabajo suyo tirado a la basura."""
    mod = _mod()
    est = mod.parsea(PACKET)
    sin = [s["seccion"] for s in est["secciones"]
           if s["casilla"] and s["seccion"] not in mod.LECTURA
           and not s["seccion"].startswith("3")]
    assert not sin, f"secciones con casilla tocada y sin lectura en el ledger: {sin}"


def test_toda_lectura_bloqueada_dice_por_que():
    """Un `listo: False` sin `bloqueo` es un pendiente sin causa: no se puede cerrar."""
    mod = _mod()
    mudos = [k for k, v in {**mod.LECTURA, **mod.LECTURA_SUELO}.items()
             if not v.get("listo") and not v.get("bloqueo")]
    assert not mudos, f"lecturas bloqueadas que no declaran el bloqueo: {mudos}"


def test_ninguna_lectura_apunta_a_un_id_sin_namespace():
    """Los ids llevan namespace de marca por contrato (`morley:zx2e`). Un id pelado
    en el ledger se convertiría en una fila mal formada al aplicarlo."""
    mod = _mod()
    malos = []
    for sec, lec in mod.LECTURA.items():
        for campo in ("de", "a", "gana", "redirige", "familia", "id"):
            v = lec.get(campo)
            if isinstance(v, str) and ":" not in v:
                malos.append(f"§{sec}.{campo}={v}")
        for campo in ("promover_tambien", "modelos", "modelos_nuevos", "ids"):
            for v in lec.get(campo) or []:
                if ":" not in v:
                    malos.append(f"§{sec}.{campo}={v}")
    assert not malos, f"ids sin namespace de marca: {malos}"
