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

def test_storage_path_patron_legacy_con_docid8():
    path = backfill.storage_path(
        "Argus Security", "Manual SG100 ENG.pdf", 2,
        "494e71be-aaaa-bbbb-cccc-ddddeeeeffff",
    )
    assert path == "argus_security/argus_security_Manual_SG100_ENG_494e71be_p002.jpg"
    # URL-safe sin encoding: quote() no cambia nada.
    from urllib.parse import quote

    assert quote(path) == path


def test_storage_path_conserva_guiones_y_puntos():
    assert (
        backfill.storage_path("Detnov", "CAD-150-MS.416_es", 30, "0037a1f2-x")
        == "detnov/detnov_CAD-150-MS.416_es_0037a1f2_p030.jpg"
    )


def test_storage_path_docid8_discrimina_revisiones_mismo_source():
    # Caso real S271b: HLSI-MN-103_RP1r-Supra_lr bajo DOS document_ids
    # (revisiones v04/v07 separadas en s107) — sin docid8 colisionaban.
    a = backfill.storage_path(
        "Notifier", "HLSI-MN-103_RP1r-Supra_lr", 1,
        "494e71be-0000-0000-0000-000000000000",
    )
    b = backfill.storage_path(
        "Notifier", "HLSI-MN-103_RP1r-Supra_lr", 1,
        "e98e05ff-0000-0000-0000-000000000000",
    )
    assert a != b
    assert "494e71be" in a and "e98e05ff" in b


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

def _make_pdf(path: Path, pages: int = 2, text: str = "página") -> str:
    import fitz

    doc = fitz.open()
    for number in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"{text} {number + 1}")
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
    assert row["storage_path"] == "detnov/detnov_mini_doc-rend_p001.jpg"
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
# Fix-collisions: saneador global (S271b)
# ---------------------------------------------------------------------------

def _coverage_json(tmp_path, docs):
    coverage = tmp_path / "coverage.json"
    coverage.write_text(
        json.dumps({"documents": docs}), encoding="utf-8"
    )
    return coverage


def test_fix_collisions_sanea_colision_dedupe_y_preserva_no_colisionados(tmp_path):
    render_dir = tmp_path / "renders"
    out_dir = render_dir / "t99-fix"
    out_dir.mkdir(parents=True)
    pdf_a = tmp_path / "rev_a.pdf"
    pdf_b = tmp_path / "rev_b.pdf"
    sha_a = _make_pdf(pdf_a, pages=1, text="revision v04")
    sha_b = _make_pdf(pdf_b, pages=1, text="revision v07")  # contenido distinto
    docs = [
        {
            "document_id": "494e71be-aaaa", "source_file": "supra",
            "manufacturer": "Notifier", "status": "located_sha_verified",
            "pdf_path": str(pdf_a), "pdf_sha256": sha_a, "renderable_pages": [1],
        },
        {
            "document_id": "e98e05ff-bbbb", "source_file": "supra",
            "manufacturer": "Notifier", "status": "located_sha_verified",
            "pdf_path": str(pdf_b), "pdf_sha256": sha_b, "renderable_pages": [1],
        },
    ]
    base = {
        "tramo": "t99-fix", "source_file": "supra", "manufacturer": "Notifier",
        "storage_bucket": backfill.STORAGE_BUCKET, "bytes": 3,
        "width": 1, "height": 1, "media_type": "image/jpeg", "page_index": 1,
    }
    # Colisión con el esquema VIEJO: mismo nombre para dos document_ids.
    row_a = {**base, "item_id": backfill.item_id_for("494e71be-aaaa", 1),
             "document_id": "494e71be-aaaa", "pdf_sha256": sha_a,
             "storage_path": "notifier/notifier_supra_p001.jpg",
             "local_file": "notifier_supra_p001.jpg", "asset_sha256": "a" * 64}
    row_b = {**base, "item_id": backfill.item_id_for("e98e05ff-bbbb", 1),
             "document_id": "e98e05ff-bbbb", "pdf_sha256": sha_b,
             "storage_path": "notifier/notifier_supra_p001.jpg",
             "local_file": "notifier_supra_p001.jpg", "asset_sha256": "b" * 64}
    # Item sano no colisionado: conserva su nombre viejo.
    content_c = b"C-RENDER"
    row_c = {**base, "item_id": backfill.item_id_for("cccccccc-cccc", 1),
             "document_id": "cccccccc-cccc", "pdf_sha256": "c" * 64,
             "storage_path": "notifier/notifier_otro_p001.jpg",
             "local_file": "notifier_otro_p001.jpg",
             "asset_sha256": hashlib.sha256(content_c).hexdigest()}
    (out_dir / "notifier_supra_p001.jpg").write_bytes(b"PISADO")
    (out_dir / "notifier_otro_p001.jpg").write_bytes(content_c)
    manifest = backfill.manifest_path("t99-fix", render_dir)
    for row in (row_a, row_a, row_b, row_c):  # row_a duplicada (línea repetida)
        backfill.append_jsonl(manifest, row)

    status = backfill.fix_collisions(
        render_dir, _coverage_json(tmp_path, docs), tmp_path / "report.json"
    )
    assert status == 0
    rows = backfill.read_jsonl(manifest)
    assert len(rows) == 3  # dedupe: 1 fila por item
    by_id = {r["item_id"]: r for r in rows}
    fixed_a = by_id[row_a["item_id"]]
    fixed_b = by_id[row_b["item_id"]]
    # Esquema nuevo SOLO en los colisionados, con docid8 discriminando.
    assert fixed_a["storage_path"] == "notifier/notifier_supra_494e71be_p001.jpg"
    assert fixed_b["storage_path"] == "notifier/notifier_supra_e98e05ff_p001.jpg"
    assert fixed_a["asset_sha256"] != fixed_b["asset_sha256"]
    # sha por fila verificado contra el fichero en disco.
    for row in rows:
        local = out_dir / row["local_file"]
        assert hashlib.sha256(local.read_bytes()).hexdigest() == row["asset_sha256"]
    # El no colisionado queda intacto (nombre viejo, sin re-render).
    assert by_id[row_c["item_id"]]["storage_path"] == "notifier/notifier_otro_p001.jpg"
    assert "fixed_by" not in by_id[row_c["item_id"]]
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["collided_paths"] == 1
    assert report["tramos"]["t99-fix"]["items_fixed"] == 2
    assert report["tramos"]["t99-fix"]["duplicate_lines_removed"] == 1
    # Re-run = no-op (idempotente).
    status = backfill.fix_collisions(
        render_dir, _coverage_json(tmp_path, docs), tmp_path / "report2.json"
    )
    assert status == 0
    report2 = json.loads((tmp_path / "report2.json").read_text(encoding="utf-8"))
    assert report2["collided_paths"] == 0
    assert report2["tramos"] == {}


