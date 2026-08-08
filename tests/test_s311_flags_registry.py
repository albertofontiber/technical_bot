"""s311/L2b — el registro de flags ES un invariante, no un doc (blueprint §4-L2b).

Contratos, con su alcance HONESTO (declarado en el dúo del blueprint):
  · COMPLETITUD NOMINAL: cada call-site TEXTUAL de lectura de entorno en `src/`
    (getenv directo/indirecto, environ[.get], `_strict_on_off` en ambas firmas,
    `_mp_flag`) está registrado — un `getenv` nuevo sin registrar = suite ROJA.
    NO garantiza equivalencia semántica de parsing entre lectores no migrados.
  · DIVERGENCIAS DECLARADAS: si dos lectores usan defaults distintos para la misma
    flag, la divergencia vive VISIBLE en el registro — y este test exige que el
    conjunto declarado coincida con la realidad re-escaneada (una divergencia nueva
    pone esto rojo con instrucciones, no se corrige a ciegas).
  · PIN DE DEMO_FLAGS por NOMBRE: pins fantasma (el harness pina, nadie lee) quedan
    declarados — hoy exactamente uno, con su historia.
  · SNAPSHOT SIN SECRETOS: las flags `sensible` reportan presencia, jamás valor.
"""
from __future__ import annotations

import re
from pathlib import Path

from src.flags import REGISTRO, snapshot

REPO = Path(__file__).resolve().parent.parent


def _escanear() -> dict[str, set[str]]:
    """Los MISMOS patrones del generador del registro (censo v4, s311)."""
    encontrados: dict[str, set[str]] = {}

    def add(nombre, default):
        encontrados.setdefault(nombre, set()).add(default)

    for f in (REPO / "src").rglob("*.py"):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r'os\.getenv\(\s*"([A-Z_0-9]+)"\s*(?:,\s*([^)]+?))?\s*\)', t):
            add(m.group(1), (m.group(2) or "None").strip())
        for m in re.finditer(r'os\.environ\.get\(\s*"([A-Z_0-9]+)"', t):
            add(m.group(1), "None")
        for m in re.finditer(r'os\.environ\[\s*"([A-Z_0-9]+)"\s*\]', t):
            add(m.group(1), "(REQUERIDA)")
        for m in re.finditer(r'_strict_on_off\(\s*"([A-Z_0-9]+)"', t):
            d = re.search(rf'_strict_on_off\(\s*"{m.group(1)}"\s*,\s*"(\w+)"', t)
            add(m.group(1), f'"{d.group(1)}"' if d else '"off"')
        for m in re.finditer(r'_mp_flag\(\s*"([A-Z_0-9]+)"', t):
            add(m.group(1), '"off"')
        for c in re.finditer(r'^(\w+)\s*=\s*"([A-Z_0-9]+)"\s*$', t, re.M):
            if re.search(rf'os\.getenv\(\s*{c.group(1)}\b', t):
                add(c.group(2), "None")
            if re.search(rf'\.get\(\s*{c.group(1)}\b', t):
                # env.get(CONST, ...) con el entorno como mapping — release_profiles
                add(c.group(2), "None")
    return encontrados


def test_completitud_nominal_del_registro():
    """Toda lectura textual registrada; todo lo registrado existe. El mensaje del
    fallo ES la instrucción: registrar la flag nueva o retirar la entrada muerta."""
    reales = set(_escanear())
    registradas = set(REGISTRO)
    assert reales - registradas == set(), (
        f"flags leídas en src/ SIN registrar en src/flags.py: "
        f"{sorted(reales - registradas)} — añade su entrada (censo v3)"
    )
    assert registradas - reales == set(), (
        f"entradas del registro sin lector vivo en src/: "
        f"{sorted(registradas - reales)} — retíralas (o el lector cambió de patrón)"
    )


def test_divergencias_de_defaults_declaradas_y_exactas():
    reales = {n for n, ds in _escanear().items() if len(ds) > 1}
    declaradas = {n for n, spec in REGISTRO.items() if "divergencia" in spec}
    assert reales == declaradas, (
        f"divergencias reales {sorted(reales)} ≠ declaradas {sorted(declaradas)} — "
        f"una divergencia NUEVA se DECLARA en su entrada del registro (visible), "
        f"no se corrige a ciegas (regla L2b)"
    )
    # y las dos de hoy son las conocidas, ambas con lados falsy (adjudicación pendiente)
    assert declaradas == {"ANTHROPIC_API_KEY", "IDENTITY_RESOLVE_POLICY"}


def test_pin_de_demo_flags_sin_fantasmas_nuevos():
    """El pin del harness contra el registro, por NOMBRE. `DIVERSIFY_TIEBREAK` es el
    fantasma CONOCIDO: lever s97/s101 NO-GO cuyo código nunca se mergeó — el harness
    pina una flag que ningún lector de src/ consume. Se declara, no se borra (tocar
    DEMO_FLAGS cambia la identidad de la config del assessment sin necesidad)."""
    # En SUBPROCESO a propósito: importar factlevel_assessment FIJA los DEMO_FLAGS en
    # os.environ en import-time (línea ~139) — hacerlo aquí envenenaría a todos los
    # tests posteriores del proceso (cazado: 5 tests de s69 rotos por el prompt-variant
    # pineado). El aislamiento es bidireccional: ni su entorno ni el nuestro se tocan.
    import json as _json
    import subprocess
    import sys

    salida = subprocess.run(
        [sys.executable, "-c",
         "import sys, json; sys.path.insert(0, '.'); "
         "from scripts.factlevel_assessment import DEMO_FLAGS; "
         "print(json.dumps(sorted(DEMO_FLAGS)))"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert salida.returncode == 0, salida.stderr
    demo_flags = _json.loads(salida.stdout.strip().splitlines()[-1])

    fantasmas = set(demo_flags) - set(REGISTRO)
    assert fantasmas == {"DIVERSIFY_TIEBREAK"}, (
        f"pins fantasma nuevos en DEMO_FLAGS: {sorted(fantasmas - {'DIVERSIFY_TIEBREAK'})} "
        f"— ¿flag pineada sin lector? regístrala o justifícala aquí"
    )


def test_snapshot_jamas_expone_secretos(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-super-secreto")
    monkeypatch.setenv("RERANK_TOP_K", "10")
    s = snapshot()
    assert s["ANTHROPIC_API_KEY"] == "(presente)"
    assert "sk-super-secreto" not in str(s)
    assert s["RERANK_TOP_K"] == "10"                    # lo no-sensible sí se ve
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert snapshot()["ANTHROPIC_API_KEY"] == "(ausente)"


def test_todas_las_sensibles_estan_marcadas():
    """Ningún nombre con pinta de credencial sin `sensible: True` — el snapshot es
    la única superficie nueva y no puede filtrar por omisión de marca."""
    # por PARTES del nombre, no substring: KEYWORD≠KEY, TOKENS(límite)≠TOKEN
    piezas_credencial = {"KEY", "TOKEN", "SECRET", "JWT", "URL"}
    sospechosos = {n for n in REGISTRO
                   if piezas_credencial & set(n.split("_"))}
    # excepción DECLARADA: MP_DISTINCTIVE_TOKEN es un token DE EVIDENCIA del contrato
    # must-preserve (una palabra del manual), no una credencial.
    sin_marcar = {n for n in sospechosos
                  if not REGISTRO[n].get("sensible")} - {"MP_DISTINCTIVE_TOKEN"}
    assert sin_marcar == set(), (
        f"nombres con pinta de credencial sin marca sensible: {sorted(sin_marcar)}"
    )
