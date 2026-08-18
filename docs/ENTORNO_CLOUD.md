# Entorno cloud y trabajo «on the go» — dónde corre Claude

> **Objetivo.** Lanzar y GOBERNAR el trabajo desde el móvil con la misma autonomía
> que en local. Reescrito en **s323** contra la documentación oficial vigente: la
> versión anterior (s315c) mandaba a un menú «Environments» que ya no se llama así
> y daba por buena una lista de secretos que hoy tiene una advertencia explícita.

## 1. Alcance adoptado: Cloud + Dispatch (el selector «dónde corre Claude»)

**Adjudicación de Alberto (s323): se adoptan DOS superficies, Cloud y Dispatch.**
Remote Control queda documentado pero NO adoptado — se activa el día que haga
falta conducir una sesión local paso a paso desde el móvil.

| Superficie | Dónde corre | Qué cubre aquí | Qué NO |
|---|---|---|---|
| **Cloud session** ✅ | VM de Anthropic (Ubuntu 24.04) | evals, sondas, harness, código, docs, DB, harvest de portales. **Sigue con el PC apagado** | **OneDrive**: PDFs del corpus y el extraction store |
| **Dispatch** ✅ | **Tu PC** (pestaña *Cowork* de la app de escritorio) | le mandas la tarea desde el móvil y, si es trabajo de código, abre una sesión de Code **en tu máquina** ⇒ ve OneDrive y el `.env` | necesita el PC encendido (Pro/Max; no existe en Team/Enterprise) |
| **Remote Control** ⬜ | Tu PC, conducido desde móvil/web | conversación en vivo con una sesión local | no adoptado por ahora |

**Consecuencia útil de esa combinación**: como las sesiones que abre Dispatch corren
en el PC, **el gap de OneDrive queda cubierto igualmente** — la diferencia con Remote
Control es el modo (le encargas y te avisa, en vez de conducir tú el turno). Ojo: en
sesiones nacidas de Dispatch, las aprobaciones de apps caducan a los 30 minutos y
vuelven a pedirse, en vez de durar toda la sesión.

**Dónde está el selector:** el icono de nube en la fila de encima del cuadro de
mensaje, en claude.ai/code, en la app de escritorio y en la app móvil. No hay
página de ajustes ni URL directa. Ahí se crean y editan los environments.

**Regla de decisión:** ¿el trabajo toca PDFs/OneDrive, o necesita el `.env` y los
MCPs locales? → Dispatch (o sesión normal aquí). ¿Es evals, DB, código o docs y
quieres cerrar el portátil? → Cloud. Doc oficial:
<https://code.claude.com/docs/en/claude-code-on-the-web> ·
<https://code.claude.com/docs/en/cloud-environments> ·
<https://code.claude.com/docs/en/desktop#sessions-from-dispatch>

## 2. Qué es automático (versionado en el repo, no en la web)

- **`.claude/hooks/session-start.sh`** — deja el contenedor listo: dependencias con
  sus tres workarounds (langdetect, PyJWT/cryptography de deb, requirements-dev
  arrastrando el base), **historial git COMPLETO** (los tests de contratos congelados
  leen blobs viejos; sin `unshallow` fallan ~180) y `PYTHONPATH=.`. Corre solo si
  `CLAUDE_CODE_REMOTE=true`, que es la variable canónica documentada.
  **s323: idempotente** — un `resume` ya no reinstala (centinela = huella sha1 de los
  requirements + import real; si cambian los requirements o la VM es nueva, reinstala).
- **`scripts/cloud_smoke.py`** — verificador del entorno con recibo. Es el
  instrumento del Protocolo 1 aquí: sin él, «el cloud funciona» es una declaración
  sin comprobar. Contrato fijado en `tests/test_cloud_smoke.py`: **nunca vuelca el
  valor de un secreto** — solo presencia y longitud. Todo detalle pasa por un
  saneador único antes de imprimirse o serializarse, porque las dos vías de fuga
  reales no son la lista de keys sino los mensajes de error de httpx (llevan la
  URL dentro) y `r.text` de una respuesta 4xx; y la URL del remote se publica sin
  su `usuario:token@` (en un clon cloud viene con credencial embebida). Los cuatro
  caminos están cubiertos por test, red incluida, con transporte simulado.

