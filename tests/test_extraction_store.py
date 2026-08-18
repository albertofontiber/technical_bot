"""Contratos del resolutor del extraction store (s325b).

Lo que se fija aquí es la propiedad que hace seguro mover el store a la nube: el
resolutor JAMÁS devuelve una lista corta en silencio. La lección viene de s316 —un
pipeline que estampa recibo habiendo cubierto una fracción del lote es peor que uno
que se para—, así que todos los caminos degradados tienen que LANZAR.
"""
import hashlib
import json

import pytest

from src.extraction_store import (
    BUCKET,
    MANIFIESTO,
    StoreError,
    abrir_store,
)


def _escribir_store(tmp_path, contenidos: dict[str, bytes]):
    d = tmp_path / "agent_anthropic-sonnet-45"
    d.mkdir(parents=True)
    for nombre, datos in contenidos.items():
        (d / nombre).write_bytes(datos)
    return d


def test_disco_manda_cuando_el_directorio_existe(tmp_path, monkeypatch):
    d = _escribir_store(tmp_path, {"aa.json": b'{"a": 1}', "bb.json": b'{"b": 2}'})
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "clave")

    store = abrir_store(directorio=d)

    assert store.origen == "disco", "con disco disponible no se toca la red"
    assert store.listar() == ["aa.json", "bb.json"]
    assert json.loads(store.ruta_de("aa.json").read_text(encoding="utf-8")) == {"a": 1}


def test_el_manifiesto_no_se_lista_como_un_documento(tmp_path):
    d = _escribir_store(tmp_path, {"aa.json": b"{}", MANIFIESTO: b"{}"})
    assert abrir_store(directorio=d).listar() == ["aa.json"]


def test_sin_disco_y_sin_keys_lanza_en_vez_de_devolver_vacio(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(StoreError, match="no hay extraction store"):
        abrir_store(directorio=tmp_path / "no-existe")


def test_fichero_ausente_en_disco_lanza(tmp_path):
    d = _escribir_store(tmp_path, {"aa.json": b"{}"})
    with pytest.raises(StoreError):
        abrir_store(directorio=d).ruta_de("zz.json")


# --- modo bucket, con transporte simulado -------------------------------

class _RespuestaFalsa:
    def __init__(self, contenido: bytes, status: int = 200):
        self.content = contenido
        self.status_code = status


def _bucket_falso(monkeypatch, objetos: dict[str, bytes], tmp_path):
    """Simula el Storage: devuelve bytes por clave, 404 para lo que no está."""
    import httpx

    llamadas: list[str] = []

    def _get(url, headers=None, timeout=None):
        clave = url.split(f"/object/{BUCKET}/", 1)[1]
        llamadas.append(clave)
        if clave not in objetos:
            return _RespuestaFalsa(b"", 404)
        return _RespuestaFalsa(objetos[clave])

    monkeypatch.setattr(httpx, "get", _get)
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "clave")
    monkeypatch.setenv("EXTRACTION_CACHE_DIR", str(tmp_path / "cache"))
    return llamadas


