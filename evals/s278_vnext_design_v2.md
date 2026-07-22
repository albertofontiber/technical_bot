# s278 — Diseño vNext v2: cerrar los FAIL de la P1 `b92ff51` (POST-dúo r1)

**Estado:** v2 tras adjudicar el dúo r1 (Sol xhigh 8 hallazgos · Fable 14 · adjudicación
`evals/s278_vnext_duo_r1_adjudication_v1.yaml`, todos CONFIRMADOS-o-aceptados, 0 FP). Sustituye a
`s278_vnext_design_v1.md`. Gobernanza DEC-148.

## 0. Criterio de cierre C1 (corrige SEC-29 y ADJUDICADOR)

1. Fixes implementados + suites verdes **con seals históricos re-anclados** (§8 — los 10 seal-tests
   stale se VERSIONAN contra blobs sellados de git, no se relajan; pre-existen en `b92ff51`).
2. Oráculo offline sobre commit limpio: 62/62 PASS + 93/93 checks preservados + FAILs
   postgeneración corregidos (subset §5; los fixes de fuente no son acreditables ahí).
3. **Gate de seguridad TECH_DEBT #29 (stop-line, NO ceremonia):** migración RLS forward-only
   (`chunks_v2_enunciados` + inventario de grants/policies legacy) + smoke del bot. Bloquea el
   merge #184 aunque todo lo demás pase. (El backend usa service_role → el smoke debe ser
   invariante; la exposición confirmada del Advisor es real.)
4. **Pasada de harness pagada (~$3):** los 13 QIDs de la P1 **+ hp009 y hp010 como controles de
   regresión de `replace`** (HP009-E2E: el settled s93/DEC-084 midió "REPLACE regresa hp009" EN
   VIVO — métrica retrieval/famtie, distinta del seam-test; el census no emula fail-open `<3`,
   nivel-2, vector ni reranker, así que el control va en la pasada e2e).
   **Lectura por receipts, no solo texto** (RECEIPTS-LECTURA): verificar CONTEXTO SERVIDO —
   `5b6a3a19` en hp002, chunks MIE-MI-530 en hp018, `b7633e98` en cat017, `f68f2d40` en cat019.
5. **Adjudicador pineado = Alberto** (lee la pasada; pre-screen ciego del dúo si hay REVIEW
   masivo). El autor NO se auto-adjudica FAIL→PASS.
6. Merge #184 = flip Railway (perfil §7). Rollback: `COVERAGE_RELEASE_PROFILE` a su valor previo.

## 1. Identidad determinista (hp018:r1)

### 1a. `replace` + guard candidate-member + QUARANTINE-LIST (corrige GUARD-3FILAS)
- `IDENTITY_RESOLVE_POLICY=replace` con guard estructural: un token solo entra en `drop_tokens`
  si TODOS los miembros de su expansión original son consumibles. Implementación (GUARD-IMPL):
  `Catalog.resolve()` expone `all_members_consumable` (hoy `catalog_store.py:159` filtra los
  candidates ANTES del punto del drop, `catalog_resolver.py:260-263`) — test propio del contrato.
- **Quarantine-list data-side** (`data/catalog/` o config versionada): unidades
  pendientes-de-adjudicación → fail-open-a-add POR UNIDAD. Semilla: las 3 filas del census
  (`umbrella:FAAST` — la cubre también el guard —, `umbrella:ZXR`, `alias:G-100-R`). El guard NO
  cubre ZXR (miembros consumibles; MIE-MI-430 es de zxr4b/5b no-miembros) ni G-100-R (vía alias):
  SIN quarantine habría pérdida real. Se vacía conforme Alberto adjudica.
- Métrica del settled declarada (Protocolo 2 §5): DEC-084 cerró "identidad-en-retrieval EXHAUSTO"
  en métrica famtie con política `add`; hp018:r1 de la P1 es métrica ítems-semánticos de release —
  no se re-litiga DEC-084, se ataca un FAIL nuevo con mecanismo nuevo (drop gobernado).
- Regresiones pineadas intactas: `test_catalog_resolver.py:109,123,208` + nuevas (guard, quarantine).

### 1b. Determinismo/autoridad en `content_search` (corrige LIMIT-ORDER)
- **`order=source_file.asc,page_number.asc,id.asc` SERVER-SIDE** en la request PostgREST
  (`retriever.py:561-566` hoy no pasa `order` → la ventana es plan-dependiente; ordenar client-side
  después NO es determinismo con >LIMIT matches).
