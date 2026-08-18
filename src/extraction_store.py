# -*- coding: utf-8 -*-
"""Resolutor del extraction store: disco primero, bucket después (s325b).

POR QUÉ. El store (`data/extraction/<config>/*.json`) vivía SOLO en OneDrive, y era
lo que ataba la fase de enunciados y las re-ingestas a tener el PC encendido. Con el
store también en el bucket privado `extraction`, una sesión cloud puede LEERLO sin
máquina local; en local NO cambia nada, porque si el directorio está, se usa él.

ALCANCE (dúo s325b, adjudicado por Alberto): esto cubre el CONSUMO. La ingesta de
manuales nuevos sigue siendo local — `scripts/ingest_new.py` no solo lee: ESCRIBE la
extracción nueva al store y exige los PDFs y su sidecar `_metadata.json` en disco.
Por eso aquí no hay operación de publicación: prometerla sin cablear la escritura
haría que una re-ingesta en cloud produjera JSONs en una caché efímera que nunca
entran al manifiesto, y la fuente de verdad divergiría en silencio.

CONTRATO. Cuatro operaciones, y cada una existe porque un consumidor real la hace:

    store = abrir_store()                 # o abrir_store(directorio=...)
    store.listar()                        # nombres — `pipeline.run`, `enunciados_pass`
    store.ruta_de(nombre)                 # ruta local lista para abrir
    store.indice()                        # nombre -> {source_path, sha_pdf}
    store.buscar_por_sha(sha)             # nombre exacto a partir de un sha

`indice()` es lo que evita que el modo bucket degenere: `_build_sha_map` construye su
mapa doc→sha leyendo la CABECERA de los 1.143 ficheros, así que sin índice el primer
uso se bajaría el store entero. En bucket sale del manifiesto con un solo GET.

FAIL-CLOSED a propósito (lección s316: un pipeline que estampa recibo habiendo
cubierto una fracción del lote es peor que uno que se para). Si no hay ni disco ni
bucket, si falta el manifiesto, o si un fichero descargado no casa con su sha256,
esto LANZA `StoreError`. Nunca devuelve una lista corta en silencio. Quien consuma
debe distinguir ese error de INFRAESTRUCTURA de un «documento sin extracción», que
sí es esperable en un lote real (decisión del dúo s316 en `derive_channels_lote`).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

CONFIG_POR_DEFECTO = "agent_anthropic-sonnet-45"
BUCKET = "extraction"
MANIFIESTO = "_manifest.json"
CABECERA = 600  # bytes que basta leer para sacar source_path y sha256 del PDF

_RE_SOURCE = re.compile(r'"source_path":\s*"([^"]+)"')
_RE_SHA = re.compile(r'"sha256":\s*"([0-9a-f]{16,})"')


class StoreError(RuntimeError):
    """El store no se puede resolver o su contenido no es íntegro."""


def _cabecera(datos: bytes) -> dict:
    cab = datos[:CABECERA].decode("utf-8", "ignore")
    mm, ms = _RE_SOURCE.search(cab), _RE_SHA.search(cab)
    return {"source_path": mm.group(1) if mm else None,
            "sha_pdf": ms.group(1) if ms else None}


class _StoreDisco:
    origen = "disco"

    def __init__(self, directorio: Path):
        self.directorio = directorio
        self._indice: dict[str, dict] | None = None

    def listar(self) -> list[str]:
        return sorted(
            p.name for p in self.directorio.glob("*.json") if p.name != MANIFIESTO
        )

    def ruta_de(self, nombre: str) -> Path:
        p = self.directorio / nombre
        if not p.is_file():
            raise StoreError(f"{nombre} no está en {self.directorio}")
        return p

    def indice(self) -> dict[str, dict]:
        # CACHEADO, igual que el manifiesto en el lado bucket: sin esto, cada búsqueda
        # fallida releía las cabeceras de los 1.143 ficheros y un lote con muchos
        # misses salía O(n·m) de I/O (hallazgo de Fable, ronda 2). Leer la cabecera de
        # cada fichero es el mismo coste que tenía el código original.
        if self._indice is None:
            self._indice = {
                nombre: _cabecera((self.directorio / nombre).read_bytes()[:CABECERA])
                for nombre in self.listar()
            }
        return self._indice

    def buscar_por_sha(self, sha: str) -> str | None:
        directo = f"{sha}.json"
        if (self.directorio / directo).is_file():
            return directo
        # El match EXACTO por sha del PDF va antes que el de prefijo: un prefijo de 12
        # hex es improbable que colisione, pero si colisionara el prefijo ganaría por
        # orden lexicográfico y devolvería el fichero equivocado (Fable, ronda 2).
        for nombre, cab in self.indice().items():
            if cab.get("sha_pdf") == sha:
                return nombre
        for p in sorted(self.directorio.glob(f"{sha[:12]}*.json")):
            return p.name
        return None

    def __repr__(self) -> str:
        return f"<store disco {self.directorio}>"


class _StoreBucket:
    origen = "bucket"

    def __init__(self, config: str, url: str, key: str, cache: Path):
        self.config = config
        self.url = url.rstrip("/")
        self.key = key
        self.cache = cache
        self._manifiesto: dict[str, dict] | None = None

    @property
    def _h(self) -> dict:
        return {"apikey": self.key, "Authorization": f"Bearer {self.key}"}

    def _descargar(self, clave: str) -> bytes:
        import httpx

        # TODO fallo de lectura sale como StoreError, incluidos los de transporte
        # (timeout, DNS, conexión). Si escapara un `httpx.ReadTimeout` tal cual, el
        # consumidor —que solo relanza StoreError— lo degradaría a «error de este
        # documento» y el tramo podría cerrarse con rc=0 con la red caída: el mismo
        # agujero que esta clase existe para tapar (crítico de Sol, ronda 2).
        try:
            r = httpx.get(f"{self.url}/storage/v1/object/{BUCKET}/{clave}",
                          headers=self._h, timeout=120)
        except Exception as exc:
            raise StoreError(f"fallo de transporte leyendo {BUCKET}/{clave}: "
                             f"{type(exc).__name__}: {exc}")
        if r.status_code >= 400:
            raise StoreError(
                f"no se pudo leer {BUCKET}/{clave}: HTTP {r.status_code}. "
                "¿Se subió el store con scripts/upload_extraction_store.py?"
            )
        return r.content

    def manifiesto(self) -> dict[str, dict]:
        if self._manifiesto is None:
            # Un GET en vez de paginar 1.143 objetos de 1.000 en 1.000.
            crudo = self._descargar(f"{self.config}/{MANIFIESTO}")
            try:
                datos = json.loads(crudo.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                # Un manifiesto ilegible es infraestructura rota, no «no hay nada».
                raise StoreError(f"manifiesto de {BUCKET}/{self.config} ilegible: {exc}")
            if not isinstance(datos, dict):
                raise StoreError(
                    f"manifiesto de {BUCKET}/{self.config} con forma inesperada"
                )
            self._manifiesto = datos
        return self._manifiesto

    def listar(self) -> list[str]:
        return sorted(n for n in self.manifiesto() if n != MANIFIESTO)

    def indice(self) -> dict[str, dict]:
        return {
            n: {"source_path": e.get("source_path"), "sha_pdf": e.get("sha_pdf")}
            for n, e in self.manifiesto().items()
            if n != MANIFIESTO
        }

    def buscar_por_sha(self, sha: str) -> str | None:
        man = self.manifiesto()
        directo = f"{sha}.json"
        if directo in man:
            return directo
        # Exacto ANTES que prefijo, por el mismo motivo que en el lado disco.
        for nombre in sorted(man):
            if (man[nombre] or {}).get("sha_pdf") == sha:
                return nombre
        for nombre in sorted(man):
            if nombre.startswith(sha[:12]):
                return nombre
        return None

    def ruta_de(self, nombre: str) -> Path:
        esperado = self.manifiesto().get(nombre)
        if esperado is None:
            raise StoreError(
                f"{nombre} no está en el manifiesto de {BUCKET}/{self.config}"
            )
        sha = esperado["sha256"]

        # La caché se indexa por SHA, no por tamaño: una re-extracción del mismo
        # peso no puede reutilizar el fichero viejo (hallazgo de Fable, dúo s325b).
        destino = self.cache / f"{Path(nombre).stem}.{sha[:12]}.json"
        if destino.is_file():
            return destino

        datos = self._descargar(f"{self.config}/{nombre}")
        real = hashlib.sha256(datos).hexdigest()
        if real != sha:
            raise StoreError(
                f"{nombre} descargado no casa con el manifiesto "
                f"(sha {real[:12]} vs {sha[:12]})"
            )
        # Escritura atómica: un corte a mitad no debe dejar un JSON truncado.
        self.cache.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self.cache, delete=False,
                                         suffix=".parcial") as tmp:
            tmp.write(datos)
            parcial = Path(tmp.name)
        parcial.replace(destino)
        return destino

    def __repr__(self) -> str:
        return f"<store bucket {BUCKET}/{self.config}>"


def publicar_al_bucket(ruta_local: str | Path,
                       config: str = CONFIG_POR_DEFECTO) -> None:
    """Publica una extracción recién escrita: sube el objeto Y actualiza el manifiesto.

    Es la PUERTA ÚNICA de consistencia. El store tiene un solo productor
    (`scripts/ingest_new.py`, que escribe `<sha>.json` en disco), así que la forma
    de que el bucket no derive del disco no es acordarse de re-subir: es que el
    mismo acto que escribe, publique. El `--verificar` del script de subida queda
    como red de seguridad, no como el mecanismo.

    Sube el objeto ANTES de tocar el manifiesto: si algo falla entre medias, sobra
    un objeto sin registrar (invisible para `listar()`, inocuo) en vez de faltar uno
    registrado — que sí rompería una lectura.
    """
    import httpx

    ruta = Path(ruta_local)
    datos = ruta.read_bytes()
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not (url and key):
        raise StoreError(
            "no se puede publicar: faltan SUPABASE_URL / SUPABASE_SERVICE_KEY"
        )
    h = {"apikey": key, "Authorization": f"Bearer {key}"}

    def _subir(clave: str, cuerpo: bytes) -> None:
        r = httpx.post(f"{url}/storage/v1/object/{BUCKET}/{clave}",
                       headers={**h, "Content-Type": "application/json",
                                "x-upsert": "true"},
                       content=cuerpo, timeout=180)
        if r.status_code >= 300:
            raise StoreError(f"no se pudo publicar {clave}: HTTP {r.status_code} "
                             f"{r.text[:120]}")

    _subir(f"{config}/{ruta.name}", datos)

    # Leer el manifiesto para AÑADIR una entrada. Solo un 404 significa "todavía no
    # hay manifiesto"; cualquier otro fallo (500 transitorio, timeout, JSON roto) NO
    # puede tratarse como "está vacío", porque el paso siguiente lo SOBRESCRIBE: un
    # hipo de red dejaría un manifiesto con una sola entrada y el resto del store
    # invisible para `listar()` (crítico de Sol, ronda 2).
    try:
        r = httpx.get(f"{url}/storage/v1/object/{BUCKET}/{config}/{MANIFIESTO}",
                      headers=h, timeout=60)
    except Exception as exc:
        raise StoreError(f"no se pudo leer el manifiesto para actualizarlo: {exc}")
    if r.status_code == 404:
        manifiesto: dict = {}
    elif r.status_code >= 400:
        raise StoreError(
            f"el manifiesto respondió HTTP {r.status_code}: no se sobrescribe a ciegas"
        )
    else:
        try:
            manifiesto = json.loads(r.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StoreError(f"manifiesto ilegible ({exc}): no se sobrescribe a ciegas")
        if not isinstance(manifiesto, dict):
            raise StoreError("manifiesto con forma inesperada: no se sobrescribe")

    manifiesto[ruta.name] = {"sha256": hashlib.sha256(datos).hexdigest(),
                             "bytes": len(datos), **_cabecera(datos)}
    _subir(f"{config}/{MANIFIESTO}",
           json.dumps(manifiesto, ensure_ascii=False, indent=1).encode("utf-8"))

    # LÍMITE DECLARADO: esto es read-modify-write sin CAS. Supabase Storage no ofrece
    # compare-and-swap, así que dos publicaciones simultáneas pueden perder una
    # entrada (la última gana). Hoy no ocurre —`ingest_new` es un proceso único por
    # lote— y la red de seguridad es `upload_extraction_store.py`, que reconstruye el
    # manifiesto entero desde el disco. Si algún día hay ingestas concurrentes, esto
    # necesita un lock antes que cualquier otra cosa.


def abrir_store(
    config: str = CONFIG_POR_DEFECTO,
    directorio: str | Path | None = None,
    *,
    permitir_bucket: bool = True,
):
    """Devuelve el store a usar. Disco primero; bucket si no hay disco.

    `directorio` es lo que hoy llega por `--store` / `--data-root`. Si apunta a un
    directorio existente, se usa tal cual y el comportamiento es el de siempre.
    """
    if directorio is not None:
        d = Path(directorio)
        if d.is_dir():
            return _StoreDisco(d)

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if permitir_bucket and url and key:
        raiz = os.getenv("EXTRACTION_CACHE_DIR") or str(
            Path(tempfile.gettempdir()) / "technical_bot_extraction"
        )
        return _StoreBucket(config, url, key, Path(raiz) / config)

    raise StoreError(
        f"no hay extraction store: {directorio or '(sin --store/--data-root)'} no es un "
        "directorio y falta SUPABASE_URL/SUPABASE_SERVICE_KEY para leer del bucket "
        f"`{BUCKET}`. En local pasa --data-root; en cloud, define las variables."
    )
