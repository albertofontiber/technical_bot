# -*- coding: utf-8 -*-
"""s315/#68 — fase de canales derivados por lote: contratos verificables sin claves.

Lo que se fija aquí:
  · `parse_questions(jsonl_path)` aplica los MISMOS criterios pineados del dúo s101
    a un jsonl por-lote (keep-FIRST por chunk, cap 4, dedup global, len>=15,
    exclusión MIE-MI-310) — la paridad de criterios es la razón de parametrizar en
    vez de duplicar;
  · los pins de modelo anti-drift: hyq del lote NO hereda LLM_MODEL (hoy Opus 5) —
    genera con el vintage del corpus (sonnet-4-6); enunciados con el GO de DEC-102
    (haiku h1);
  · los dos drivers nuevos exponen su CLI (smoke --help, sin tocar red ni DB).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _jsonl(tmp_path, registros):
    p = tmp_path / "lote.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in registros),
                 encoding="utf-8")
    return p


def test_parse_questions_por_lote_aplica_criterios_pineados(tmp_path):
    from s101_hyq_embed import parse_questions

    q_larga = "¿Cómo se configura el retardo de la sirena en la central?"
    registros = [
        {"chunk_id": "c1", "source_file": "doc_a.pdf",
         "questions": [q_larga, "corta", q_larga + " (bis)",
                       "¿Qué tensión usa el lazo A?", "¿Qué tensión usa el lazo B?",
                       "¿Qué tensión usa el lazo C?"]},
        # registro DUPLICADO del mismo chunk → se descarta ENTERO (keep-FIRST)
        {"chunk_id": "c1", "source_file": "doc_a.pdf", "questions": ["¿Otra?"]},
        # dedup GLOBAL normalizado: misma pregunta en otro chunk NO entra
        {"chunk_id": "c2", "source_file": "doc_b.pdf",
         "questions": [q_larga.upper()]},
        # exclusión pineada
        {"chunk_id": "c3", "source_file": "MIE-MI-310_manual.pdf",
         "questions": ["¿Pregunta del doc excluido con longitud sobrada?"]},
    ]
    questions, chunk_ids, srcs, st = parse_questions(_jsonl(tmp_path, registros))
    # c1: cap 4/chunk sobre las >=15 chars y deduplicadas → 4 exactas, sin "corta"
    assert len([c for c in chunk_ids if c == "c1"]) == 4
    assert "corta" not in questions
    # c2: su única pregunta era dup normalizado de c1 → fuera
    assert "c2" not in chunk_ids
    # c3: doc excluido
    assert "c3" not in chunk_ids
    assert st["excl_mi310"] >= 1


def test_parse_questions_sin_argumento_sigue_leyendo_el_global():
    """El default es byte-idéntico: sin path lee el jsonl global s99 (HYQ)."""
    import inspect

    from s101_hyq_embed import parse_questions

    sig = inspect.signature(parse_questions)
    assert list(sig.parameters) == ["jsonl_path"]
    assert sig.parameters["jsonl_path"].default is None


def test_pins_de_modelo_anti_drift():
    import derive_channels_lote as drv
    import hyq_lote_pipeline as hyq

    # hyq del lote = vintage del corpus (run s102), NUNCA el LLM_MODEL vivo del bot
    assert hyq.HYQ_GEN_MODEL == "claude-sonnet-4-6"
    # enunciados = el GO de G0 (DEC-102)
    assert drv.ENUN_MODEL.startswith("claude-haiku-4-5")


def test_clis_exponen_contrato(tmp_path):
    for script, esperados in (
        ("scripts/derive_channels_lote.py", ["--since", "--docs-file", "--tag",
                                             "--data-root", "--aplicar", "--solo"]),
        ("scripts/hyq_lote_pipeline.py", ["--docs", "--tag", "--model",
                                          "--aplicar", "--fase"]),
        ("scripts/enunciados_pass.py", ["--store", "--docs", "--tranche",
                                        "--vintage", "--budget-usd"]),
    ):
        out = subprocess.run([sys.executable, script, "--help"], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, f"{script} --help falló: {out.stderr[:200]}"
        for flag in esperados:
            assert flag in out.stdout, f"{script}: falta {flag} en --help"