- Sobre la ventana determinista: rank de autoridad client-side con `documents.status`
  (active/superseded — YA se consume en `_filter_by_document_status`, `retriever.py:1703-1708`;
  sin DDL) antes del corte final.
- **Residual declarado:** si >LIMIT filas alfabéticamente anteriores, un doc activo puede quedar
  fuera de la ventana (nota: `v.04` ordena antes que `v.07`); mitigación = LIMIT interno mayor +
  el rank de autoridad; el residual se mide en la pasada §0.4, no se promete cero.

## 2. Catálogo INSPIRE (cat017) — SOLO la mitad retrieval

- Gobernar: umbrella `INSPIRE → {e10, e15}` + formas PREFIJADAS (`INSPIRE E10`, `Notifier INSPIRE
  E10`, …) + doc_map al doc `80e1b7d2`. **`E10`/`E15` bare = homonym-candidate fail-open** salvo
  probe de no-colisión (E10-BARE: colisionan con códigos de error/otras superficies).
- La otra mitad (servibilidad del doc bajo snapshot v2) va en §4 — el doc de cat017 TIENE
  lineage con prefijo-backfill + `language`/`doc_type` NULL (CAT017-LINEAGE): gobernar el catálogo
  NO lo hace servible por sí solo.
- **Los 58 aliases indetectables: FUERA del camino crítico C1** (ALIASES-58; 0 de los 29 FAIL
  dependen de ellos; hay superficies basura en la lista elegible). Para C1 solo: round-trip PIN
  que congela la conducta actual + triage de DATOS (re-tipar basura fuera de tipos elegibles).
  La extensión de `_SEP` → workstream post-C1 con eval propio.

## 3. Reserva obligation-aware (hp002) — sin cambios de fondo

Máximo 1 callout de warning, solo preguntas procedimentales/diagnósticas, scope canónico, ANTES
del cap global `MAX_APPENDED=4` (`post_rerank_coverage.py:96`) con presupuesto propio, revalidando
el chunk exacto. Trigger runtime sin QID: patrón code-gated (tipo `_SELECTION_INTENT` DEC-101),
definido en la implementación con sus negativos (no-procedimental, cross-family, hp009).
Flag propio default-off, poseído por el perfil §7.

## 4. Servibilidad/autoridad de documento (cat019 **y cat017**) (corrige CAT017-LINEAGE + SQL-side)

- El RPC `document_local_snapshot_v2` exige `doc_type`/`language` no-vacíos **dentro de SQL**
  (migración `20260722013000`, `identity_complete`) → un verificador Python NO puede aceptar
  honestamente lo que el RPC rechaza. **Fix raíz = data-fix versionado y reversible** (UPDATE de
  los 2 docs: `348c4ec1` cat019 + `80e1b7d2` cat017 — doc_type/language + criterio explícito para
  lineage con prefijo-backfill), con receipt y **visto de Alberto** (mutación live pequeña;
  prod=demo DEC-071e). Antes del UPDATE: probe read-only contando docs que comparten el problema
  (blast-radius visible; si son cientos, se re-plantea como migración de backfill).
- Identidad de blob (`...-c.pdf` vs `...-c`): comparación canónica fail-closed declarada en UN
  sitio + test de tampering (code-side, sin tocar DB).
- Source card de PROSA: span atestado por documento+extracción+source+chunk+content-hash+
  quote-hash/bounds, selección complementaria, nunca QID. Mismo primitivo que §5.

## 5. Evidence Contract v1 (corrige EC-TECHO: techo honesto ~17, tabla por-ítem)

Default-off, byte-inerte off, perfil-owned (§7), sin QID/gold en runtime. Mecánica igual que v1
(ledger de obligaciones desde evidencia servida; pre-writer reserva; post-writer valida cobertura/
cita/contradicción; append EXACTO ligado a fuente o `disclose`/`abstain`; un writer; verifier
`accept|clarify|disclose|abstain`; reusable DEC-136). Cambios v2:

- **Tabla por-ítem ANTES del build** (de los 29): clase `append-alcanzable` / `disclose-alcanzable`
  / `edición-necesaria` / `fuente (§1-§4)`. hp005:r2 (cita inline) y hp011:r1 (retractación de
  semántica errónea) = **edición-necesaria → residual DECLARADO de esta fase** (no se reabre
  S219-221: aquella familia era revisión libre full-answer con 3 regresiones protegidas; aquí NO
  hay reescritura — lo no-alcanzable con append/disclose se declara residual, punto).
  **Techo honesto: ~17/29** con §1-§4 aportando el resto; si la tabla da menos, se declara.
