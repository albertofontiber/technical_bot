# S277 document-local coverage — cierre de evidencia y handoff v5

## Propósito y estado

Este documento consolida la evidencia terminal del mecanismo document-local y
su integración en `coverage_c1_v2`. **No es una quinta revisión adversarial**:
hubo cuatro rondas completas Sol/Fable, todas adjudicadas y cerradas, y no se
lanzó ninguna ronda adicional sobre este packet.

El estado estrecho es:

- mecanismo document-local: `GO_MECHANISM`;
- perfil atómico: `coverage_c1_v2` materializado y preregistrado;
- P1 v2: `PENDING`, no ejecutada;
- release C1: NO-GO mientras no exista `P1_PASS` y siga abierta la deuda de
  seguridad global TECH_DEBT #29;
- KPI oficial: **146/154 = 94,81 %**, sin crédito nuevo;
- multi-turn/multi-hop: `NOT_BUILT`.

## Autoridad v2 aplicada y verificada live

La autoridad positiva ya no depende de una etiqueta legacy de familia. La
tabla gobernada `document_revision_lineages` y
`documents.revision_lineage_id` definen una identidad canónica; una lineage
NULL/no verificada, una cadena incompleta o ramificada, más de una revisión
activa, punteros no recíprocos, un blob activo distinto o un overflow fallan
cerrados.

`evals/s277_document_local_migration_reconciliation_receipt_v2.json` registra
estado `RECONCILED` y **7/7 checks verdaderos**. Las cuatro versiones
document-local constan aplicadas en history:

- `20260721210847` — snapshot inicial;
- `20260721220110` — autoridad de blob exacta;
- `20260722013000` — registry de lineage y snapshot v2;
- `20260722014500` — ACL/RLS mínimos para P1.

La función live `public.document_local_snapshot_v2` es SQL, `STABLE`,
`SECURITY INVOKER`, con `search_path` vacío. Su
`pg_get_functiondef` normalizado a LF tiene SHA-256
`19975e3784e0cd12176cbf0b246c4e0ee8a4eed008de7542d0c6d0b6c0f9a82e`.
`service_role` y `p1_readonly` pueden ejecutarla; PUBLIC/anon/authenticated no.
El rol P1 sólo ve `id` y `authority_status` del registry, bajo RLS que admite
lineages verificadas. La captura no usó `migration repair` ni `--include-all`.

## Mecanismo medido

La secuencia es:

`structural anchor validado → un GET de snapshot atómico → revalidación de
lineage/lifecycle/blob → ranking semántico sin catálogo dentro del blob exacto
→ receipt de una fila Markdown completa → máximo un append`.

`evals/s277_document_local_coverage_probe_v2.json` conserva el veredicto
`GO_MECHANISM` con **22/22 checks** sobre 13 QIDs:

- todos los prefijos permanecen byte-idénticos;
- sólo HP011 alcanza el selector y añade una fila document-local; 12/13 quedan
  fuera por lifecycle o idioma y esa aplicabilidad limitada se reporta;
- el target está ausente de todas las requests y del runtime genérico;
- la fila servida está ligada a la revisión activa v.07, a su lineage y al blob
  exacto, con identidad autoritativa `Notifier / RP1r / usuario`;
- caps por scope y combinado, lifecycle, identidad, SHA/blob, duplicados,
  tampering y formato Markdown tienen controles negativos fail-closed;
- los controles live rechazan tanto un anchor SHA falso como una tsquery
  malformada;
- coste observado: **84 GET, 0 llamadas de modelo y 0 escrituras de base de
  datos**.

El alcance continúa siendo ES-only y limitado a una fila Markdown pipe
completa con separador inmediatamente anterior. No se afirma soporte genérico
de prosa, HTML, registros multilínea o inglés.

## Cuatro rondas Sol/Fable, cerradas

Las cuatro rondas están en `evals/adversarial_review_log.jsonl` con
`duo_status=complete_adjudicated`:

| Ronda | Timestamp Sol | Findings | Confirmados | FP | Cierre principal |
|---|---:|---:|---:|---:|---|
| 1 | `2026-07-21T22:59:27` | 11 | 9 | 2 | snapshot atómico, scopes independientes y alcance ES/Markdown |
| 2 | `2026-07-21T23:33:33` | 10 | 8 | 2 | sentinels `limit+1`, caps, historial y controles SQL live |
| 3 | `2026-07-22T00:09:18` | 9 | 8 | 1 | identidad desde autoridad activa, manifest y bloqueo de writes/modelos |
| 4 | `2026-07-22T01:01:29` | 5 | 5 | 0 | lineage gobernada, cap combinado 64 y framing de aplicabilidad |

Total: **35 findings, 30 confirmados y 5 falsos positivos**. Todos los
confirmados quedaron adjudicados como resueltos antes de cerrar
`GO_MECHANISM`. No hay una quinta revisión pendiente ni fallida.

## Integración en `coverage_c1_v2`

`coverage_c1_v1` permanece inmutable: activa sus cuatro capacidades históricas
y mantiene document-local apagado. `coverage_c1_v2` añade
`DOCUMENT_LOCAL_COVERAGE` como quinta capacidad del perfil y permite sólo las
lanes structural + document-local, con `MUST_PRESERVE_CONTRACT=on` y
`VISUAL_ASSETS_REGISTRY` preservado como opción ortogonal.

La superficie document-local admite como máximo un GET físico a
`/rest/v1/rpc/document_local_snapshot_v2`. Cada réplica v2 debe producir
exactamente una lane trace document-local; `status=error` es NO-GO y
`http_requests` debe corresponder 1:1 con los receipts GET físicos. En
`hp011:r1` y `hp011:r2` se exige además un GET, un único ID seleccionado y ese
ID presente en el contexto servido.

Los artefactos normativos son:

- `evals/s277_c1_p1_design_v2.md`;
- `evals/s277_c1_p1_prereg_v2.yaml`;
- `evals/s277_c1_p1_release_config_schema_v2.json`.

La P1 v2 debe empezar fresca: **27/27 réplicas, 81 delegaciones pagables a modelos y cap
interno de 30 USD** (bound estático 29,727 USD). No puede reanudar ni completar
el run histórico 18/27. Al cierre de este packet no se ha ejecutado ninguna
llamada de esa P1 v2 ni existe `P1_PASS`.

## Límites y siguiente decisión

`GO_MECHANISM` y un eventual `P1_PASS` no bancan facts ni demuestran por sí
solos el objetivo ≥98 %. El marcador sigue en 146/154; los +5 requieren eval
orgánico/fresco u otra familia causal.

TECH_DEBT #29 no bloquea esta medición P1 acotada, pero **sí bloquea merge y
release global**: antes de exponer el candidato deben cerrarse mediante una
migración forward-only el inventario de RLS/grants/policies y sus smokes. Merge,
deploy y canary conservan autorizaciones y gates separados.

La arquitectura multi-turn/multi-hop sigue siendo únicamente el norte de
DEC-136. No existen todavía estado conversacional durable, ingress idempotente,
leases/fencing, outbox ni hops acotados implementados.
