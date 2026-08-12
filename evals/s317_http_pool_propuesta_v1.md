# s317 — Cliente HTTP compartido de proceso (#72 fase 1 = rapidez fase 2) — propuesta v1 (construida)

Alberto adjudicó el rumbo (12-ago): foco en arquitectura/flujos + velocidad de
respuesta. El perfil v1 (`evals/s317_perfil_retrieval_v1.md`) atribuyó ~10 de los
19 s calientes de retrieval a construir 14 `httpx.Client` POR CONSULTA. Esto está
CONSTRUIDO en el working tree: atacad `src/http_pool.py`, la migración de 55
sitios, `conftest.py` raíz, `tests/test_s317_http_pool.py` y los recibos
v1/v2 del perfil.

## Alcance v1 — SOLO transporte, CERO política (decisión deliberada)

- UN `httpx.Client` por proceso (pool keep-alive 10, expiry 30 s < idle-timeout
  de proxies) y UN contexto SSL. `transport=HTTPTransport(retries=1)` reintenta
  SOLO el connect fallido (una petición ya enviada JAMÁS se reintenta).
- Los timeouts siguen POR SITIO, valor idéntico al que cada sitio declaraba: el
  shim `abierto(timeout=X)` los inyecta por petición. Migración de UN token:
  `with httpx.Client(timeout=X) as client:` → `with abierto(timeout=X) as client:`
  — cuerpos INTACTOS (55 sitios: retriever 29, logging_db 12, catalog_resolver 5,
  deep_lookup/convo_store 2+2, visual_assets/document_local/doc_scoped/shadow/
  supabase_client 1 c/u).
- **La política de reintentos consciente-de-idempotencia (la otra mitad de #72)
  queda FUERA a propósito**: cambia semántica de fallo y exige dúo propio por
  sitio. La v1 no puede cambiar conducta salvo velocidad, por construcción.
- Kill-switch `HTTP_POOL=off` (Railway, sin deploy): cliente fresco POR PETICIÓN
  con la forma de hoy. **Default ON** — argumentado: es infra de transporte, no
  conducta; la casa exige default-off para CONDUCTA, y la paridad medida es
  0-diff (abajo). Si el dúo lo tumba, se invierte el default.

## Testabilidad (la decisión estructural)

La suite ENTERA corre con `HTTP_POOL=off` (conftest.py raíz): los ~20 ficheros
que fingen la red parcheando `httpx.Client` siguen interceptando SIN churn — la
ruta off llama por método nominal con timeout en el constructor, la FORMA
exacta de hoy. Lo que la suite verifica es la EQUIVALENCIA de los 55 sitios.
El pool ON tiene: tests dedicados (singleton, timeout por sitio, no-cierre,
kill-switch, trinquete anti-regresión del patrón viejo) + la MEDICIÓN real.

## Medido (recibos v1 → v2)

- Caliente **19,0 → 4,5 s (−76%)** · fría **53,5 → 12,4 s (−77%)**. Las mismas
  14 peticiones; el residual (4,4 s de ssl.read) es espera genuina de RPCs.
- **Paridad 2×2**: off-vs-on = 0 ids distintos, orden IDÉNTICO; el jitter de
  1 id es ruido base PRE-existente (off-vs-off también lo tiene).
- Proyección sobre la traza real (retrieve 11-27 s/turno): ~3-8 s.

## Alternativas descartadas

1. **Refactor con dedent** (client = pool.client() sin with): blast radius de
   ~60 cuerpos re-indentados; el shim de un-token deja el diff revisable.
2. **Async/httpx.AsyncClient**: el retriever es síncrono por diseño (corre en
   to_thread); async-izar el pipeline es otra obra, no esta.
3. **Retries de petición ahora**: fase 2 de #72, dúo propio (idempotencia no
   universal — un POST de log pudo confirmarse).
4. **Migrar también reingest/extract y dedup_pass**: offline, no pagan por
   turno; fuera del alcance (declarado, no olvidado).

## Gaps declarados

- El camino pool-ON del serving NO corre en CI (la suite va en off): lo cubren
  los tests dedicados del shim + el perfil/paridad en vivo. Coste aceptado para
  no re-escribir 20 ficheros de fakes.
- `keepalive_expiry=30 s` es heurística (idle-timeouts de Supabase/CF no
  documentados públicamente); `retries=1` de connect cubre el caso de conexión
  caducada a mitad.
- Anthropic/Voyage SDKs llevan su propio cliente (ya reutilizado a nivel de
  proceso desde r11/intent y el embedder) — fuera de este alcance.
- El default ON entra en producción CON el merge (Railway redeploy): la mejora
  llega sin paso extra; el kill-switch es la vuelta atrás sin deploy.

## Estado tras el dúo r14 (Sol 5 · Fable 4, convergentes en 1, 0 FP) — TODO APLICADO

- **Sol M1 (verificado ejecutando): los `limits` del cliente eran CÓDIGO MUERTO**
  con un `HTTPTransport` explícito (el transporte conserva sus defaults —
  expiry 5 s, no los 30 prometidos) → `HTTPTransport(limits=_LIMITS)` y el test
  mide el POOL EFECTIVO (`_pool._keepalive_expiry`), no kwargs.
- **Sol M3 + Fable F1: «cero política» era falso y «retries=1 cubre la conexión
  caducada» era técnicamente FALSO** (los retries de transporte solo cubren
  CONNECT; una keep-alive muerta falla al escribir sin reintento) → retries
  RETIRADO del todo (semántica de fallo = la de hoy) y el modo de fallo
  keep-alive-caducada DECLARADO como riesgo residual con su mitigación
  (expiry 30 s), no como «cubierto».
- **Sol M2: el kill-switch no era «la forma de hoy»** (por-petición vs
  por-bloque; los bloques de logging_db/catalog_resolver reutilizan cliente) →
  un cliente fresco POR BLOQUE `with` que se cierra al salir; sin `with`
  (SupabaseHTTP) por-petición, declarado.
- **Sol C1 + M5 ≡ Fable F2: la evidencia n=1 no sostenía «EQUIVALENCIA» ni el
  default ON** → sonda reforzada A/B INTERCALADA (3 queries × 3 reps por modo,
  con jitter base medido en el control off-off) + latencias medianas; recibo v2
  re-estampado con ella. El gap CI-sin-pool-ON sigue DECLARADO (coste aceptado:
  no reescribir 20 ficheros de fakes); mitigación nueva: tests del pool efectivo
  + trinquete estructural. PoolTimeout bajo picos declarado (max_connections 40
  ≈ 3 turnos simultáneos).
- **Fable F3: footgun `timeout=None`** → None jamás se inyecta (manda el
  default 30 s del cliente de proceso), con test.
- **Fable F4: el trinquete solo vigilaba los 10 migrados** → barrido
  ESTRUCTURAL de `src/**/*.py` entero (allowlist = http_pool): un módulo futuro
  no puede reintroducir el patrón sin CI en rojo.
- Colaterales del build cazados por CUATRO tripwires de la casa (no del dúo):
  `http_pool` sellado en el manifest de P1 · `HTTP_POOL` registrado en flags ·
  clasificado en el inventario de entorno de la release-config · y **el serio**:
  el guard PostgREST de P1 (parchea el httpx de 4 módulos SIN tocar el global)
  quedaba ESQUIVADO por el pool — ahora cubre también esa superficie (cierra el
  singleton, fuerza kill-switch en su scope, su httpx es el proxy). Lección:
  un cliente compartido re-rutea superficies que otros aparatos creían locales.
