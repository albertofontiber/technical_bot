# s281 MT-0c — packet de revisión adversarial FOCAL (zona effectively-once)

**Qué se revisa:** la lane MT-0c del build multi-turn Fase 0 — el runtime effectively-once
del lado orquestador, commit `d51792b` (rama `claude/s281-mt0`). Es la pieza que convierte
las 8 RPCs SECURITY DEFINER propuestas por MT-0b en un ciclo de turno idempotente bajo
crashes. La lane quedó WIP-committeada (interrumpida por pausa) con 49 tests verdes; esta
ronda es el dúo focal OBLIGATORIO antes de cerrarla.

## Archivos del diff (todos nuevos)

- `src/orchestrator/convo_store.py` — Protocol `ConvoStore` (8 RPCs) + `ConvoScanner`
  (superficie de lectura del janitor, DIFERIDA: solo la sirve el fake) + cliente
  `PostgRESTConvoStore` (httpx, Accept-Profile/Content-Profile convo; jamás ejercitado
  contra red en tests).
- `src/orchestrator/fake_convo_store.py` — doble sintético in-memory que DECLARA fidelidad
  al bit con el contrato SQL (`supabase/migration_proposals/20260723100001_s281_convo_rpcs_f0.sql`
  + schema hermano `...100000...`); reloj inyectable `ManualClock`.
- `src/orchestrator/lifecycle.py` — driver `run_conversational_turn` (ingress→claim/reclaim→
  run_turn→complete_run→begin_delivery→send fuera de transacción→record_delivery; fail_run
  en excepción y re-raise), poller `deliver_pending`, janitor `reclaim_and_repair` (reclama
  runs huérfanos + sella `sending` atascados). Ventana at-least-once post-send DECLARADA en
  el docstring del módulo.
- `tests/test_convo_store_contract.py` + `tests/test_lifecycle_effectively_once.py` —
  suite de contrato + matriz de crash en las 5 fronteras, concurrencia por interleaving
  determinista (declarado: el fake NO es thread-safe; PTB secuencial en F0).

## Claims de la lane (lo que hay que intentar tumbar)

1. El fake es fiel al contrato SQL al bit (reasons, orden de checks, presupuestos, duplicados).
2. Toda frontera de crash recupera sin doble cómputo visible ni doble entrega, salvo la
   ventana post-send declarada (el usuario puede recibir 2 veces; inherente sin idempotency
   key de Telegram).
3. El fencing garantiza que un worker stale no completa ni publica tras un reclaim.
4. Los duplicados de Telegram producen exactamente una respuesta.
5. Dos conversaciones quedan aisladas; `state_version` es monotónico por conversación.
6. El cliente PostgREST real es viable tal cual contra las RPCs propuestas.

## Contexto canónico

- Diseño: `evals/s280_multiturn_design_v2.md` §1 (effectively-once ÍNTEGRO en F0) + gate de
  Fase 0 (crash en cada frontera + aislamiento de chats).
- Assessment: `evals/s276_multiturn_multihop_architecture_assessment_v1.md` §3.2.
- Conformidad MT-0b: `evals/s281_mt0b_conformance_v1.md` (incluye el janitor de `sending`).
- MT-0a (base sobre la que compone): `src/orchestrator/{contracts,adapters,orchestrator}.py`.

## Qué pedimos

Ataca las 6 claims con ancla fichero:línea y escenario concreto de fallo (inputs/estado →
efecto malo). Presta atención especial a: quién EJECUTA cada ruta de recuperación en
producción real (semántica de redelivery de PTB/Telegram; barridos repetidos del janitor a
lo largo del tiempo; presupuestos de attempts), razas que el interleaving determinista no
cubre pero Postgres real sí permite, y divergencias fake↔SQL que harían que los tests
sintéticos certifiquen un sistema distinto del real. Severidad por hallazgo + veredicto
global (SÓLIDO | SÓLIDO-CON-CAMBIOS | RECHAZAR).
