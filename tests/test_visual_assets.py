"""S269 — registro de activos visuales (flag VISUAL_ASSETS_REGISTRY, default off).

Contrato verificado aquí:
    * flag off  → no-op EXACTO: cero llamadas al registro, `diagrams` intacto;
    * flag on   → lookup SOLO de las páginas de fragmentos citados en la respuesta;
    * cap 4 activos por respuesta (S271; antes 2), con orden de relevancia
      pre-declarado: páginas de los fragmentos MÁS citados primero; empate →
      orden de cita en la respuesta;
    * 'uncertain'/'not_useful' JAMÁS se sirven (ni aunque la API los devuelva);
    * falla abierta: excepción en el lookup → respuesta intacta, sin diagramas.
"""

from types import SimpleNamespace

import src.rag.generator as gen
import src.rag.visual_assets as va


# ---------------------------------------------------------------------------
# Helpers (mismo patrón de fake-Anthropic que test_generator_stop_reason.py)
# ---------------------------------------------------------------------------

class _FakeMessages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text=self._text)],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )


def _fake_anthropic(monkeypatch, text):
    fake = _FakeMessages(text)
    monkeypatch.setattr(
        gen.anthropic, "Anthropic",
        lambda api_key=None: SimpleNamespace(messages=fake),
    )
    return fake


def _chunk(doc_id, page, source_file, similarity=0.9):
    return {
        "content": "Texto del manual con el dato 42 V.",
        "similarity": similarity,
        "product_model": "CAD-250",
        "section_title": "Especificaciones",
        "content_type": "specification",
        "source_file": source_file,
        "document_id": doc_id,
        "page_number": page,
    }


def _spy_lookup(monkeypatch, assets_by_page):
    calls = []

    def fake_lookup(document_id, page_number):
        calls.append((document_id, page_number))
        return list(assets_by_page.get((document_id, page_number), []))

    monkeypatch.setattr(va, "lookup_visual_assets", fake_lookup)
    return calls


def _useful(url, role="wiring"):
    return {
        "storage_url": url,
        "technical_utility": "useful",
        "visual_role": role,
        "asset_scope": "page_render",
        "page_label": None,
    }


# ---------------------------------------------------------------------------
# Flag OFF (default): no-op absoluto
# ---------------------------------------------------------------------------

def test_flag_off_por_default_y_cero_llamadas(monkeypatch):
    assert gen.VISUAL_ASSETS_REGISTRY is False  # default off (_strict_on_off)
    _fake_anthropic(monkeypatch, "Respuesta técnica [F1].\nFuentes: manual_cad250 (rev. 1)")
    calls = _spy_lookup(
        monkeypatch, {("d1", 4): [_useful("https://assets/p4.jpg")]}
    )
    res = gen.generate_answer(
        "¿Tensión del lazo?", [_chunk("d1", 4, "manual_cad250.pdf")]
    )
    assert res["diagrams"] == []
    assert calls == []  # ni una llamada al registro con el flag off


# ---------------------------------------------------------------------------
# Flag ON: solo páginas citadas, formato telegram, cap 4 + orden de relevancia
# ---------------------------------------------------------------------------