def test_fix_collisions_marca_reupload_solo_si_misma_ruta_con_sha_obsoleto(tmp_path):
    render_dir = tmp_path / "renders"
    out_dir = render_dir / "t99-mark"
    out_dir.mkdir(parents=True)
    pdf = tmp_path / "doc.pdf"
    sha_pdf = _make_pdf(pdf, pages=1)
    doc = {
        "document_id": "dddddddd-1111", "source_file": "doc",
        "manufacturer": "Detnov", "status": "located_sha_verified",
        "pdf_path": str(pdf), "pdf_sha256": sha_pdf, "renderable_pages": [1],
    }
    # Fila YA en esquema nuevo pero con fichero corrupto en disco y un receipt
    # verificado de esa MISMA ruta con el sha viejo → el objeto remoto es un
    # binario equivocado en la ruta que se conserva → marcar (x-upsert=true).
    new_path = backfill.storage_path("Detnov", "doc", 1, "dddddddd-1111")
    row = {
        "tramo": "t99-mark", "item_id": backfill.item_id_for("dddddddd-1111", 1),
        "document_id": "dddddddd-1111", "page_index": 1, "source_file": "doc",
        "manufacturer": "Detnov", "pdf_sha256": sha_pdf,
        "storage_bucket": backfill.STORAGE_BUCKET,
        "storage_path": new_path, "local_file": new_path.split("/")[1],
        "asset_sha256": "0" * 64, "bytes": 5, "width": 1, "height": 1,
        "media_type": "image/jpeg",
    }
    (out_dir / row["local_file"]).write_bytes(b"CORRUPTO")
    backfill.append_jsonl(backfill.manifest_path("t99-mark", render_dir), row)
    backfill.append_jsonl(
        backfill.upload_receipts_path("t99-mark", render_dir),
        {"item_id": row["item_id"], "storage_path": new_path,
         "asset_sha256": "0" * 64, "verified": True},
    )
    status = backfill.fix_collisions(
        render_dir, _coverage_json(tmp_path, [doc]), tmp_path / "report.json"
    )
    assert status == 0
    marked = backfill.read_jsonl(out_dir / "reupload_marked.jsonl")
    assert [m["item_id"] for m in marked] == [row["item_id"]]
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert len(report["reupload_marked"]) == 1
    assert report["orphaned_storage_objects"] == []


def test_receipt_is_current_exige_sha_y_ruta_vigentes():
    row = {"asset_sha256": "a" * 64, "storage_path": "x/y.jpg"}
    good = {"verified": True, "asset_sha256": "a" * 64, "storage_path": "x/y.jpg"}
    assert backfill.receipt_is_current(good, row)
    assert not backfill.receipt_is_current({**good, "asset_sha256": "b" * 64}, row)
    assert not backfill.receipt_is_current({**good, "storage_path": "x/z.jpg"}, row)
    assert not backfill.receipt_is_current({**good, "verified": False}, row)
    assert not backfill.receipt_is_current(good, None)


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


def test_gate_sample_excluye_tramos_para_el_gate_del_resto(tmp_path, monkeypatch):
    labels_path = tmp_path / "labels.jsonl"
    monkeypatch.setattr(backfill, "LABELS_PATH", labels_path)
    for n in range(5):
        backfill.append_jsonl(labels_path, {**_label(n), "tramo": "t00-piloto"})
    for n in range(5, 10):
        backfill.append_jsonl(labels_path, {**_label(n), "tramo": "t02-detnov"})
    out = tmp_path / "gate_resto.json"
    status = backfill.gate_sample(
        None,
        render_dir=tmp_path,
        exclude_tramos=("t00-piloto",),
        out_path=out,
    )
    assert status == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["excluded_tramos"] == ["t00-piloto"]
    assert payload["serving_set_total"] == 5  # solo el serving-set no-piloto
    assert len(payload["rows"]) == 5
    assert all(row["tramo"] == "t02-detnov" for row in payload["rows"])