```
python scripts/cloud_smoke.py                # entorno + deps + keys + conectividad
python scripts/cloud_smoke.py --sin-red      # sin llamadas a APIs
python scripts/cloud_smoke.py --sin-dotenv   # desde LOCAL, simula lo que vería el cloud
```

**Qué llega y qué no a una sesión cloud** (sale de un clon fresco del repo):

| Llega | No llega |
|---|---|
| `CLAUDE.md`, `docs/`, `.claude/settings.json` y sus hooks | `~/.claude/CLAUDE.md`, skills, agentes y comandos de usuario |
| Lo que esté commiteado, sin más | MCPs locales — este repo **no tiene `.mcp.json`**: en cloud la DB se toca por REST con `SUPABASE_*`, no por MCP |
| Los tests, los golds, los recibos | El `.env` (por eso las keys van al environment) |
| Los PDFs (bucket `manuales`) y el **extraction store** (bucket `extraction`, §3.5) | Los PDFs **nuevos** sin subir y su sidecar `_metadata.json` de identidad |

## 3. Checklist de Alberto (una vez, ~10 min)

### 3.1 Environment cloud

Selector de nube → **Add cloud environment** (o el engranaje del existente).

- **Network access: Full.** Decisión de Alberto en s323 (DEC-220). *Trusted* —el
  nivel por defecto— es lo que bloqueó casmarglobal en s315 y deja fuera Supabase,
  Voyage y OpenAI.
- **Environment variables** (formato `.env`, un `KEY=value` por línea; los valores
  están en tu `.env` local / dashboard de Railway):

| Variable | Para qué | ¿Imprescindible? |
|---|---|---|
| `SUPABASE_URL` | scripts contra la DB (harness, sondas, loaders) | sí |
| `SUPABASE_SERVICE_KEY` | ídem — los SCRIPTS leen esto, el MCP no llega | sí |
| `ANTHROPIC_API_KEY_SCRIPTS` | generadores, harness, sondas, **revisor Fable**. Ese nombre y no `ANTHROPIC_API_KEY`: la plataforma filtra la original y la sesión no la ve (§3.6); el hook la reconstruye | sí |
| `VOYAGE_API_KEY` | embeddings de `chunks_v2` (retrieval real) | sí |
| `OPENAI_API_KEY` | **revisor Sol del dúo (Protocolo 3)** y juez | sí — sin ella, s316 se repite |
| `DATABASE_URL` | scripts de operador **en local** (rgpd_retencion, marcar_utilidad). En cloud NO habilita DDL: no hay TCP al 5432 (§3.4) | opcional |
| `RAILWAY_TOKEN` | censo de flags y variables vivas de producción | opcional |
| `NOTIFIER_USER` / `NOTIFIER_PASSWORD` | harvest del portal Notifier | opcional |
| `LLAMAPARSE_API_KEY` | LlamaParse. **Ese es el nombre** que lee `ingest_new.py:319` — el `LLAMA_CLOUD_API_KEY` que decía el doc de s315c no lo lee nadie | opcional |

**NO añadir `TELEGRAM_BOT_TOKEN`**: el bot vive en Railway y un script haciendo
polling en una sesión cloud competiría con producción, robándole updates a los
técnicos. `cloud_smoke.py` avisa si aparece.

