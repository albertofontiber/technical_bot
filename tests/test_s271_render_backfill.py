"""S271 — pipeline de render backfill por tramos (todo offline, sin red).

Contrato verificado aquí:
    * patrón de storage legacy: manual-images/{slug}/{slug}_{stem}_pNNN.jpg,
      slugs URL-safe sin encoding;
    * tramos deterministas: piloto = primeros docs hasta >=500 páginas con
      corte en frontera de documento; resto = un tramo por fabricante;
    * item_id estable (independiente de orden/resume);
    * render con BIND sha256 del PDF + checkpoint resumible (re-run = no-op);
    * upload/load sin --execute = preflight puro (0 escrituras);
    * classify preflight: cuenta pendientes + coste medido, 0 llamadas;
    * gate sample: determinista (seed 271), solo useful ∧ rol servible, n<=60.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "s271_render_backfill", ROOT / "scripts" / "s271_render_backfill.py"
)
backfill = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("s271_render_backfill", backfill)
_spec.loader.exec_module(backfill)


# ---------------------------------------------------------------------------
# Patrón de storage + ids
# ---------------------------------------------------------------------------

def test_storage_path_patron_legacy():
    path = backfill.storage_path("Argus Security", "Manual SG100 ENG.pdf", 2)
    assert path == "argus_security/argus_security_Manual_SG100_ENG_p002.jpg"
    # URL-safe sin encoding: quote() no cambia nada.
    from urllib.parse import quote

    assert quote(path) == path


def test_storage_path_conserva_guiones_y_puntos():
    assert (
        backfill.storage_path("Detnov", "CAD-150-MS.416_es", 30)
        == "detnov/detnov_CAD-150-MS.416_es_p030.jpg"
    )


def test_item_id_estable_y_unico_por_pagina():
    a = backfill.item_id_for("doc-1", 4)
    assert a == backfill.item_id_for("doc-1", 4)
    assert a != backfill.item_id_for("doc-1", 5)
    assert a.startswith("s271_")


# ---------------------------------------------------------------------------
# Tramos deterministas
# ---------------------------------------------------------------------------

def _doc(doc_id, manufacturer, source, pages):
    return {
        "document_id": doc_id,
        "manufacturer": manufacturer,
        "source_file": source,
        "pdf_path": "unused.pdf",
        "pdf_sha256": "0" * 64,
        "renderable_pages": list(range(1, pages + 1)),
    }


def test_build_tramos_piloto_500_con_corte_en_frontera_de_doc():
    docs = [
        _doc("d1", "Aritech", "a1", 300),
        _doc("d2", "Aritech", "a2", 150),
        _doc("d3", "Aritech", "a3", 100),  # cruza 500 → entra ENTERO y corta
        _doc("d4", "Aritech", "a4", 40),
        _doc("d5", "Detnov", "b1", 70),
    ]
    tramos = backfill.build_tramos(docs)
    pilot = tramos[backfill.PILOT_TRAMO_ID]
    assert [d["document_id"] for d in pilot] == ["d1", "d2", "d3"]
    assert backfill.tramo_pages(pilot) == 550  # >=500, sin partir documentos
    # Resto: un tramo por fabricante, en orden alfabético y numerados.
    assert list(tramos) == [backfill.PILOT_TRAMO_ID, "t01-aritech", "t02-detnov"]
    assert [d["document_id"] for d in tramos["t01-aritech"]] == ["d4"]
    assert [d["document_id"] for d in tramos["t02-detnov"]] == ["d5"]


def test_select_tramos_resto_excluye_piloto():
    tramos = backfill.build_tramos(
        [_doc("d1", "Aritech", "a", 600), _doc("d2", "Detnov", "b", 10)]
    )
    resto = backfill.select_tramos(tramos, "resto")
    assert backfill.PILOT_TRAMO_ID not in resto
    assert list(resto) == ["t01-detnov"]


# ---------------------------------------------------------------------------
# Render: BIND sha del PDF + checkpoint resumible
# ---------------------------------------------------------------------------

def _make_pdf(path: Path, pages: int = 2) -> str:
    import fitz

    doc = fitz.open()
    for number in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"página {number + 1}")
    doc.save(path)
    doc.close()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_render_tramo_manifest_y_resume(tmp_path):
    pdf = tmp_path / "mini.pdf"
    sha = _make_pdf(pdf, pages=2)
    doc = {
        "document_id": "doc-render",
        "manufacturer": "Detnov",
        "source_file": "mini",
        "pdf_path": str(pdf),
        "pdf_sha256": sha,
        "renderable_pages": [1, 2],
    }
    render_dir = tmp_path / "renders"
    stats = backfill.render_tramo("t99-test", [doc], render_dir)
    assert stats == {"rendered": 2, "resumed": 0, "failed_docs": 0}
    rows = backfill.read_jsonl(backfill.manifest_path("t99-test", render_dir))
    assert len(rows) == 2
    row = rows[0]
    assert row["storage_path"] == "detnov/detnov_mini_p001.jpg"
    local = backfill.tramo_dir("t99-test", render_dir) / row["local_file"]
    assert hashlib.sha256(local.read_bytes()).hexdigest() == row["asset_sha256"]
    assert row["media_type"] == "image/jpeg"
    assert row["render"] == {"dpi": 170, "jpeg_quality": 80}
    # Re-run = no-op (checkpoint resumible).
    stats = backfill.render_tramo("t99-test", [doc], render_dir)
    assert stats == {"rendered": 0, "resumed": 2, "failed_docs": 0}
    assert len(backfill.read_jsonl(backfill.manifest_path("t99-test", render_dir))) == 2


def test_render_tramo_aborta_doc_si_el_sha_del_pdf_cambio(tmp_path):
    pdf = tmp_path / "mini.pdf"
    _make_pdf(pdf)
    doc = {
        "document_id": "doc-x",
        "manufacturer": "Detnov",
        "source_file": "mini",
        "pdf_path": str(pdf),
        "pdf_sha256": "f" * 64,  # NO es el sha del PDF local
        "renderable_pages": [1],
    }
    stats = backfill.render_tramo("t99-sha", [doc], tmp_path / "renders")
    assert stats["failed_docs"] == 1
    assert stats["rendered"] == 0
    assert not backfill.manifest_path("t99-sha", tmp_path / "renders").exists()


# ---------------------------------------------------------------------------
# Upload / load: preflight puro sin --execute
# ---------------------------------------------------------------------------

def _seed_manifest_and_receipt(render_dir, tramo="t99-up", with_receipt=False):
    row = {
        "tramo": tramo,
        "item_id": backfill.item_id_for("doc-1", 1),
        "document_id": "doc-1",
        "page_index": 1,
        "source_file": "mini",
        "manufacturer": "Detnov",
        "pdf_sha256": "e" * 64,
        "storage_bucket": backfill.STORAGE_BUCKET,
        "storage_path": "detnov/detnov_mini_p001.jpg",
        "local_file": "detnov_mini_p001.jpg",
        "asset_sha256": "a" * 64,
        "bytes": 1000,
        "width": 100,
        "height": 141,
        "media_type": "image/jpeg",
    }
    backfill.append_jsonl(backfill.manifest_path(tramo, render_dir), row)
    if with_receipt:
        backfill.append_jsonl(
            backfill.upload_receipts_path(tramo, render_dir),
            {
                "item_id": row["item_id"],
                "document_id": "doc-1",
                "page_index": 1,
                "storage_path": row["storage_path"],
                "storage_url": "https://x/storage/v1/object/public/manual-images/"
                + row["storage_path"],
                "asset_sha256": "a" * 64,
                "verified": True,
            },
        )
    return row


def test_upload_preflight_no_escribe_nada(tmp_path, capsys):
    _seed_manifest_and_receipt(tmp_path)
    status = backfill.upload_tramo(
        "t99-up", execute=False, env_path=tmp_path / "no.env", render_dir=tmp_path
    )
    assert status == 0
    assert not backfill.upload_receipts_path("t99-up", tmp_path).exists()
    out = capsys.readouterr().out
    assert "1 pendientes" in out and "0 escrituras" in out


def test_load_preflight_solo_cuenta_subidas_verificadas(tmp_path, capsys):
    _seed_manifest_and_receipt(tmp_path, with_receipt=True)
    payloads = backfill._load_payloads("t99-up", tmp_path)
    assert len(payloads) == 1
    row = payloads[0]
    assert row["technical_utility"] == "uncertain"  # JAMÁS servible sin gate
    assert row["visual_role"] is None
    assert row["asset_sha256"] == "a" * 64  # sha REAL del binario
    assert row["source_extraction_sha256"] == "e" * 64
    status = backfill.load_tramo(
        "t99-up", execute=False, env_path=tmp_path / "no.env", render_dir=tmp_path
    )
    assert status == 0
    assert "0 escrituras" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Classify preflight: 0 llamadas, coste medido
# ---------------------------------------------------------------------------

def test_classify_preflight_cuenta_y_estima_sin_llamadas(tmp_path, monkeypatch):
    _seed_manifest_and_receipt(tmp_path, with_receipt=True)
    monkeypatch.setattr(backfill, "LABELS_PATH", tmp_path / "labels.jsonl")
    plan = backfill.classify_preflight(["t99-up"], tmp_path)
    assert plan["paid_calls_made"] == 0
    assert plan["items_total"] == 1
    assert plan["items_pending"] == 1
    assert plan["model"] == "gpt-5.6-luna"
    per_item = plan["estimate"]["per_item_usd"]
    assert plan["estimate"]["pending_cost_usd"] == round(per_item * 1, 3)
    assert plan["estimate"]["budget_stop_usd"] == 12.0
    # Con el item ya etiquetado, pending cae a 0 (resume por item_id).
    backfill.append_jsonl(
        tmp_path / "labels.jsonl",
        {"item_id": backfill.item_id_for("doc-1", 1)},
    )
    plan = backfill.classify_preflight(["t99-up"], tmp_path)
    assert plan["items_pending"] == 0


def test_measured_per_item_usa_recibos_v4_reales():
    per_item, basis = backfill.measured_per_item_usd()
    # Recibos v4 versionados en evals/: base medida, no el fallback.
    assert basis.startswith("v4_receipts_measured")
    assert 0.0001 < per_item < 0.01


# ---------------------------------------------------------------------------
# Gate sample: determinista, solo serving-set
# ---------------------------------------------------------------------------

def _label(n, utility="useful", role="wiring"):
    return {
        "item_id": f"it{n}",
        "document_id": f"d{n}",
        "page_index": n,
        "source_file": "m",
        "manufacturer": "Detnov",
        "technical_utility": utility,
        "visual_role": role,
        "confidence": "high",
        "reason": "r",
        "asset_sha256": "a" * 64,
    }


def test_gate_sample_rows_solo_servibles_y_determinista():
    labels = (
        [_label(n) for n in range(70)]
        + [_label(100, utility="uncertain")]
        + [_label(101, utility="not_useful")]
        + [_label(102, role="cover")]
        + [_label(103, role="marketing")]
    )
    sample = backfill.gate_sample_rows(labels)
    assert len(sample) == 60  # cap del gate
    assert all(
        l["technical_utility"] == "useful"
        and l["visual_role"] in backfill.SERVABLE_ROLES
        for l in sample
    )
    assert sample == backfill.gate_sample_rows(labels)  # seed 271 determinista