def test_flag_on_lookup_solo_de_paginas_citadas(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    # La respuesta cita SOLO [F1]; el fragmento 2 (otra página) no se consulta.
    _fake_anthropic(monkeypatch, "Dato X [F1].\nFuentes: manual_cad250 (rev. 1)")
    calls = _spy_lookup(
        monkeypatch,
        {
            ("d1", 4): [_useful("https://assets/p4.jpg")],
            ("d2", 9): [_useful("https://assets/p9.jpg")],
        },
    )
    res = gen.generate_answer(
        "¿Tensión del lazo?",
        [_chunk("d1", 4, "manual_cad250.pdf"), _chunk("d2", 9, "otro_manual.pdf")],
    )
    assert calls == [("d1", 4)]
    assert len(res["diagrams"]) == 1
    diagram = res["diagrams"][0]
    assert diagram["url"] == "https://assets/p4.jpg"
    # Leyenda del transporte: manual + página (formato telegram_bot.py).
    assert diagram["product"] == "manual_cad250"
    assert diagram["section"] == "pág. 4"
    assert diagram["content_type"] == "wiring"


def test_flag_on_fallback_linea_fuentes_sin_refs_f(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    # Sin [F#]: el mecanismo de citas obligatorio es la línea "Fuentes: manual".
    _fake_anthropic(monkeypatch, "El dato es 42 V.\nFuentes: manual_cad250 (rev. 1)")
    calls = _spy_lookup(monkeypatch, {("d1", 4): [_useful("https://assets/p4.jpg")]})
    res = gen.generate_answer(
        "¿Tensión del lazo?", [_chunk("d1", 4, "manual_cad250.pdf")]
    )
    assert calls == [("d1", 4)]
    assert [d["url"] for d in res["diagrams"]] == ["https://assets/p4.jpg"]


def test_flag_on_sin_citas_no_hay_lookup(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    _fake_anthropic(monkeypatch, "No tengo ese dato en los fragmentos recuperados.")
    calls = _spy_lookup(monkeypatch, {("d1", 4): [_useful("https://assets/p4.jpg")]})
    res = gen.generate_answer(
        "¿Tensión del lazo?", [_chunk("d1", 4, "manual_cad250.pdf")]
    )
    assert calls == []
    assert res["diagrams"] == []


def test_cap_maximo_cuatro_activos(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    _fake_anthropic(
        monkeypatch, "Dato [F1] y [F2] y [F3].\nFuentes: a; b; c"
    )
    calls = _spy_lookup(
        monkeypatch,
        {
            ("d1", 1): [_useful("https://assets/a1.jpg"), _useful("https://assets/a2.jpg")],
            ("d2", 2): [_useful("https://assets/b1.jpg"), _useful("https://assets/b2.jpg")],
            ("d3", 3): [_useful("https://assets/c1.jpg")],
        },
    )
    res = gen.generate_answer(
        "¿Especificaciones?",
        [
            _chunk("d1", 1, "manual_a.pdf"),
            _chunk("d2", 2, "manual_b.pdf"),
            _chunk("d3", 3, "manual_c.pdf"),
        ],
    )
    assert len(res["diagrams"]) == 4  # cap S271 (antes 2, contrato S190)
    assert [d["url"] for d in res["diagrams"]] == [
        "https://assets/a1.jpg",
        "https://assets/a2.jpg",
        "https://assets/b1.jpg",
        "https://assets/b2.jpg",
    ]
    # Tras llenar el cap con las dos primeras páginas citadas no se siguen
    # consultando páginas (la 3ª ni se mira).
    assert calls == [("d1", 1), ("d2", 2)]


def test_orden_relevancia_mas_citado_primero(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    # F2 se cita DOS veces; F1 una → la página de F2 va primero aunque F1
    # aparezca antes en la respuesta.
    _fake_anthropic(
        monkeypatch, "Dato A [F1]. Dato B [F2]. Más detalle [F2].\nFuentes: a; b"
    )
    calls = _spy_lookup(
        monkeypatch,
        {
            ("d1", 1): [_useful("https://assets/a1.jpg")],
            ("d2", 2): [_useful("https://assets/b1.jpg")],
        },
    )
    res = gen.generate_answer(
        "¿Especificaciones?",
        [_chunk("d1", 1, "manual_a.pdf"), _chunk("d2", 2, "manual_b.pdf")],
    )
    assert calls == [("d2", 2), ("d1", 1)]
    assert [d["url"] for d in res["diagrams"]] == [
        "https://assets/b1.jpg",
        "https://assets/a1.jpg",
    ]


def test_orden_relevancia_empate_por_orden_de_cita(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    # Empate (una cita cada uno) → orden de cita en la respuesta: F2 antes que F1.
    _fake_anthropic(monkeypatch, "Dato B [F2]. Dato A [F1].\nFuentes: a; b")
    calls = _spy_lookup(
        monkeypatch,
        {
            ("d1", 1): [_useful("https://assets/a1.jpg")],
            ("d2", 2): [_useful("https://assets/b1.jpg")],
        },
    )
    res = gen.generate_answer(
        "¿Especificaciones?",
        [_chunk("d1", 1, "manual_a.pdf"), _chunk("d2", 2, "manual_b.pdf")],
    )
    assert calls == [("d2", 2), ("d1", 1)]
    assert [d["url"] for d in res["diagrams"]] == [
        "https://assets/b1.jpg",
        "https://assets/a1.jpg",
    ]


def test_orden_relevancia_agrega_citas_por_pagina(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    # F1 y F3 comparten página (d1, 1): 1+1 citas > 1 cita de F2 → la página
    # compartida gana aunque F2 esté citado antes que F3.
    _fake_anthropic(monkeypatch, "A [F2]. B [F1]. C [F3].\nFuentes: a; b")
    calls = _spy_lookup(
        monkeypatch,
        {
            ("d1", 1): [_useful("https://assets/a1.jpg")],
            ("d2", 2): [_useful("https://assets/b1.jpg")],
        },
    )
    res = gen.generate_answer(
        "¿Especificaciones?",
        [
            _chunk("d1", 1, "manual_a.pdf"),
            _chunk("d2", 2, "manual_b.pdf"),
            _chunk("d1", 1, "manual_a.pdf"),
        ],
    )
    assert calls == [("d1", 1), ("d2", 2)]
    assert [d["url"] for d in res["diagrams"]] == [
        "https://assets/a1.jpg",
        "https://assets/b1.jpg",
    ]


# ---------------------------------------------------------------------------
# uncertain / not_useful jamás servidos
# ---------------------------------------------------------------------------

def test_lookup_filtra_useful_en_query_y_en_cliente(monkeypatch):
    captured = {}

    class _FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            # La API devuelve (indebidamente) mezcla de utilidades Y roles: el
            # cliente debe re-filtrar y servir SOLO useful ∧ rol técnico.
            return [
                {"storage_url": "https://a/useful.jpg", "technical_utility": "useful", "visual_role": "wiring"},
                {"storage_url": "https://a/uncertain.jpg", "technical_utility": "uncertain", "visual_role": "wiring"},
                {"storage_url": "https://a/notuseful.jpg", "technical_utility": "not_useful", "visual_role": "table"},
                {"storage_url": "https://a/cover-useful.jpg", "technical_utility": "useful", "visual_role": "cover"},
                {"storage_url": "https://a/photo-useful.jpg", "technical_utility": "useful", "visual_role": "product_photo"},
                {"storage_url": "https://a/sinlabel.jpg"},
            ]

    class _FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None, params=None):
            captured["url"] = url
            captured["params"] = params
            return _FakeResponse()

    monkeypatch.setattr(va.httpx, "Client", _FakeClient)
    rows = va.lookup_visual_assets("doc-1", 7)
    # El filtro duro va en la QUERY (la DB solo devuelve useful ∧ rol técnico
    # en producción — regla de vocab del contrato S190)...
    assert captured["params"]["technical_utility"] == "eq.useful"
    assert captured["params"]["visual_role"] == "in.(wiring,table,procedure,ui)"
    assert captured["params"]["document_id"] == "eq.doc-1"
    assert captured["params"]["page_index"] == "eq.7"
    # ...y el cliente re-verifica (cinturón y tirantes): fuera uncertain,
    # not_useful, cover-useful, product_photo-useful y sin-label.
    assert [row["storage_url"] for row in rows] == ["https://a/useful.jpg"]


def test_uncertain_not_useful_jamas_llegan_a_diagrams(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    _fake_anthropic(monkeypatch, "Dato [F1].\nFuentes: manual_cad250")
    # lookup_visual_assets ya filtra en query y en cliente; aquí simulamos un
    # lookup roto que devuelve filas no-useful: append_cited_visual_assets
    # debe descartarlas igualmente (re-verificación final del contrato).
    def bad_lookup(document_id, page_number):
        return [
            {"storage_url": "https://a/uncertain.jpg", "technical_utility": "uncertain", "visual_role": "wiring"},
            {"storage_url": "https://a/notuseful.jpg", "technical_utility": "not_useful", "visual_role": "table"},
        ]

    monkeypatch.setattr(va, "lookup_visual_assets", bad_lookup)
    res = gen.generate_answer(
        "¿Tensión?", [_chunk("d1", 4, "manual_cad250.pdf")]
    )
    assert res["diagrams"] == []


def test_roles_no_tecnicos_jamas_llegan_a_diagrams(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    _fake_anthropic(monkeypatch, "Dato [F1].\nFuentes: manual_cad250")

    # Lookup roto que devuelve useful con rol NO servible (cover/marketing/
    # product_photo/other): append debe descartarlos (regla S190 §visual_role).
    def bad_lookup(document_id, page_number):
        return [
            {"storage_url": "https://a/cover.jpg", "technical_utility": "useful", "visual_role": "cover"},
            {"storage_url": "https://a/mkt.jpg", "technical_utility": "useful", "visual_role": "marketing"},
            {"storage_url": "https://a/photo.jpg", "technical_utility": "useful", "visual_role": "product_photo"},
            {"storage_url": "https://a/other.jpg", "technical_utility": "useful", "visual_role": "other"},
        ]

    monkeypatch.setattr(va, "lookup_visual_assets", bad_lookup)
    res = gen.generate_answer(
        "¿Tensión?", [_chunk("d1", 4, "manual_cad250.pdf")]
    )
    assert res["diagrams"] == []


# ---------------------------------------------------------------------------
# Falla abierta
# ---------------------------------------------------------------------------

def test_fail_open_excepcion_en_lookup(monkeypatch):
    monkeypatch.setattr(gen, "VISUAL_ASSETS_REGISTRY", True)
    _fake_anthropic(monkeypatch, "Dato [F1].\nFuentes: manual_cad250")

    def boom(document_id, page_number):
        raise RuntimeError("registry down")

    monkeypatch.setattr(va, "lookup_visual_assets", boom)
    res = gen.generate_answer(
        "¿Tensión del lazo?", [_chunk("d1", 4, "manual_cad250.pdf")]
    )
    assert res["answer"].startswith("Dato")
    assert res["diagrams"] == []
    assert res["stop_reason"] == "end_turn"


# ---------------------------------------------------------------------------
# Unidad: extracción de citas
# ---------------------------------------------------------------------------

def test_cited_fragment_numbers_refs_y_fallback():
    chunks = [
        _chunk("d1", 1, "manual_alpha.pdf"),
        _chunk("d2", 2, "manual_beta.pdf"),
    ]
    # Refs [F#] (fuera de rango se ignora).
    assert va.cited_fragment_numbers("x [F2] y [F9]", chunks) == [2]
    # Fallback por nombre de manual en la línea de fuentes.
    assert va.cited_fragment_numbers(
        "El dato es 42 V.\nFuentes: manual_beta (rev. 3)", chunks
    ) == [2]
    # Sin cita → vacío (no se adjunta nada).
    assert va.cited_fragment_numbers("Sin fuentes aquí.", chunks) == []


def test_cited_fragments_ranked_citas_y_posiciones():
    chunks = [
        _chunk("d1", 1, "manual_alpha.pdf"),
        _chunk("d2", 2, "manual_beta.pdf"),
    ]
    # F2 citado 2 veces (posición primera=2), F1 una (posición=10).
    ranked = va.cited_fragments_ranked("x [F2] y [F1] z [F2]", chunks)
    assert [(n, c) for n, c, _ in ranked] == [(2, 2), (1, 1)]
    # Fallback fuentes: cada manual cuenta 1; orden por aparición en el texto.
    ranked = va.cited_fragments_ranked(
        "Dato.\nFuentes: manual_beta; manual_alpha", chunks
    )
    assert [(n, c) for n, c, _ in ranked] == [(2, 1), (1, 1)]