**Riesgo aceptado (DEC-220):** los environments **no tienen secret store** — la
doc oficial desaconseja meter credenciales, porque son legibles por cualquiera que
use el environment. Con red *Full* y la service key del corpus dentro, una sesión
que lea un portal o un PDF hostil tiene, en principio, con qué exfiltrar. Se acepta
a cambio de que ninguna sesión se quede a medias por una política de red, y la
mitigación es operativa: environment **personal** (nunca compartido) y **rotar
keys** ante cualquier sospecha. Partirlo en dos environments por privilegio
(`código` sin service key / `datos` con ella) son 2 minutos en el mismo selector el
día que se prefiera.

### 3.2 Smoke de recepción (sin esto no está montado)

En la primera sesión cloud del environment nuevo:

```
python scripts/cloud_smoke.py && python -m pytest -q && python scripts/check_deps.py
```

Debe dar `VEREDICTO: LISTO` y la suite en verde. El recibo queda en
`evals/s323_cloud_smoke_v1.json` y se commitea: es la prueba fechada de que ese
environment sirve. Repetir cuando caduque el caché (~7 días) o al tocar una variable.

### 3.3 Móvil y Dispatch

- **App**: Claude para iOS/Android, misma cuenta claude.ai → pestaña **Code**: ahí
  están las sesiones cloud (empezar una, contestar preguntas, revisar el diff,
  pedirle que abra el PR o que vigile CI de uno abierto).
- **Dispatch**: vive en la pestaña **Cowork**, no en Code. Le mandas la tarea desde
  el móvil como un mensaje; si es trabajo de desarrollo, abre una sesión de Code **en
  tu PC** —aparece en la barra lateral con el badge *Dispatch*— y te llega un push
  cuando termina o cuando necesita tu aprobación. Es la vía para lo que toca OneDrive
  o el `.env`, y requiere el PC encendido.
- **Traer una sesión cloud al terminal**: `claude --teleport` (árbol limpio, mismo
  repo, misma cuenta). Hoy no hay CLI `claude` en el PATH de esta máquina; desde la
  app de escritorio se usa el menú **Continue in**.

### 3.4 Supabase: qué hace falta configurar (y qué no)

**Para DATOS (leer, insertar, actualizar, borrar, RPC): nada.** Los scripts van por
REST con `SUPABASE_SERVICE_KEY`, que es la clave `service_role` y **se salta RLS**;
es la misma ruta que ya usan en local y que usa el bot en Railway. Con esa variable
en el environment y red *Full*, una sesión cloud escribe en la DB sin tocar nada del
lado de Supabase (verificado: `GET /rest/v1/documents` → 200).

**Para ESQUEMA (DDL/migraciones) la vía en cloud es el CONECTOR MCP de Supabase**, no
la conexión directa. Medido en el smoke de recepción (s325d): con red **Full**, un
`psycopg2.connect` al pooler da **timeout en el puerto 5432** contra las dos IPs del
host — el proxy de la sesión deja pasar HTTP/HTTPS, no TCP arbitrario. `DATABASE_URL`
sigue siendo la vía en LOCAL (`rgpd_retencion.py`, `marcar_utilidad.py`), y ponerla en
el environment no hace daño, pero **no habilita DDL desde cloud**. El conector MCP, en
cambio, viaja por los servidores de Anthropic y ni siquiera depende de la allowlist —
es como se aplicaron las migraciones históricas (DEC-140, migración 007).

`cloud_smoke.py` lo comprueba (`red:postgres`, no crítico): en una sesión cloud, ese
FALLO es el comportamiento esperado y no un environment mal montado.

**Lo único que SÍ rompería una sesión cloud** son las *Network Restrictions* de
Supabase (allowlist de IPs, en Settings → Database): las sesiones salen desde IPs de
Anthropic, que no son fijas. Están desactivadas por defecto; si algún día se activan,
hay que contar con esto. El `service_role` no las esquiva.

### 3.5 El extraction store en la nube (s325b) — y lo que SIGUE siendo local

