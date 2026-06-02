"""Tests del eje NO-FABRICACIÓN + ramificación por estado-del-hecho (C1, DEC-012).

score_gold se testea con la LÓGICA pura: el check cross-model (undue_inference_check) NO se
llama aquí — se INYECTA su resultado (undue_inferences / inference_error), igual que producción
inyecta contradictions / factual_error. Así el test es determinista y no depende de la API.
Varios casos cruzados (error de un eje + FALLO del otro) los añadió el dúo adversarial (P3 r2).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import atomic_scorer as sc  # noqa: E402


def _gold(qid, conducta, facts):
    return {"qid": qid, "conducta_esperada": conducta, "atomic_facts": facts}


def test_refuse_inference_en_answer_like():
    # s41/DEC-012: refuse-inference deja de caer a REVISAR; colapsa a "answer" en el gate.
    assert "refuse-inference" in sc.ANSWER_LIKE


def test_ausente_probado_no_cuenta_en_completitud():
    # C1: un hecho ausente-probado (valor null) NO entra en el denominador de completitud.
    gold = _gold("t1", "answer", [
        {"tipo": "core", "estado": "presente", "texto": "tension de alimentacion 24V", "valor": "24"},
        {"tipo": "core", "estado": "ausente-probado", "texto": "no documenta el procedimiento X", "valor": None},
    ])
    res = sc.score_gold(gold, "El equipo se alimenta a 24V.", undue_inferences=[])
    assert res["core"] == "1/1", res["verdict"]
    assert res["verdict"].startswith("PASS"), res["verdict"]


def test_fabricacion_sobre_ausente_es_fallo():
    # El bot afirma compatibilidad sobre un hecho ausente-probado → FALLO (asimetría de seguridad).
    gold = _gold("t2", "refuse-inference", [
        {"tipo": "core", "estado": "ausente-probado",
         "texto": "no hay documentacion de compatibilidad cross-brand", "valor": None},
    ])
    res = sc.score_gold(gold, "Si, el detector A es compatible con la central B.",
                        undue_inferences=[{"hecho_ausente": "compatibilidad cross-brand",
                                           "afirmacion_bot": "es compatible", "tipo": "compatibilidad"}])
    assert res["verdict"].startswith("FALLO (fabricación"), res["verdict"]


def test_refuse_sin_fabricacion_pasa_por_completitud():
    # refuse-inference correcto: da los specs por-producto (completitud) + no fabrica la relación.
    gold = _gold("t3", "refuse-inference", [
        {"tipo": "core", "estado": "presente", "texto": "el detector A admite 24V", "valor": "24"},
        {"tipo": "core", "estado": "ausente-probado", "texto": "no hay doc de compatibilidad", "valor": None},
    ])
    res = sc.score_gold(gold, "El detector A admite 24V. No consta compatibilidad documentada; "
                              "consulte al fabricante.",
                        undue_inferences=[], inference_error=None)
    assert res["core"] == "1/1", res["verdict"]
    assert res["verdict"].startswith("PASS"), res["verdict"]


def test_admit_sin_fabricacion_pasa():
    # admit correcto: el corpus no cubre, el bot admite, no fabrica.
    gold = _gold("t4", "admit", [
        {"tipo": "core", "estado": "ausente-probado", "texto": "no consta el dato Y", "valor": None},
    ])
    res = sc.score_gold(gold, "El manual no especifica ese dato.", undue_inferences=[])
    assert res["verdict"].startswith("PASS"), res["verdict"]


def test_inference_error_va_a_revisar():
    # El eje no-fabricación no evaluable (y sin FALLO en el otro eje) → REVISAR, no auto-FALLO.
    gold = _gold("t5", "admit", [
        {"tipo": "core", "estado": "ausente-probado", "texto": "no consta Z", "valor": None},
    ])
    res = sc.score_gold(gold, "algo", inference_error="llamada LLM falló: timeout")
    assert res["verdict"].startswith("REVISAR"), res["verdict"]


def test_sin_eje_con_absente_degrada_pass_a_revisar():
    # fix P3 r2: sin el eje no-fabricación (undue=None, como sin --llm), un gold con ausente-probado
    # cuyo veredicto sería PASS se degrada a REVISAR (no se certifica PASS sin verificar fabricación).
    # La completitud sigue excluyendo el ausente-probado (C1).
    gold = _gold("t6", "answer", [
        {"tipo": "core", "estado": "presente", "texto": "tension 24V", "valor": "24"},
        {"tipo": "core", "estado": "ausente-probado", "texto": "no doc del procedimiento X", "valor": None},
    ])
    res = sc.score_gold(gold, "Usa 24V.")
    assert res["core"] == "1/1", res["verdict"]
    assert res["verdict"].startswith("REVISAR"), res["verdict"]
    assert "FALLO" not in res["verdict"], res["verdict"]  # no inventa un FALLO sin el eje


def test_sin_absente_sin_eje_no_degrada():
    # No-regresión: un gold SIN ausente-probado, sin --llm, conserva su PASS (no se degrada).
    gold = _gold("t6b", "answer", [
        {"tipo": "core", "estado": "presente", "texto": "tension 24V", "valor": "24"},
    ])
    res = sc.score_gold(gold, "Usa 24V.")
    assert res["verdict"].startswith("PASS"), res["verdict"]


def test_contradiccion_gana_a_error_de_inferencia():
    # Asimetría de seguridad (P3 r2): un FALLO factual NO se degrada a REVISAR porque el OTRO eje
    # diera error. Los hallazgos se evalúan antes que los errores.
    gold = _gold("x1", "answer", [
        {"tipo": "core", "estado": "presente", "texto": "tension 24V", "valor": "24"},
        {"tipo": "core", "estado": "ausente-probado", "texto": "no doc X", "valor": None},
    ])
    res = sc.score_gold(gold, "Usa 12V.",
                        contradictions=[{"hecho": "24V", "afirmacion_bot": "12V", "por_que": "valor distinto"}],
                        inference_error="timeout")
    assert res["verdict"].startswith("FALLO (alucinación"), res["verdict"]


def test_fabricacion_gana_a_error_factual():
    # Asimetría (P3 r2): un FALLO de fabricación NO se degrada porque el factual diera error.
    gold = _gold("x2", "refuse-inference", [
        {"tipo": "core", "estado": "ausente-probado", "texto": "no hay doc de compatibilidad", "valor": None},
    ])
    res = sc.score_gold(gold, "Son compatibles.",
                        factual_error="timeout",
                        undue_inferences=[{"hecho_ausente": "compat", "afirmacion_bot": "son compatibles",
                                           "tipo": "compatibilidad"}])
    assert res["verdict"].startswith("FALLO (fabricación"), res["verdict"]


def test_factual_tiene_prioridad_sobre_fabricacion():
    # Dos FALLOS a la vez: la contradicción factual se reporta primero (orden estable).
    gold = _gold("x4", "answer", [
        {"tipo": "core", "estado": "presente", "texto": "tension 24V", "valor": "24"},
        {"tipo": "core", "estado": "ausente-probado", "texto": "no doc X", "valor": None},
    ])
    res = sc.score_gold(gold, "Usa 12V.",
                        contradictions=[{"hecho": "24V", "afirmacion_bot": "12V", "por_que": "valor distinto"}],
                        undue_inferences=[{"hecho_ausente": "X", "afirmacion_bot": "...", "tipo": "valor"}])
    assert res["verdict"].startswith("FALLO (alucinación: contradice"), res["verdict"]


def test_ausente_probado_con_valor_no_null_no_cuenta_completitud():
    # Agujero latente (P3 r2): aunque el esquema permita valor no-null en un ausente-probado, C1 lo
    # excluye de completitud (se ramifica por ESTADO, no por valor). undue=[] → no se degrada.
    gold = _gold("x3", "answer", [
        {"tipo": "core", "estado": "presente", "texto": "tension 24V", "valor": "24"},
        {"tipo": "core", "estado": "ausente-probado", "texto": "no doc corriente reposo", "valor": "500"},
    ])
    res = sc.score_gold(gold, "Usa 24V.", undue_inferences=[])
    assert res["core"] == "1/1", res["verdict"]