- **Tabla de métricas de settled citados** (Protocolo 2 §5, visible aquí):
  | Settled | Métrica del veredicto | Métrica de HOY | ¿Coinciden? |
  |---|---|---|---|
  | S206 checklist (DEC-118~) | synthesis-miss, 0 ganancias estables +1 regresión | ítems-semánticos P1 | NO — y el mecanismo difiere: S206 guiaba al generador; EC appendea/valida post-writer sin generador |
  | S216 multiwriter | NO-GO de diseño (descomposición question-only) | — | no se reabre: EC no descompone la pregunta; clasifica EVIDENCIA servida |
  | S219-221 revisión full-answer | ganancias con 3 regresiones protegidas | — | no se reabre: EC no reescribe (edición-necesaria = residual) |
  | DEC-134 flags must-preserve | familia de anexo EXHAUSTA (6 residuales, cada fix muerto con métrica) | ítems P1 | PARCIAL — riesgo real de "otro flag de la familia": la diferencia es que EC construye el ledger desde la FUENTE (spans/hashes), no enciende flags existentes; el gate §0.2/0.4 lo falsa si no paga |
- Riesgo declarado (fable#7): la reserva PRE-writer influye al generador (S206-adyacente). Se
  mide por separado en el oráculo (arm sin pre-writer vs con) antes de incluirla; si no paga, EC
  queda solo post-writer.
- Aritmética (hp012 `792`): NO verbatim — obligación `arithmetic` con derivación declarada
  (`4 × (99+99)`, operandos citados de la fuente); si el writer no la produce, el post-writer
  appendea la derivación completa con atribución, no el literal a secas.

## 6. Verificación por tramo

| Tramo | Instrumento | Coste |
|---|---|---|
| §1a/§2 catálogo/resolver (+quarantine) | tests + census re-run offline | $0 |
| §1b orden/autoridad | tests + fixture multi-revisión (v.04/v.07 hp011) | $0 |
| §3/§4 | tests + probes GET read-only + probe blast-radius §4 | ~$0 |
| §5 postgeneración | oráculo offline (62/62+93/93 + FAILs postgen; arm pre-writer aparte) | $0 |
| Fuente e2e + regresión replace | pasada harness 13 QIDs **+ hp009/hp010**, lectura por receipts | ~$3 |
| Seguridad | migración RLS + inventario grants + smoke (gate #29) | $0 |
| Cierre | Alberto adjudica + merge #184 + flip perfil | — |

## 7. Perfil de release vNext (corrige PROFILE-VNEXT)

`coverage_c1_v3` NUEVO y atómico (v1/v2 intocados): posee los flags de c1_v2 + los nuevos
(`EVIDENCE_CONTRACT`, `OBLIGATION_RESERVE_HP002`, `PROSE_SOURCE_CARD`) **y gobierna
`IDENTITY_RESOLVE_POLICY`** (perfil → policy, un solo flip). El contrato valida acoplamientos
(EC requiere MUST_PRESERVE on, etc.). Flip Railway = `COVERAGE_RELEASE_PROFILE=coverage_c1_v3`
+ retirar los flags-hoja legacy (hoy: callout/verb_trigger/MUST_PRESERVE quedan; el contrato
rechaza overrides → checklist de variables exacta en el PR de release).

## 8. Versionado de seals (corrige VERSIONADO-SEALS — mandato DEC-147)

Los 10 seal-tests que fallan (pre-existen en `b92ff51` pristino; clase "drift del working tree
vs prereg sellado") se RE-ANCLAN a los blobs sellados de git de su commit de sello (o a
snapshots congelados versionados) — verifican la INMUTABILIDAD del artefacto histórico, no la
quietud del árbol vivo. Ni se relajan ni se borran. Config de release nueva = v3 con sus propios
hashes.

## 9. Gaps declarados

1. El oráculo no acredita fixes de contexto → pasada harness §0.4 (sin fence; no es P1-réplica).
2. doc_map 861/1014: el guard/quarantine protegen catálogo-side; residual e2e en la pasada.
3. Residual §1b (>LIMIT) y residual EC (edición-necesaria ~2) DECLARADOS, no prometidos a cero.
4. Las 3 filas census + cifra de ledger + visto del data-fix §4 = con Alberto (no bloquean §1a/
   §1b/§3/§5/§7/§8 con quarantine activa).
5. Coste dúo r1 Sol al ledger provisional; Fable corrió in-session ($0 marginal).
