# s317 — Puerta de REVISIÓN de la ingesta (#73) — propuesta v1 (construida)

Cierra TECH_DEBT #73: el dedup por sha256 prueba bytes distintos, no información
nueva — en s316d los 2 candidatos «nuevos» del barrido Casmar eran revisiones
VIEJAS de documentos ya en corpus (INS570-3 vs issue 8; P/N …-03 vs …-04),
cazadas A MANO. El fix está CONSTRUIDO en el working tree (sin commitear):
atacad el código real (`src/reingest/revision_gate.py` + cableado en
`scripts/ingest_new.py::gates` + `tests/test_s317_revision_gate.py` +
`scripts/s317_revision_census.py`).

## Diseño (precisión-primero)

- **Señales de edición $0** (filename + PORTADA vía PyMuPDF, sin LlamaParse),
  en familias muestreadas del corpus REAL (query a `documents` en s317, no
  inventadas): `pn_utc` (P/N con último grupo = revisión, SOLO con el token
  `_rNNN` confirmando el MISMO valor) · `rnnn` (token solo, base = nombre sin
  él) · `issue` (Notifier/Morley + INSxxx-N) · `rev` numérica y letra (NUNCA
  comparadas entre sí) · `fecha` AAAAMM (portal Casmar) · `v` (vN-NN).
- **Idioma = identidad**: los tokens es/en/pt/ml… quedan EN la base — una
  edición ES jamás supersede a la PT (real: 4188-1124-ES issue 6 convive con
  -PT issue 4). Las RACHAS de fecha se podan de la base (en Notifier la fecha
  cambia con cada issue; sin la poda dos issues no compartirían base).