El store (`data/extraction/<config>/*.json`, un fichero por PDF llamado `<sha>.json`)
vivía **solo en OneDrive**: 1.143 JSON / 353,7 MB en `agent_anthropic-sonnet-45` y 28
/ 2,6 MB en `llm`. Era lo que ataba la fase de enunciados y las re-ingestas al PC.

Ahora vive también en el bucket **privado** `extraction` (privado a conciencia:
`manuales` es público-por-URL porque el bot sirve esos PDFs a los técnicos; el store
es contenido derivado). Quién lo lee no cambia de código: `src/extraction_store.py`
resuelve **disco primero, bucket después**, así que en local todo sigue igual.

```
python scripts/upload_extraction_store.py "<data-root>"             # dry-run
python scripts/upload_extraction_store.py "<data-root>" --aplicar   # se corre en LOCAL
python scripts/upload_extraction_store.py "<data-root>" --verificar # cruza SHA local vs bucket
```

**Consistencia (la parte que evita el problema, no que lo detecta).** El store tiene
**un solo productor**: `scripts/ingest_new.py`, el único sitio del repo que escribe
`<sha>.json`. Ahí mismo, en el acto que escribe, se **publica al bucket**
(`publicar_al_bucket`) y se actualiza el manifiesto. Así el bucket no depende de que
nadie se acuerde de re-subir. La publicación es **fail-open declarado**: la extracción
ya está en disco y cuesta dinero, así que un fallo de red no tumba la ingesta — queda
anotado en el resultado del documento y en el recibo del lote.

Las otras dos capas son red, no mecanismo:

1. **`--verificar`** cruza el **sha** de cada fichero local contra el manifiesto del
   bucket (no el tamaño: un JSON re-extraído del mismo peso pasaba desapercibido).
   Correrlo tras cada lote y cuando algo huela raro.
2. **La `config` ES la versión del mecanismo de extracción**: `agent_anthropic-sonnet-45`,
   `llm`, y lo que venga. Cambiar de extractor significa un **prefijo nuevo** en el
   bucket, no pisar el anterior — por eso un cambio de mecanismo no puede producir una
   mezcla silenciosa de extracciones viejas y nuevas bajo el mismo nombre. Re-extraer
   con el MISMO mecanismo sí cambia el sha, y entonces la publicación (o `--verificar`)
   lo reconcilia.

Detalles que importan: cada config sube un `_manifest.json` con `sha256`, `bytes`,
`source_path` y `sha_pdf` por fichero, de forma que `listar()` y el mapa doc→sha
cuesten **un GET** en vez de recorrer 1.143 objetos; la caché local se indexa por sha
(`EXTRACTION_CACHE_DIR` para moverla); y todo camino degradado **lanza** en vez de
devolver una lista corta — un fallo del store aborta el tramo en lugar de contarse
como «documento sin extracción», que es el aviso esperable de un lote real.

**Lo que sigue siendo local (declarado, no pendiente):** **ingestar manuales nuevos**.
`scripts/ingest_new.py` no solo lee el store: **escribe** en él la extracción nueva, y
antes exige los PDFs en `Manuales_<canal>` con su `_metadata.json`. Por eso el
resolutor no ofrece publicación: prometerla sin cablear la escritura haría que una
ingesta en cloud dejara JSONs en una caché efímera que nunca entran al manifiesto, y
la fuente de verdad divergiría en silencio. Cubrir eso es otro frente (subir PDFs y
sidecars + operación de publicación), con su propio dúo.

### 3.6 Lo que midió el smoke de recepción (s325d, 18-ago) — environment VERIFICADO

