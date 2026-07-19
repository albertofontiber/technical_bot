"""S271 — transporte de diagramas en Telegram: álbum vs fotos sueltas.

Contrato verificado aquí (decisión de Alberto, S271):
    * <=2 imágenes → fotos sueltas con caption descriptiva (comportamiento
      original, un ``reply_photo`` por diagrama);
    * >2 imágenes → UN solo ``reply_media_group`` (álbum) con caption SOLO en
      la primera ``InputMediaPhoto`` (Telegram la muestra bajo el álbum),
      listando todas las páginas adjuntas;
    * falla del álbum → fail-open: degradar a fotos sueltas (una URL mala no
      deja al técnico sin las demás).
"""

import asyncio
import types

import src.bot.telegram_bot as bot


class _Message:
    def __init__(self, media_group_error=None):
        self.replies = []
        self.photos = []
        self.media_groups = []
        self._media_group_error = media_group_error

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)

    async def reply_photo(self, photo, caption=None, **_kwargs):
        self.photos.append({"photo": photo, "caption": caption})

    async def reply_media_group(self, media, **_kwargs):
        if self._media_group_error is not None:
            raise self._media_group_error
        self.media_groups.append(media)


class _Update:
    def __init__(self, media_group_error=None):
        self.message = _Message(media_group_error)
        self.effective_user = types.SimpleNamespace(id=7)


def _diagram(n, content_type="wiring"):
    return {
        "url": f"https://assets/p{n}.jpg",
        "product": f"manual_{n}",
        "section": f"pág. {n}",
        "content_type": content_type,
    }


def _run_pipeline(monkeypatch, update, diagrams):
    served = [{"id": "served", "content": "evidencia", "similarity": 1.0}]
    monkeypatch.setattr(bot, "extract_product_models", lambda _q: ["CAD-250"])
    monkeypatch.setattr(bot, "retrieve_chunks", lambda *a, **k: served)
    monkeypatch.setattr(bot, "rerank", lambda *a, **k: served)
    monkeypatch.setattr(
        bot,
        "generate_answer",
        lambda *a, **k: {"answer": "respuesta", "diagrams": diagrams},
    )
    monkeypatch.setattr(bot, "log_query", lambda **_k: None)
    context = types.SimpleNamespace(user_data={})
    asyncio.run(bot._process_query(update, context, "¿Conexionado CAD-250?"))


# ---------------------------------------------------------------------------
# <=2 imágenes: fotos sueltas (sin álbum)
# ---------------------------------------------------------------------------

def test_dos_diagramas_van_como_fotos_sueltas(monkeypatch):
    update = _Update()
    _run_pipeline(monkeypatch, update, [_diagram(1), _diagram(2)])
    assert update.message.media_groups == []
    assert [p["photo"] for p in update.message.photos] == [
        "https://assets/p1.jpg",
        "https://assets/p2.jpg",
    ]
    # Caption descriptiva por foto: manual + página.
    assert update.message.photos[0]["caption"] == "📐 manual_1 — pág. 1"


def test_un_diagrama_foto_suelta(monkeypatch):
    update = _Update()
    _run_pipeline(monkeypatch, update, [_diagram(1)])
    assert update.message.media_groups == []
    assert len(update.message.photos) == 1


# ---------------------------------------------------------------------------
# >2 imágenes: un solo MEDIA GROUP, caption en la primera
# ---------------------------------------------------------------------------

def test_mas_de_dos_diagramas_van_en_album(monkeypatch):
    update = _Update()
    diagrams = [_diagram(1), _diagram(2), _diagram(3), _diagram(4)]
    _run_pipeline(monkeypatch, update, diagrams)
    assert update.message.photos == []  # ni una foto suelta
    assert len(update.message.media_groups) == 1  # UN solo mensaje-álbum
    media = update.message.media_groups[0]
    assert len(media) == 4
    assert all(isinstance(item, bot.InputMediaPhoto) for item in media)
    assert [item.media for item in media] == [
        "https://assets/p1.jpg",
        "https://assets/p2.jpg",
        "https://assets/p3.jpg",
        "https://assets/p4.jpg",
    ]
    # Caption SOLO en la primera (así Telegram la muestra bajo el álbum) y
    # lista todas las páginas adjuntas.
    assert media[0].caption is not None
    for n in (1, 2, 3, 4):
        assert f"manual_{n} — pág. {n}" in media[0].caption
    assert all(item.caption is None for item in media[1:])


def test_album_caption_truncada_a_1024(monkeypatch):
    update = _Update()
    diagrams = [_diagram(n) for n in range(1, 5)]
    for diagram in diagrams:
        diagram["section"] = "pág. " + "X" * 400
    _run_pipeline(monkeypatch, update, diagrams)
    media = update.message.media_groups[0]
    assert len(media[0].caption) <= 1024  # límite de caption de Telegram


# ---------------------------------------------------------------------------
# Fail-open del álbum → fotos sueltas
# ---------------------------------------------------------------------------

def test_album_fallido_degrada_a_fotos_sueltas(monkeypatch):
    update = _Update(media_group_error=RuntimeError("bad media"))
    diagrams = [_diagram(1), _diagram(2), _diagram(3)]
    _run_pipeline(monkeypatch, update, diagrams)
    assert update.message.media_groups == []
    assert [p["photo"] for p in update.message.photos] == [
        "https://assets/p1.jpg",
        "https://assets/p2.jpg",
        "https://assets/p3.jpg",
    ]
    # La respuesta de texto se sirvió igualmente (el canal visual falla abierto).
    assert update.message.replies == ["respuesta"]