- **Cruce corpus-wide** contra `documents` activos con fetch PAGINADO
  (PostgREST corta a 1000 en silencio — clase #72; `documents` = 1.069 filas).
  Índice = revisión MÁXIMA por (base, formato).
- **Veredictos**: BLOQUEADO (corpus > candidata; se excluye del lote, motivo
  con el fichero vigente) · SUPERSEDE (candidata > corpus; procede + anotada
  como candidata a cadena #4) · NO_COMPARABLE (misma revisión bytes distintos,
  o aridad distinta; procede LISTADA) · SIN_SENAL (fail-open declarado del
  TECH_DEBT: procede, listada como «edición no verificable» en el dry).
- **Conflictos no bloquean**: filename vs portada con valores distintos para la
  misma (base, formato) → la señal se retira; P/N que contradice a su `_rNNN`
  → ni pn_utc ni rnnn se afirman.
- **Override consciente**: `--ignorar-revision` (ingesta adjudicada de una
  revisión vieja), ruidoso en el informe.

## Validación ya ejecutada

- **Batería 23/23** (`tests/test_s317_revision_gate.py`): los DOS fallos reales
  de s316d reproducidos y BLOQUEADOS (el INS570-3 solo detectable por PORTADA);
  dirección SUPERSEDE; idioma no cruza; fecha con poda de rachas; letra A<B;
  misma-revisión-bytes-distintos NO bloquea; 7 trampas de FP reales del corpus
  (ms1-2-4, 18-187110-10, EN54-20, «revisar», P/N sin _rNNN…) en SIN_SENAL.
- **Censo sobre el corpus REAL** (`evals/s317_revision_census_v1.json`): 1.069
  activos paginados · 134 con señal (13%) · **exactamente 1 par multi-revisión
  activo** (MI_KIDDE_KE_DP312x_SNx 202503/202512 — deuda #4 REAL, va a
  adjudicación de Alberto) · **0 pares falsos** sobre 1.069 nombres.

## Alternativas descartadas

1. **Comparar por `document_family`** (columna existente): su normalización
   solo poda fechas/hash — dos revisiones con `_rNNN` o `issue` distinto NO
   comparten familia hoy; la puerta necesita extracción propia por formato.
2. **Bloquear también sin señal comparable** (fail-closed total): el 87% de los
   nombres activos no emite señal — bloquearía lotes enteros legítimos. El
   TECH_DEBT ya predeclaró fail-open-listado para ese caso.
3. **LLM para leer la portada**: coste por candidato y no determinista; las
   señales ancladas cubren los casos reales conocidos y el residuo queda
   LISTADO para ojo humano (el dry-run es el punto de control existente).
4. **Poblar `supersedes_id` automáticamente** (cadena #4): escritura en
   `documents` fuera del alcance del gate de ingesta; el recibo anota las
   candidatas y la cadena se decide con Alberto.

## Gaps declarados

- Cobertura de señal = 13% de los nombres activos (los 87% restantes: fail-open
  LISTADO, nunca silencioso). La cobertura sobre CANDIDATOS nuevos será mayor
  (portal Casmar trae fecha AAAAMM sistemática; UTC trae _rNNN), pero no está
  medida.
- Revisiones raras se pierden a propósito (precisión): `RevIMarch2016` (letra
  pegada a palabra), `0044-055-02` (P/N sin _rNNN), `Issue 0165-02 v2` mixto.
- La portada solo se lee en el CANDIDATO (las de los 1.069 del corpus no están
  a mano); el índice del corpus es solo-filename.
- El par vivo 202503/202512 NO se toca aquí (adjudicación de Alberto: marcar
  supersedida la 202503).
- `senales_de_portada` recorta a 2.000 chars — una portada-índice muy larga
  podría dejar la señal fuera (no observado en los casos reales).

## Estado tras el dúo r13 (Sol 8 · Fable 7, convergentes en 3, 0 FP) — TODO APLICADO en v1.1

- **Sol C1 ≡ Fable F2 (crítico): ceguera INTRA-LOTE** → doble cruce en `gates()`:
  corpus (igualdad BLOQUEA, contrato >=) + resto del lote (igualdad degrada a
  revisión-a-mano — dos candidatos iguales no se excluyen mutuamente).
- **Sol C2 (crítico): la señal no se persistía** → se escribe en
  `documents.revision`/`revision_date` (las columnas de migrations/001, siempre
  NULL hasta hoy) con forma serializada parseable; `indice_corpus` lee filename
  + columna — una revisión solo-detectable-por-portada sigue visible para
  lotes futuros. Roundtrip testeado.
- **Fable F1 (medio, probado): la fecha contaminaba la TUPLA de revisión**
  («rev 4 30-10-2024» → rev=(4,30,10), comparaba DÍAS) → extracción sobre
  CRUDO con continuación multi-parte SOLO por `.`/`_` (las revisiones reales:
  «Rev 3.2», «rev1_1_4»; las fechas usan espacio/guión) y el valor excindido
  ANTES de la poda de fechas. Colateral cazado al testear: `\b` no funciona en
  crudo (el `_` es \w) → prefijos de separador explícitos.
- **Sol M2 ≡ Fable F5: contrato #73 LITERAL** → corpus >= candidata ⇒ BLOQUEADO
  (la misma-revisión-bytes-distintos ya no pasa; el override existe para el
  caso adjudicado).
- **Sol M4 ≡ Fable F7: índice con TODAS las revisiones** por (base, formato) —
  la máxima de la MISMA aridad decide; ya no depende del orden de llegada.
- **Sol M1: idioma** → si la base existe con `language` distinto en documents ⇒
  NO_COMPARABLE (jamás bloqueo a ciegas); el lookup canónico completo
  (manufacturer, family, language) queda como límite declarado.
- **Sol M5: override auditable** → `--ignorar-revision [GLOB]` por fichero;
  veredicto + ignorada en candidato, resultados y recibo de commit.
- **Sol M6: `ISS 07NOV23`** → familia `iss_fecha` (ddMMMyy) implementada.
- **Fable F3/F4: portada acotada** → SOLO familia INS (span-independiente),
  recorte a 600 chars (zona de título) + guarda anti-cita («ver INS570-2» de
  un hermano no dispara; 329 remisiones internas en el censo s294).
- **Fable F6: años ≤2019** podan de la base.
- **Sol M3 ≡ Fable F2b (framing)**: el censo ya no afirma «0 pares falsos»
  absoluto ni «la puerta lo habría bloqueado» incondicional — cobertura
  inter-familia declarada ciega (par conocido MI-Casmar↔bcn, DEC-192) y la
  dirección vieja-primero sigue siendo trabajo de la cadena #4.
- Batería 23→35 tests; censo re-corrido con v1.1: 134/1069 con señal, mismo
  único par intra-familia detectado.
