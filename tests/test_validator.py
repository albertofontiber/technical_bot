"""Tests for src/rag/validator.py — cross-model grounding auditor.

The validator is invoked post-generation by Opus to detect unsupported
factual claims in Sonnet's answer. This file covers:

1. `warrants_validation()` heuristic: when to spend the Opus call.
2. `audit_grounding()` shape + error handling (mocked API).
3. `build_retry_feedback()` output format.

The generator's decision tree (pass / retry / fallback) is covered in
`test_generator_validator_integration` via mocks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.validator import (  # noqa: E402
    audit_grounding,
    build_retry_feedback,
    warrants_validation,
)


# ---------------------------------------------------------------------------
# warrants_validation heuristic
# ---------------------------------------------------------------------------

def test_warrants_skips_short_answer():
    assert warrants_validation("Sí, el LED parpadea en verde.") is False


def test_warrants_skips_pure_admit():
    answer = (
        "No tengo información sobre ese fabricante en mi base de datos. "
        "Consulta directamente la documentación técnica del fabricante."
    )
    assert warrants_validation(answer) is False


def test_warrants_validates_answer_with_multiple_numerics():
    answer = (
        "Para la instalación del lazo convencional de la central ZXe: "
        "utiliza cable apantallado 2×1,5 mm², con una longitud máxima de 1200 m "
        "desde la central hasta el último dispositivo del bucle. "
        "La impedancia total del lazo no debe superar los 40 Ω, "
        "y la tensión de alimentación nominal es 24 VDC estabilizados. "
        "El consumo de corriente en reposo es 80 mA por lazo, "
        "y en condición de alarma general puede subir hasta 250 mA. "
        "Fuente: Manual técnico ZXe, sección 3.4."
    )
    assert len(answer) >= 200
    assert warrants_validation(answer) is True


def test_warrants_validates_answer_with_many_citations():
    answer = (
        "La central admite configuración local mediante el teclado frontal [F1]. "
        "Se accede al menú principal pulsando la tecla de menú durante tres segundos [F2]. "
        "Desde ahí se pueden programar los dispositivos del lazo [F3]. "
        "Los parámetros se guardan automáticamente al salir. "
        "Fuente: Manual técnico."
    )
    assert len(answer) >= 200
    assert warrants_validation(answer) is True


def test_warrants_validates_long_answer_without_units():
    # Long procedural answer with no numerics — still worth validating because
    # invented section names / product names slip through other heuristics.
    long_answer = (
        "Para configurar la central correctamente, sigue estos pasos en orden: "
        "primero accede al modo instalador desde el menú principal usando la clave técnica. "
        "Después selecciona el submenú de programación de zonas y subzonas asociadas. "
        "A continuación define el nombre lógico de cada zona y su descripción textual. "
        "Verifica que el tipo de dispositivo asociado coincide con el instalado físicamente. "
        "Guarda los cambios antes de salir del submenú para que queden registrados. "
        "Comprueba que el modo normal se restablece sin fallos ni avisos residuales en pantalla. "
        "Si aparece un fallo, revisa cuidadosamente el cableado del lazo correspondiente. "
        "Consulta la sección de diagnósticos avanzados para interpretar códigos de error. "
        "Finaliza el procedimiento con una prueba de alarma real en varios dispositivos para validar. "
        "Revisa el log de eventos para confirmar que todo se ha registrado correctamente. "
        "Fuente: Manual técnico de instalación y programación."
    )
    assert len(long_answer) > 800
    assert warrants_validation(long_answer) is True


def test_warrants_skips_short_answer_with_one_number():
    # Borderline — one number, short answer → skip.
    answer = "La tensión nominal es 24 VDC. Fuente: Manual."
    assert warrants_validation(answer) is False


# ---------------------------------------------------------------------------
# audit_grounding shape + error handling
# ---------------------------------------------------------------------------

def _mock_opus_response(text: str) -> MagicMock:
    """Build a mock anthropic.Anthropic().messages.create() response."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    return response


def test_audit_returns_empty_when_no_chunks():
    result = audit_grounding("¿qué hace X?", [], "Some answer with 24 VDC values.")
    assert result == {"unsupported": []}


def test_audit_parses_clean_verdict():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_opus_response(
        '{"unsupported": []}'
    )
    with patch("src.rag.validator.anthropic.Anthropic", return_value=mock_client):
        result = audit_grounding(
            "¿tensión de la ZXe?",
            [{"product_model": "ZXe", "content": "La ZXe opera a 24 VDC nominales."}],
            "La tensión es 24 VDC. Fuente: ZXe.",
        )
    assert result == {"unsupported": []}


def test_audit_parses_contaminated_verdict():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_opus_response(
        json.dumps({
            "unsupported": [
                {"claim": "cable 1.5 km", "reason": "valor no aparece en fragmentos"},
                {"claim": "UNE-EN 12845", "reason": "norma no mencionada"},
            ]
        })
    )
    with patch("src.rag.validator.anthropic.Anthropic", return_value=mock_client):
        result = audit_grounding(
            "longitud máxima cable",
            [{"product_model": "ZXe", "content": "La ZXe es un panel de control."}],
            "Admite hasta 1.5 km según UNE-EN 12845.",
        )
    assert len(result["unsupported"]) == 2
    assert result["unsupported"][0]["claim"] == "cable 1.5 km"


def test_audit_extracts_json_from_wrapped_output():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_opus_response(
        'Voy a auditar...\n```json\n{"unsupported": []}\n```\nEso es todo.'
    )
    with patch("src.rag.validator.anthropic.Anthropic", return_value=mock_client):
        result = audit_grounding(
            "q", [{"content": "chunk"}], "answer with 24 VDC 40 Ω 1200 m values",
        )
    assert result == {"unsupported": []}


def test_audit_handles_malformed_json():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_opus_response(
        "sorry, I can't answer that"
    )
    with patch("src.rag.validator.anthropic.Anthropic", return_value=mock_client):
        result = audit_grounding(
            "q", [{"content": "chunk"}], "answer",
        )
    assert result["unsupported"] == []
    assert "error" in result


def test_audit_handles_api_exception():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("connection reset")
    with patch("src.rag.validator.anthropic.Anthropic", return_value=mock_client):
        result = audit_grounding(
            "q", [{"content": "chunk"}], "answer",
        )
    assert result["unsupported"] == []
    assert "error" in result


def test_audit_filters_malformed_entries():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_opus_response(
        json.dumps({
            "unsupported": [
                {"claim": "valid claim", "reason": "reason"},
                {"reason": "missing claim field"},  # dropped
                "string entry",  # dropped
                {"claim": "another valid", "reason": "r"},
            ]
        })
    )
    with patch("src.rag.validator.anthropic.Anthropic", return_value=mock_client):
        result = audit_grounding("q", [{"content": "c"}], "a")
    assert len(result["unsupported"]) == 2
    assert result["unsupported"][0]["claim"] == "valid claim"


# ---------------------------------------------------------------------------
# build_retry_feedback
# ---------------------------------------------------------------------------

def test_build_retry_feedback_empty():
    assert build_retry_feedback([]) == ""


def test_build_retry_feedback_lists_claims():
    feedback = build_retry_feedback([
        {"claim": "1.5 km cable", "reason": "no aparece"},
        {"claim": "240 zonas", "reason": "valor inventado"},
    ])
    assert "1.5 km cable" in feedback
    assert "240 zonas" in feedback
    assert "no aparece" in feedback
    assert "ELIMINANDO" in feedback or "eliminando" in feedback.lower()
