"""s311/L2b — el registro de flags ES un invariante, no un doc (blueprint §4-L2b).

El escáner canónico vive en `tests/_censo_flags.py` (v5) y lo comparten este test y el
generador del registro — cero deriva entre ambos. Contratos, con su alcance HONESTO:
  · COMPLETITUD NOMINAL v5 (Sol s311 cazó 3 huecos del v4: comillas simples
    [deep_lookup], PROFILE_OWNED_FLAGS en bucle dinámico, y flags data-driven de los
    YAML de fabricantes): nombres Y METADATA (lectores por flag) — la deriva de
    metadata pasaba verde en v4 (CHUNKS_TABLE sin deep_lookup en lectores).
  · DIVERGENCIAS DECLARADAS == reales (solo defaults de LECTORES DE CÓDIGO; los
    placeholders mecánicos de yaml/loop no cuentan).
  · PIN DE DEMO_FLAGS por AST (sin importar factlevel: su import fija env — dos bugs
    de contaminación cazados; el AST elimina la clase entera).
  · SNAPSHOT sin secretos, heurística por PARTES ampliada (Sol: fail-open con
    DSN/PASSWORD…) — sigue siendo heurística y así se declara.
"""
from __future__ import annotations

import ast
from pathlib import Path

from src.flags import REGISTRO, snapshot
from tests._censo_flags import escanear, divergencias

REPO = Path(__file__).resolve().parent.parent


def test_completitud_nominal_nombres_y_metadata():
    censo = escanear()
    reales = set(censo)
    registradas = set(REGISTRO)
    assert reales - registradas == set(), (
        f"flags leídas en src/ SIN registrar: {sorted(reales - registradas)}"
    )
    assert registradas - reales == set(), (
        f"entradas sin lector vivo: {sorted(registradas - reales)}"
    )
    # metadata: los LECTORES por flag también se pinnan (v4 dejaba pasar la deriva)
    for nombre, e in censo.items():
        assert set(REGISTRO[nombre]["lectores"]) == e["lectores"], (
            f"{nombre}: lectores del registro {sorted(REGISTRO[nombre]['lectores'])} ≠ "
            f"reales {sorted(e['lectores'])} — regenera con el censo v5"
        )


def test_divergencias_de_defaults_declaradas_y_exactas():
    reales = divergencias(escanear())
    declaradas = {n for n, spec in REGISTRO.items() if "divergencia" in spec}
    assert reales == declaradas, (
        f"divergencias reales {sorted(reales)} ≠ declaradas {sorted(declaradas)} — "
        f"una divergencia NUEVA se DECLARA en su entrada (visible), no se corrige a ciegas"
    )
    # s323 fase C: + SUPABASE_URL/SUPABASE_SERVICE_KEY — el gate de identidad las
    # exige con os.environ[...] mientras config.py usa default "". Divergencia
    # DELIBERADA: sin credenciales el gate no puede evaluar, y "no he podido
    # comprobar" NO es "todo bien" (critico del duo r34). El pin detecta, no corrige.
    assert declaradas == {"ANTHROPIC_API_KEY", "IDENTITY_RESOLVE_POLICY",
                          "SUPABASE_URL", "SUPABASE_SERVICE_KEY"}


def test_pin_de_demo_flags_sin_fantasmas_nuevos():
    """DEMO_FLAGS se extrae por AST — importar factlevel fija env en import-time y
    contaminó la suite dos veces (s69 y el propio subproceso). El literal es la fuente.
    `DIVERSIFY_TIEBREAK` es el fantasma CONOCIDO: lever s97/s101 NO-GO cuyo código
    nunca se mergeó; se declara, no se borra (identidad de la config del assessment)."""
    arbol = ast.parse((REPO / "scripts" / "factlevel_assessment.py")
                      .read_text(encoding="utf-8"))
    demo = None
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", "") == "DEMO_FLAGS":
            demo = ast.literal_eval(nodo.value)
    assert isinstance(demo, dict) and demo, "DEMO_FLAGS no encontrado como literal"

    fantasmas = set(demo) - set(REGISTRO)
    assert fantasmas == {"DIVERSIFY_TIEBREAK"}, (
        f"pins fantasma nuevos en DEMO_FLAGS: {sorted(fantasmas - {'DIVERSIFY_TIEBREAK'})}"
    )


def test_profile_owned_y_yaml_cubiertos():
    """Las dos vías dinámicas que el v4 no veía (crítico de Sol) quedan pineadas por su
    FUENTE, no por regex: el constante y los YAML."""
    from src.release_profiles import PROFILE_OWNED_FLAGS
    assert set(PROFILE_OWNED_FLAGS) <= set(REGISTRO)

    import re
    for y in (REPO / "config" / "manufacturers").glob("*.yaml"):
        for m in re.finditer(r"^\s*flag:\s*([A-Z_0-9]+)\s*$",
                             y.read_text(encoding="utf-8"), re.M):
            assert m.group(1) in REGISTRO, (
                f"flag data-driven {m.group(1)} ({y.name}) sin registrar — "
                f"series_registry la leerá con os.getenv y el censo debe verla"
            )


def test_snapshot_jamas_expone_secretos(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-super-secreto")
    monkeypatch.setenv("RERANK_TOP_K", "10")
    s = snapshot()
    assert s["ANTHROPIC_API_KEY"] == "(presente)"
    assert "sk-super-secreto" not in str(s)
    assert s["RERANK_TOP_K"] == "10"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert snapshot()["ANTHROPIC_API_KEY"] == "(ausente)"


def test_todas_las_sensibles_estan_marcadas():
    """Heurística por PARTES del nombre, AMPLIADA tras Sol s311 (era fail-open a
    DSN/PASSWORD/…). Sigue siendo heurística — nombres sin ninguna pieza credencial
    (p.ej. un futuro `ADMIN_CONTACT`) no los ve; la frontera real es la revisión de
    la entrada nueva, y este test al menos hace imposible el descuido típico."""
    piezas = {"KEY", "TOKEN", "SECRET", "JWT", "URL", "DSN", "PASSWORD", "PASS",
              "PWD", "CREDENTIAL", "CREDENTIALS", "AUTH"}
    sospechosos = {n for n in REGISTRO if piezas & set(n.split("_"))}
    # MP_DISTINCTIVE_TOKEN: token DE EVIDENCIA del contrato must-preserve, no credencial
    sin_marcar = {n for n in sospechosos
                  if not REGISTRO[n].get("sensible")} - {"MP_DISTINCTIVE_TOKEN"}
    assert sin_marcar == set(), (
        f"nombres con pinta de credencial sin marca sensible: {sorted(sin_marcar)}"
    )