def _con_manifiesto(ficheros: dict[str, bytes], config="agent_anthropic-sonnet-45"):
    manifiesto = {
        n: {"sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)}
        for n, d in ficheros.items()
    }
    objetos = {f"{config}/{n}": d for n, d in ficheros.items()}
    objetos[f"{config}/{MANIFIESTO}"] = json.dumps(manifiesto).encode("utf-8")
    return objetos


def test_bucket_lista_desde_el_manifiesto_con_un_solo_get(tmp_path, monkeypatch):
    objetos = _con_manifiesto({"aa.json": b'{"a": 1}', "bb.json": b'{"b": 2}'})
    llamadas = _bucket_falso(monkeypatch, objetos, tmp_path)

    store = abrir_store(directorio=None)
    assert store.origen == "bucket"
    assert store.listar() == ["aa.json", "bb.json"]
    assert llamadas.count("agent_anthropic-sonnet-45/_manifest.json") == 1, (
        "listar no debe paginar el bucket: el manifiesto es UN objeto"
    )


def test_bucket_descarga_verifica_sha_y_cachea(tmp_path, monkeypatch):
    objetos = _con_manifiesto({"aa.json": b'{"a": 1}'})
    llamadas = _bucket_falso(monkeypatch, objetos, tmp_path)

    store = abrir_store(directorio=None)
    p1 = store.ruta_de("aa.json")
    assert json.loads(p1.read_text(encoding="utf-8")) == {"a": 1}

    descargas = llamadas.count("agent_anthropic-sonnet-45/aa.json")
    p2 = store.ruta_de("aa.json")
    assert p2 == p1
    assert llamadas.count("agent_anthropic-sonnet-45/aa.json") == descargas, (
        "el segundo acceso sale de la caché, no de la red"
    )


def test_bucket_rechaza_un_fichero_que_no_casa_con_su_sha(tmp_path, monkeypatch):
    objetos = _con_manifiesto({"aa.json": b'{"a": 1}'})
    objetos["agent_anthropic-sonnet-45/aa.json"] = b'{"a": 999}'  # corrupto
    _bucket_falso(monkeypatch, objetos, tmp_path)

    with pytest.raises(StoreError, match="no casa con el manifiesto"):
        abrir_store(directorio=None).ruta_de("aa.json")


def test_bucket_sin_manifiesto_lanza(tmp_path, monkeypatch):
    _bucket_falso(monkeypatch, {}, tmp_path)
    with pytest.raises(StoreError, match="no se pudo leer"):
        abrir_store(directorio=None).listar()


def test_fichero_fuera_del_manifiesto_lanza(tmp_path, monkeypatch):
    objetos = _con_manifiesto({"aa.json": b"{}"})
    _bucket_falso(monkeypatch, objetos, tmp_path)
    with pytest.raises(StoreError, match="no está en el manifiesto"):
        abrir_store(directorio=None).ruta_de("zz.json")


def test_indice_en_bucket_sale_del_manifiesto_sin_bajar_nada(tmp_path, monkeypatch):
    """`_build_sha_map` recorre el store entero: sin indice, el modo bucket se
    bajaria los 1.143 objetos en el primer uso (hallazgo convergente del duo)."""
    ficheros = {"aa.json": b'{"sha256": "' + b"a" * 64 + b'", "source_path": "C:/x/AA.pdf"}'}
    objetos = _con_manifiesto(ficheros)
    manifiesto = json.loads(objetos["agent_anthropic-sonnet-45/_manifest.json"])
    manifiesto["aa.json"].update({"source_path": "C:/x/AA.pdf", "sha_pdf": "a" * 64})
    objetos["agent_anthropic-sonnet-45/_manifest.json"] = json.dumps(manifiesto).encode()
    llamadas = _bucket_falso(monkeypatch, objetos, tmp_path)

    store = abrir_store(directorio=None)
    idx = store.indice()

    assert idx["aa.json"]["source_path"] == "C:/x/AA.pdf"
    assert idx["aa.json"]["sha_pdf"] == "a" * 64
    assert llamadas == ["agent_anthropic-sonnet-45/_manifest.json"], (
        "indice() no puede descargar extracciones"
    )


def test_buscar_por_sha_resuelve_el_nombre_exacto(tmp_path, monkeypatch):
    """`s94_f1_generate._sha_path` busca por PATRON (sha[:12]*), no por nombre."""
    sha = "b" * 64
    objetos = _con_manifiesto({f"{sha}.json": b"{}"})
    _bucket_falso(monkeypatch, objetos, tmp_path)
    store = abrir_store(directorio=None)

    assert store.buscar_por_sha(sha) == f"{sha}.json"
    assert store.buscar_por_sha("c" * 64) is None


def test_la_cache_se_indexa_por_sha_no_por_tamano(tmp_path, monkeypatch):
    """Una re-extraccion del MISMO peso no puede servirse de la cache vieja."""
    nombre = "aa.json"
    v1, v2 = b'{"v": 1}', b'{"v": 2}'  # mismo tamano, contenido distinto
    objetos = _con_manifiesto({nombre: v1})
    _bucket_falso(monkeypatch, objetos, tmp_path)
    p1 = abrir_store(directorio=None).ruta_de(nombre)
    assert p1.read_bytes() == v1

    objetos2 = _con_manifiesto({nombre: v2})
    _bucket_falso(monkeypatch, objetos2, tmp_path)
    p2 = abrir_store(directorio=None).ruta_de(nombre)
    assert p2.read_bytes() == v2, "la cache sirvio contenido viejo"
    assert p1 != p2


def test_indice_en_disco_lee_las_cabeceras(tmp_path):
    d = _escribir_store(tmp_path, {
        "aa.json": b'{"sha256": "' + b"d" * 64 + b'", "source_path": "C:/x/AA.pdf"}',
    })
    idx = abrir_store(directorio=d).indice()
    assert idx["aa.json"] == {"source_path": "C:/x/AA.pdf", "sha_pdf": "d" * 64}


def test_publicar_sube_el_objeto_y_luego_el_manifiesto(tmp_path, monkeypatch):
    """La PUERTA UNICA: quien escribe el store publica en el mismo acto.

    El orden importa: primero el objeto, despues el manifiesto. Al reves, un corte
    dejaria una entrada registrada sin objeto detras — y eso si rompe una lectura.
    """
    import httpx

    from src.extraction_store import publicar_al_bucket

    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "clave")
    subidas: list[tuple[str, bytes]] = []

    def _post(url, headers=None, content=None, timeout=None):
        subidas.append((url.split("/object/extraction/", 1)[1], content))
        return _RespuestaFalsa(b"", 200)

    def _get(url, headers=None, timeout=None):
        return _RespuestaFalsa(b"", 404)  # aun no hay manifiesto

    monkeypatch.setattr(httpx, "post", _post)
    monkeypatch.setattr(httpx, "get", _get)

    fichero = tmp_path / ("c" * 64 + ".json")
    cuerpo = b'{"sha256": "' + b"c" * 64 + b'", "source_path": "C:/x/CC.pdf"}'
    fichero.write_bytes(cuerpo)

    publicar_al_bucket(fichero)

    claves = [c for c, _ in subidas]
    assert claves == [f"agent_anthropic-sonnet-45/{'c' * 64}.json",
                      "agent_anthropic-sonnet-45/_manifest.json"]
    manifiesto = json.loads(subidas[1][1].decode("utf-8"))
    entrada = manifiesto[f"{'c' * 64}.json"]
    assert entrada["sha256"] == hashlib.sha256(cuerpo).hexdigest()
    assert entrada["source_path"] == "C:/x/CC.pdf"
    assert entrada["sha_pdf"] == "c" * 64


