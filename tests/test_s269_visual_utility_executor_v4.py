"""Ejecutor v4 (full-bridge): preflight 0-red, checkpoint resumible y muestra del gate."""

import json

import httpx
import openai

import scripts.s269_visual_utility_executor_v4 as v4


def _forbid_network(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("cliente de red construido durante el preflight")

    monkeypatch.setattr(httpx, "Client", _boom)
    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    monkeypatch.setattr(openai, "OpenAI", _boom)


def test_preflight_cero_llamadas_full_bridge(monkeypatch):
    _forbid_network(monkeypatch)
    plan = v4.preflight()

    assert plan["items_total"] == 5096
    assert plan["batch_size"] == 10
    assert plan["model"] == "gpt-5.6-luna"
    assert plan["max_retries"] == 0
    assert plan["paid_calls_made"] == 0
    # Sin labels v4 aun: todo pendiente, 510 batches.
    assert plan["items_pending"] == 5096 - plan["items_done"]
    if plan["items_done"] == 0:
        assert plan["batches_pending"] == 510
    estimate = plan["estimate"]
    # Por-item MEDIDO en v3 ($0.05445/80) -> full bridge ~$3.47, bajo el stop-line.
    assert estimate["basis"] == "v3_labels_measured"
    assert 3.0 < estimate["full_bridge_cost_usd"] < 4.0
    assert estimate["full_bridge_cost_usd"] < estimate["budget_stop_usd"] == 5.0
    gate = plan["gate_sample"]
    assert gate["n"] == 60 and gate["seed"] == "269"
    assert gate["excluded_v3_pages"] == 80


def test_checkpoint_resume_tolera_linea_truncada(tmp_path):
    labels = tmp_path / "labels.jsonl"
    rows = [
        {"item_id": "s269v4_0001", "technical_utility": "useful"},
        {"item_id": "s269v4_0002", "technical_utility": "not_useful"},
        {"item_id": "s269v4_0001", "technical_utility": "not_useful"},  # re-etiquetado
    ]
    text = "\n".join(json.dumps(row) for row in rows)
    labels.write_text(text + '\n{"item_id": "s269v4_0003", "trunc', encoding="utf-8")

    done = v4.done_item_ids(labels)
    # La linea truncada (crash mid-append) se ignora -> ese item se re-etiqueta.
    assert done == {"s269v4_0001", "s269v4_0002"}
    # Dedupe conserva la ULTIMA aparicion (universo sin duplicados).
    by_id = {row["item_id"]: row for row in v4.read_label_lines(labels)}
    assert len(by_id) == 2
    assert by_id["s269v4_0001"]["technical_utility"] == "not_useful"


def test_gate_sample_determinista_serving_set_y_exclusion_v3(monkeypatch):
    # Universo sintetico: solo useful∧rol-servible entra; excluidos los de v3.
    v3_pages = v4.v3_cohort_pages()
    excluded_doc, excluded_page = sorted(v3_pages)[0]
    labels = []
    for index in range(200):
        labels.append(
            {
                "item_id": f"x{index:03d}",
                "document_id": f"doc-{index:03d}",
                "page_index": 7,
                "technical_utility": "useful" if index % 2 == 0 else "not_useful",
                "visual_role": ["wiring", "cover", "table", "product_photo"][index % 4],
            }
        )
    # candidato en pagina v3: debe quedar fuera aunque sea useful+wiring
    labels.append(
        {
            "item_id": "x_v3",
            "document_id": excluded_doc,
            "page_index": excluded_page,
            "technical_utility": "useful",
            "visual_role": "wiring",
        }
    )
    sample = v4.gate_sample_rows(labels)
    # Serving-set sintetico: pares con rol wiring (i%4==0) o table (i%4==2) =
    # 100 candidatos -> se toman exactamente 60 (cap del gate).
    assert len(sample) == 60
    assert all(
        row["technical_utility"] == "useful"
        and row["visual_role"] in {"wiring", "table"}
        for row in sample
    )
    assert all(row["item_id"] != "x_v3" for row in sample)
    # Determinismo: misma seleccion y mismo orden en una segunda pasada.
    assert v4.gate_sample_rows(labels) == sample
