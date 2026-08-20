# s331 · G1 — replay del hilo real Kidde por brazos (resultado, 20-ago-2026 noche)

> Runner `scripts/s331_gates.py` · recibos `evals/s331_g1_{off,a,af,acf}_v1.json` ·
> ruta de serving REAL (`resolve_conversational_turn` → `run_turn(from_production())`,
> clon de `_process_query`) · presencia pre-condicionada `vigente` por brazo ·
> manifest con git sha + catalog_commit + fingerprint (limitación declarada) + flags.
> **Ventana NO perfecta declarada**: timeouts transitorios del canal CONTENT (Supabase,
> ~22:30-23:00Z) con retry fail-open, estampados en `channel_failures` de cada turno.
> Respuestas LEÍDAS verbatim antes de todo veredicto (regla DEC-092b).

## Veredictos por brazo

| Brazo | Flags | Binding/hint | Servido T3 | Conducta (leída) |
|---|---|---|---|---|
| **off** (paridad prod) | IDENTITY_RESOLVE=on solo | Truncado a `2X-AF1` (reproduce) | **SOLO la datasheet hermana `2x-af1-s-161721-es` (5 chunks)** — manual de familia NO servido | — (baseline del incidente) |
| **a** | +F1_RESOLVE_GOVERNED | **PASS**: T2 bindea `2X-AF1-FB-S`; T3 hint la lleva | **FAIL**: mismo servido que off ⇒ **pérdida de entrada-al-pool** (clase DEC-084) con `allowed_sources` PERFECTO (7 docs familia) | re-pregunta persiste (C off — atribución limpia) |
| **af** | +IDENTITY_FETCH | PASS | **PASS**: 3 manuales de familia servidos (+datasheet) | re-pregunta persiste (C off) |
| **acf** | +F1_MENTION_PRECEDENCE +GENERATOR_NO_REASK | PASS | PASS (mismo servido que af) | **T3: re-ask amnésico ELIMINADO** — acepta familia+FB-S y pregunta el ASPECTO de programación (clarify legítimo). T2: parcial (ver residuales) |

## Los dos hallazgos que el gate cazó (y sus fixes, ya cableados)

1. **Pool-entry loss bajo A-solo** (brazo a): la identidad completa no basta — ni vector
   (query débil «Programación principalmente») ni keyword (tags `product_model`
   compuestos `2X-A/...` no casan con `2X-AF1-FB-S`) meten los docs de familia en el
   top-50; el filtro REPLACE deja el pool en 5 chunks de la datasheet. La whitelist
   protectora no tiene nada que proteger. **Fix = `IDENTITY_FETCH` (seam EXISTENTE,
   s93)**: re-abierto bajo la métrica de HOY (este hilo servido ≠ famtie-39 donde fue
   NO-OP; settled-con-métrica) → af/acf lo miden **GO en esta clase** (el selector
   léxico casa «programación» literalmente — el modo exacto donde s93 fallaba no aplica).
2. **`turn_identity=None` en el flujo principal** (brazo acf, 1ª pasada): M3b pobló la
   identidad solo en los paths de mención y M3c-conducta consumió el canal sin cerrar
   esa población — la rama A y el carry no construían identidad ⇒ `GENERATOR_NO_REASK`
   jamás disparaba. **Fix**: `_build_turn_identity` en A (resolved_this_turn, mixto con
   mención de puerta-1) y en `_carry_forward` (carried) — cazado por el gate, no por la
   suite (95 dirigidos verdes antes Y después: la población es invisible a unit-level).

## G1c (mención fuera de corpus, brazo acf) — el contrato COMPUESTO medido

Con A encendido, el prefijo gobernado de `EMA1224B4RW-XQ` RESUELVE (detect
separator-insensitive) ⇒ standalone con familia `EMA1224B4R/W` + **estado MIXTO**
(`resolved_this_turn` + mención `this_turn`) — el corte-de-ruta queda para la clase
C-sola (ni el detect gobernado casa; brazo `c` pendiente). **La conducta leída es el
contrato de v6 cumplido y mejor que un clarify seco**: reconoce «EMA1224B4RW-XQ no
aparece en mi documentación», nombra la más cercana, pide UNA confirmación dirigida del
sufijo — y AUN ASÍ responde el fallo de tierra con la datasheet servida y el
procedimiento general desde la central. Cero amnesia. Los checks G1c del runner estaban
escritos para el mundo pre-A y marcan FAIL formal: **expectativas a re-escribir por
brazo** (c = corte-de-ruta; acf = contrato compuesto), no defecto del mecanismo.

## Residuales declarados (para G2/G3 y la decisión de ship)

- **T2 conducta parcial**: con fragmentos solo-de-la-S servidos (fetch aún no había
  rellenado en T2), el generador pide confirmación evidencia-vs-contexto en vez de
  declarar alcance («esto es de la S; en tu FB-S puede variar X»). El bloque
  nivel-RESUELTO no cubre el caso «evidencia de OTRA variante hermana» — candidato a
  afinar wording en G3, no re-abre diseño.
- **T3 pregunta el aspecto** en vez de dar overview de programación (155 chunks
  disponibles): clarify legítimo (programación ES amplia) — se observa en G3; no es la
  clase amnésica.
- Latencia af/acf T3 ~27s con retrieve inflado por los timeouts transitorios (~18s
  retrieve incl. retries; rerank 2,4s; generate 6,3s) — re-medir en ventana sana (G2).
- Brazo `c` (route-cut real) y G2/G3/G4 pendientes.

## Qué significa para el ship

La cadena del incidente está ROTA en el brazo paquete: binding → hint → whitelist →
**fetch** → familia servida → conducta sin amnesia. El lote de Railway necesitará
**4 flags** (los 3 de s331 + `IDENTITY_FETCH=on`) — el cuarto entra con este recibo
como evidencia de clase nueva bajo métrica propia (patrón de re-apertura DEC-126
cumplido: evidencia nueva + esta sesión con GO de Alberto).