def test_publicar_sin_credenciales_lanza(tmp_path, monkeypatch):
    from src.extraction_store import publicar_al_bucket

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    f = tmp_path / "aa.json"
    f.write_bytes(b"{}")
    with pytest.raises(StoreError, match="no se puede publicar"):
        publicar_al_bucket(f)


def test_pipeline_run_recorre_el_store_resuelto_sin_romperse(tmp_path, monkeypatch):
    """Humo de `src/reingest/pipeline.run` con el store resuelto.

    Existe porque al cablear el resolutor renombre el universo de `files` a
    `nombres` y deje CUATRO referencias huerfanas: los caminos normales (dry_run,
    register_only, done) reventaban con NameError y la suite no lo vio — no habia
    ni un test que EJECUTARA `run()`. Lo cazo Sol en la segunda ronda del duo.
    """
    from src.reingest import pipeline

    d = tmp_path / "agent_anthropic-sonnet-45"
    d.mkdir(parents=True)
    sha = "a" * 64
    # Texto en espanol => el documento recorre la rama `dry_run`, que es una de las
    # tres que tenian la referencia huerfana (pipeline.py:304).
    texto = ("La central de deteccion FD2705R debe instalarse conforme a la norma "
             "vigente. La tension nominal es de 24 voltios en corriente continua y "
             "el consumo maximo alcanza 250 miliamperios en alarma general. El "
             "equipo admite hasta 2 lazos.")
    (d / f"{sha}.json").write_text(json.dumps({
        "sha256": sha, "source_path": r"C:\x\AA.pdf", "pages": 1,
        "result": {"pages": [{"page": 1, "md": texto, "items": [{"md": texto}]}]},
    }), encoding="utf-8")

    monkeypatch.setattr(pipeline, "STORE_ROOT", str(tmp_path))
    monkeypatch.setattr(pipeline, "STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setattr(pipeline, "REGISTER_FILE", str(tmp_path / "reg.json"))
    monkeypatch.setattr(pipeline, "DRYRUN_SAMPLE", str(tmp_path / "sample.json"))

    pipeline.run("agent_anthropic-sonnet-45", 0, True, True)   # no debe lanzar

    # En dry-run el estado no se persiste; lo que SI se escribe es la muestra, y solo
    # se escribe si el documento LLEGO al final de la rama procesada — que es
    # exactamente lo que la referencia huerfana rompia.
    muestra = json.loads((tmp_path / "sample.json").read_text(encoding="utf-8"))
    assert len(muestra) == 1


def test_pipeline_run_aborta_si_no_hay_store(tmp_path, monkeypatch):
    """Sin disco y sin credenciales, `run` SALE con codigo != 0 (guarda s301)."""
    from src.reingest import pipeline

    monkeypatch.setattr(pipeline, "STORE_ROOT", str(tmp_path / "no-existe"))
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    with pytest.raises(SystemExit, match="No hay store"):
        pipeline.run("agent_anthropic-sonnet-45", 0, True, True)
