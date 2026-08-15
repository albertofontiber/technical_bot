"""s321 — La sonda de alcanzabilidad no puede volver a emitir un NEGATIVO sin prueba de entrega.

Nace del fallo que corrige DEC-173(b): el «NO alcanzable» de `hp017#2` se publicó desde un
recibo que **ni inyectaba ni registraba admisión** — medía el efecto de un guard y se le importó
la etiqueta. Ese negativo cerró la etapa 3 como cola de ingeniería durante meses (DEC-175(b)).

Lo que este fichero ancla:
  1. la prueba de entrega es DISTINTA por modo (y exigir ids en `appendix` sería un falso
     positivo que bloquearía todo NO legítimo de esa rama — dúo s321);
  2. en `serve` no basta «algún carrier admitido»: hay que probar que entraron TODOS;
  3. sin prueba de entrega el veredicto emitible es INCONCLUYENTE, nunca NO;
  4. y un NO legítimo (entrega probada, nada transmitido) SIGUE siendo emitible — el guard no
     puede tragarse el resultado que la sonda existe para producir.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# El guard se importa del módulo LIGERO: sin esto el test se cae en CI por falta de entorno
# (KeyError SUPABASE_URL, PR #263) y un guard que no corre en CI no guarda nada.
from scripts import reachability_verdict as PROBE  # noqa: E402

SERVE = {"mode": "serve", "inject": ["aaaaaaaa", "bbbbbbbb"]}
APPENDIX = {"mode": "appendix", "inject": [], "span_grep": "x"}


def _rep(n, oracle_yes, **kw):
    return {"rep": n, "base_yes": 0, "oracle_yes": oracle_yes, **kw}


# ── 1 · serve: hay que probar que entraron TODOS los carriers ────────────────────────────────
def test_serve_exige_todos_los_carriers_no_solo_alguno():
    """«No vacío» no basta: con 2 requeridos y 1 admitido, el hecho puede vivir en el que faltó.
    Es exactamente el fallo que la regla-C de DEC-173 ya había cazado una vez (oráculo
    INCOMPLETO en hp011#2: se inyectó la mitad del label)."""
    completo = PROBE.prueba_de_entrega(
        SERVE, {"oracle_ids_admitidos": ["aaaaaaaa-1111", "bbbbbbbb-2222"]})
    assert completo["ok"] is True and completo["faltan"] == []

    parcial = PROBE.prueba_de_entrega(SERVE, {"oracle_ids_admitidos": ["aaaaaaaa-1111"]})
    assert parcial["ok"] is False
    assert parcial["faltan"] == ["bbbbbbbb"]

    vacio = PROBE.prueba_de_entrega(SERVE, {"oracle_ids_admitidos": []})
    assert vacio["ok"] is False


def test_serve_no_cuenta_duplicados_como_carriers_distintos():
    """El recibo de `hp011#2` listaba 3 entradas admitidas con solo 2 carriers únicos, y mi
    prosa dijo «3 portadores» (dúo s321, Fable). El mismo id dos veces no cubre al que falta."""
    dup = PROBE.prueba_de_entrega(
        SERVE, {"oracle_ids_admitidos": ["aaaaaaaa-1111", "aaaaaaaa-9999"]})
    assert dup["ok"] is False and dup["faltan"] == ["bbbbbbbb"]
    assert dup["admitidos_unicos"] == 1


# ── 2 · appendix: la prueba es el SPAN, no los ids (falso positivo cazado por el dúo) ─────────
def test_appendix_no_exige_ids_y_se_declara_tautologica():
    """Dos cosas a la vez: (a) no exigir ids —si no, un NO legítimo vía appendix sería
    inemitible—; y (b) NO fingir que mide la presencia. `oracle_answer` se fabrica concatenando
    ese mismo span, así que `span in respuesta` no puede ser False en una corrida real: el guard
    sería vacuo. Se declara `estructural_tautologica` (2ª ronda del dúo s321, Fable)."""
    ok = PROBE.prueba_de_entrega(
        APPENDIX, {"span": "Es fundamental borrar la regla 1",
                   "oracle_answer": "…texto… Es fundamental borrar la regla 1 …más texto…"})
    assert ok["ok"] is True
    assert ok["tipo"] == "estructural_tautologica"
    assert "NO acredita" in ok["aviso"], "debe declarar que no prueba COBERTURA"

    vacio = PROBE.prueba_de_entrega(APPENDIX, {"span": "", "oracle_answer": "lo que sea"})
    assert vacio["ok"] is False, "un span vacío sí es un fallo de entrega real"


# ── 2b · ENTREGA ≠ COBERTURA, y el negativo exige las dos ────────────────────────────────────
def test_entrega_probada_sin_cobertura_atestada_no_puede_emitir_no():
    """El fallo que la entrega NO cubre: un oráculo incompleto (media etiqueta) se entrega
    perfectamente y produce un NO falso — es la regla-C de DEC-173 sobre `hp011#2`, donde se
    inyectó solo el chunk del label. Probar que LLEGÓ no prueba que CONTENGA el hecho."""
    reps = [_rep(i, 0, prueba_entrega={"ok": True}) for i in range(3)]
    assert PROBE.veredicto_de(reps, firm=4, cobertura_ok=False)["veredicto"] ==         "INCONCLUYENTE_SIN_COBERTURA_ATESTADA"
    assert PROBE.veredicto_de(reps, firm=4, cobertura_ok=True)["veredicto"] == "NO_ALCANZABLE"


def test_cero_reps_no_puede_emitir_un_negativo():
    """El guard que existe para impedir negativos sin evidencia emitía uno sin NINGUNA:
    `reps=0` es aceptable por CLI y `veredicto_de([])` devolvía NO_ALCANZABLE (dúo s321)."""
    v = PROBE.veredicto_de([], firm=4, cobertura_ok=True)
    assert v["veredicto"] == "INCONCLUYENTE_SIN_REPS"


# ── 3 · el fail-closed del NEGATIVO ──────────────────────────────────────────────────────────
def test_sin_prueba_de_entrega_no_se_puede_emitir_no_alcanzable():
    """El caso `hp017#2`: nada transmitido, pero tampoco se probó que se entregara nada.
    El veredicto honesto es INCONCLUYENTE — no «el modelo no puede»."""
    reps = [_rep(i, 0, prueba_entrega={"ok": False, "motivo": "sin inyección"}) for i in range(3)]
    v = PROBE.veredicto_de(reps, firm=4)
    assert v["veredicto"] == "INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA"
    assert v["alcanzable"] is False
    assert v["reps_sin_prueba_de_entrega"] == [0, 1, 2]


def test_una_sola_rep_sin_entrega_ya_bloquea_el_negativo():
    reps = [_rep(0, 0, prueba_entrega={"ok": True}),
            _rep(1, 0, prueba_entrega={"ok": True}),
            _rep(2, 0, prueba_entrega={"ok": False, "motivo": "carrier no admitido"})]
    assert PROBE.veredicto_de(reps, firm=4)["veredicto"] == "INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA"


def test_el_guard_NO_bloquea_un_negativo_legitimo():
    """Anti-falso-positivo: con entrega probada en todas y nada transmitido, el NO es el
    resultado real de la sonda y debe poder emitirse. Un guard que se traga el resultado que el
    instrumento existe para producir es peor que el fallo que corrige."""
    reps = [_rep(i, 0, prueba_entrega={"ok": True}) for i in range(3)]
    v = PROBE.veredicto_de(reps, firm=4, cobertura_ok=True)
    assert v["veredicto"] == "NO_ALCANZABLE"
    assert v["oracle_firme"] == 0


def test_alcanzable_se_emite_aunque_alguna_rep_no_pruebe_entrega():
    """Asimetría deliberada: una rep firme demuestra la capacidad por sí sola. El fail-closed
    protege el NEGATIVO, que es el que cierra líneas de trabajo."""
    reps = [_rep(0, 5, prueba_entrega={"ok": True}),
            _rep(1, 0, prueba_entrega={"ok": False, "motivo": "carrier no admitido"})]
    v = PROBE.veredicto_de(reps, firm=4)
    assert v["veredicto"] == "ALCANZABLE" and v["alcanzable"] is True


# ── 4 · el sellado que evita que un veredicto envejezca en silencio ──────────────────────────
def test_el_sello_mejora_git_sha_pero_declara_lo_que_NO_cubre():
    # `importorskip` NO sirve aquí: la sonda no falla con ImportError sino con KeyError al
    # leer el entorno (PR #263). Se captura cualquier fallo de construcción y se salta.
    try:
        import scripts.s293_reachability_probe as sonda
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"la sonda necesita entorno para construirse ({type(e).__name__}); "
                    "el guard de veredicto sí corre siempre, vive en reachability_verdict")
    """Sellar solo `git_sha` permitió que un «NO alcanzable» del 2-ago se citara en agosto como
    vigente. Esto lo mejora — pero NO es el freeze-contract completo y el docstring lo dice: sin
    huella de corpus, una mutación in-place es invisible. Llamarlo «completo» era framing por
    encima de la realidad (dúo s321, ambos revisores)."""
    assert "NO es completo" in (sonda.sello_freeze.__doc__ or ""),         "el sello no debe auto-declararse completo"
    sello = sonda.sello_freeze()
    for clave in ("git_sha", "CHUNKS_TABLE", "RETRIEVAL_TOP_K", "RERANK_TOP_K",
                  "RERANKER_BACKEND", "LLM_MODEL", "juez", "INSTRUMENT_VERSION"):
        assert clave in sello, f"el sello no cubre {clave}"
    assert {"model", "K", "THRESH_FIRM"} <= set(sello["juez"])
