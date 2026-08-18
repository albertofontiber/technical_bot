# s325b — El extraction store a la nube: que una sesión cloud no dependa del PC

Propuesta sometida al dúo adversarial (Protocolo 3). **Impacto MEDIO en ZONA DE
DOLOR (corpus/ingesta)** ⇒ dúo COMPLETO: Sol xhigh + Fable.

## Objetivo y mandato

Alberto quiere usar el modo cloud **sin depender de tener el PC encendido**. Medido
hoy, el corpus fuente ya está casi todo en la nube y el hueco es UNO:

| Qué | Dónde | ¿Alcanzable desde cloud? |
|---|---|---|
| PDFs | bucket `manuales`: 1.007 objetos / 1.245 MB | sí (1.084/1.243 documents con `source_url`) |
| Imágenes | bucket `manual-images`: 17.615 / 3.812 MB | sí |
| Chunks, enunciados, hyq | Supabase | sí |
| **Extraction store** | **solo OneDrive**: `data/extraction/agent_anthropic-sonnet-45` = **1.143 JSON / 353,7 MB**; `data/extraction/llm` = 28 / 2,6 MB | **NO** |

Sin el store, la fase de enunciados y las re-ingestas exigen máquina local. Con él
en la nube, el único límite que queda es que un PDF *nuevo* debe llegar al bucket
(subida manual o harvest del portal) — eso no lo resuelve ningún montaje.

## Estado real de los tres consumidores (verificado, no supuesto)

- `scripts/enunciados_pass.py:52` — `STORE = "data/extraction/agent_anthropic-sonnet-45"`,
  consumido en `:144` como `glob.glob(f"{STORE}/*.json")`. **Ya tiene seam**: `--store`
  lo sobrescribe (`:433`, y además pisa `_s94.STORE`).
- `scripts/ingest_new.py:195,324` — `store = data_root / "data" / "extraction" / DEFAULT_CONFIG`,
  con gate `if not store.is_dir(): raise SystemExit(...)`.
- `scripts/derive_channels_lote.py:261-263` — compone la misma ruta y se la pasa a
  `enunciados_pass.py` por `--store`.

Los tres usan la MISMA forma: *un directorio del que se listan `*.json`*.

## Diseño propuesto

**1. Bucket `extraction`, PRIVADO.** Distinto de `manuales`, que es público-por-URL
por decisión de s315 (documentación oficial de fabricante redistribuible a los
técnicos). El store es contenido DERIVADO y no tiene por qué ser público: se lee con
`SUPABASE_SERVICE_KEY`, que ya está en el environment. Layout de claves espejo del
disco, para que el listado remoto y el local sean intercambiables:

    extraction/<config>/<nombre-de-fichero>.json
    p.ej. extraction/agent_anthropic-sonnet-45/FD2705R_es.json

**2. Resolutor `src/extraction_store.py` con DOS operaciones**, no más:

    listar(config) -> list[str]        # nombres de fichero, orden estable
    ruta_de(config, nombre) -> Path    # ruta local lista para abrir

Precedencia: **disco primero** (si `--data-root`/`--store` apunta a un directorio que
existe, comportamiento byte-idéntico al de hoy), **bucket después**. En modo bucket,
`ruta_de` descarga PEREZOSAMENTE ese fichero a una caché (`$TMPDIR/technical_bot_extraction/<config>/`)
y devuelve su ruta; si ya está cacheado, no vuelve a bajar.

Descartado a propósito: sincronizar los 354 MB enteros al arrancar. Un lote toca
decenas de documentos, no 1.143, y a 30+ fabricantes el store crece — la descarga
perezosa es lo que escala.

**3. Cambios en los consumidores: mínimos.** `enunciados_pass.py` sustituye el
`glob.glob(f"{STORE}/*.json")` por `listar(...)` y el open por `ruta_de(...)`;
`ingest_new.py` cambia el gate `store.is_dir()` por «el store resuelve» (local o
bucket); `derive_channels_lote.py` deja de forzar `--store` cuando no hay `--data-root`.

**4. Subida `scripts/upload_extraction_store.py`**, patrón de
`s315_upload_manuales_storage.py`: dry-run por defecto, `--aplicar`, idempotente y
reanudable (salta objetos ya presentes con el mismo tamaño+sha), recibo en
`evals/s325b_extraction_upload_v1.json`. Se corre EN LOCAL (es el único sitio que ve
OneDrive) y se añade al runbook: tras cada lote de ingesta local, re-subir.

**5. Integridad.** El control no se inventa: `extraction_sha256` ya es la clave de
desambiguación contra la DB en `enunciados_pass.py:222`. La subida estampa el sha256
del fichero en los metadatos del objeto, y `--verificar` compara listados y hashes
local vs bucket sin escribir nada.

## Riesgos declarados de entrada

1. **Dos fuentes de verdad.** Si alguien ingesta en local y no re-sube, una sesión
   cloud ve un store viejo. Mitigación: `--verificar` + runbook + el `extraction_sha256`
   que ya cruza contra la DB. NO se resuelve solo.
2. **Fallo silencioso.** Si un JSON no está ni en disco ni en el bucket, el resolutor
   debe fallar RUIDOSAMENTE (fail-closed, como el gate actual `SystemExit`), nunca
   devolver una lista corta que haga que un lote «pase» habiendo cubierto una fracción
   — que es exactamente el crítico que Sol cazó en s316.
3. **Coste de red y latencia** por documento en cloud; y la caché muere con la VM.
4. **Confidencialidad**: bucket privado, service key. Las extracciones son de manuales
   técnicos (sin PII), pero no deben ser públicas como los PDF.
5. **La subida sigue necesitando el PC una vez.** Es el último acto local.

## Qué quiero que ataquéis

1. ¿La precedencia disco→bucket puede producir un lote que se procese A MEDIAS sin
   que nada avise? ¿Dónde falta un fail-closed?
2. ¿`listar()` remoto es equivalente al `glob` local (orden, duplicados, paginación de
   la API de Storage por encima de 1.000 objetos — hay 1.143)?
3. ¿El layout de claves aguanta 30+ fabricantes y varias `config` de extracción?
4. ¿Es correcto el bucket PRIVADO, o rompe algo que hoy dependa de URL pública?
5. ¿Qué hace este diseño peor que simplemente sincronizar el directorio entero?