Recibo de aceptación: `evals/s323_cloud_smoke_v1.json` (PR #291). En una sesión cloud
del environment `technical-bot`: `cloud_smoke` **LISTO** (0 críticos), `pytest` **4447
passed / 45 skipped**, `check_deps` OK, y el bucket sirviendo sus **1.143
extracciones**. Hizo falta un segundo intento, y lo que enseñó el primero (recibo
NO LISTO, PR #289) es lo que hay que saber antes de montar otro environment:

- **`ANTHROPIC_API_KEY` NO llega al contenedor.** La UI avisa de que «no se usará para
  autenticar las solicitudes» y, comprobado, **la sesión no la ve aunque la pegues**.
  Nuestros scripts (harness, sondas, generadores, **revisor Fable**) sí la necesitan:
  sin ella una sesión cloud no puede correr el dúo. **Define
  `ANTHROPIC_API_KEY_SCRIPTS`** en el environment y `session-start.sh` reconstruye
  `ANTHROPIC_API_KEY` al arrancar.
- **Arranque en frío ~95 s** (medido por mtimes): 25 s de clon, 10 s de `unshallow` y
  **60 s de instalación de dependencias** en VM nueva. Se deja en el hook a propósito:
  moverlo al setup script lo cachearía ~7 días, pero no compensa duplicar la lógica
  fuera del repo. Si algún día duele, ese es el movimiento y este es el dato.
- **Sin TCP al 5432** (§3.4): las migraciones desde cloud van por el conector MCP.
- Avisos que son CORRECTOS y no hay que arreglar: `langdetect` (no compila su wheel y
  no lo importa nadie), `LLAMAPARSE_API_KEY` y `NOTIFIER_*` (no se usan en cloud).

## 4. Trampas conocidas (medidas, no supuestas)

- **El dúo del Protocolo 3 es la primera víctima**: sin `OPENAI_API_KEY` en el
  environment, Sol no es ejecutable y una sesión cloud NO puede cerrar nada de
  impacto ALTO. Pasó en s315/s316 y el `cloud_smoke` lo marca como crítico.
- **`gh` no viene preinstalado** y `GH_TOKEN` vale `proxy-injected`: las herramientas
  de GitHub integradas funcionan, pero un script que lea `GITHUB_TOKEN` recibe el
  placeholder, no un token. El `git push` solo funciona contra la rama de la sesión.
- **Caché del environment**: el setup script se cachea ~7 días; el hook, no — corre
  en cada arranque (por eso ahora es idempotente). Si el arranque en frío duele, se
  puede mover la instalación a un setup script; medir primero con
  `echo $CLAUDE_PROJECT_DIR` para conocer la ruta real del clon.
- **Recursos del VM**: 30 GB de disco y memoria acotada — un `full` de un assessment
  grande puede no caber; esa clase de trabajo va por Remote Control.
- **Lo que no está pusheado no existe para una sesión cloud**: el VM clona el
  **remoto en tu rama actual**, no tu checkout. Hoy mismo el árbol local tiene
  scripts y recibos de s320/s322 sin commitear que una sesión cloud no vería.
- **Rate limits compartidos** con el resto de tu uso de Claude: varias sesiones
  cloud en paralelo consumen proporcionalmente.
- **Reconciliar al volver a local** (lección s316): tras una tanda de sesiones cloud,
  lo primero es `git fetch` + revisar qué se mergeó. El estado canónico sigue siendo
  el bloque «Estado actual» de `docs/PLAN_RAG_2026.md`.

## 5. Backup lógico del corpus (s319, DEC-209 — correr en LOCAL, no en cloud)

Tras cada lote de ingesta (mínimo: mensual):

```
python scripts/backup_supabase.py --data-root "C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
```

Vuelca la capa corpus/identidad (documents + chunks_v2 + enunciados + hyq, sin
embeddings ni PII) a `<data-root>/backups/<UTC>/` y NO da recibo sin pasar el
drill de restauración (SQLite + counts + FK). Recibo en `evals/`. RPO ≤1 lote;
RTO horas. La capa de datos personales queda FUERA a conciencia (retención RGPD
— DEC-209 [DECIDIR]); el desastre total lo cubre el backup gestionado de
Supabase. Retención de dumps: 3 rotaciones (borrar la más vieja al crear la 4ª).
