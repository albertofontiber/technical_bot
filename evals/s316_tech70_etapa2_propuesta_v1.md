# s316d — #70 etapa 2: deshacer la conflación compatibilidad ↔ cambio de tema

> ## Corrección post-Sol (ronda 5) — el diseño de abajo está SUPERADO en tres puntos
>
> Sol devolvió 1 crítico + 5 medios; verifiqué los cuatro que cargaban peso **ejecutando**
> y los cuatro eran ciertos:
>
> 1. **CRÍTICO — mi regla soltaba compatibilidad legítima.** `AND NOT adverbio` descarta
>    «¿cómo sé si funciona con Hochiki?» y «¿por qué no conecta con Apollo?»: tienen
>    vocabulario de compatibilidad Y adverbio. Era una regresión, no un riesgo abstracto.
>    **Corregido**: el vocabulario de compatibilidad GANA sobre el adverbio.
> 2. **BLOQUEADOR — `_BRAND_TO_MANUFACTURER` solo conoce 4 marcas** (detnov, notifier,
>    morley, honeywell). `_same_manufacturer('kidde', ('NC-PF2',))` = **False** ⇒ nombrar tu
>    PROPIA marca no se reconoce para 26 de 30 fabricantes. Hoy es inocuo porque la rama
>    arrastra igual; **mi cambio lo habría convertido en un borrado erróneo en 26 marcas**.
>    **Corregido**: la resolución cae al catálogo (`catalog.known_manufacturers()`, 26 marcas,
>    **offline y $0** — verificado), con el dict como seed/alias.
> 3. **La elipsis por longitud (≤4 tokens) tenía falsos positivos**: «¿Morley tiene app?» y
>    «¿Kidde saca nuevos?» son 3 tokens y son temas NUEVOS. Sustituía una conflación por otra.
>    **Corregido**: `continuacion_desnuda` = el turno es SOLO marcador + preposición + marca
>    (`^(y|e|o)?\s*(con|de|para|a|sobre|en)?\s*<marca>$`), que es lo que «¿y con Apollo?» es.
> 4. **Mi «10/10» era falso**: la tabla tenía 9 filas y una («Estoy con una central Morley
>    ZXSe») **ni siquiera ejerce la rama** — `extract_product_models` devuelve `['ZXSE']` y
>    gana la rama A. Conté mal y sobre-afirmé.
>
> **Regla vigente**: `arrastrar ⇔ vocab_compat OR continuacion_desnuda`.
> **Medición nueva: 11/11 casos que SÍ ejercen la rama** (incluidos los 2 contraejemplos
> críticos de Sol y los 2 falsos positivos de longitud), **0 golds alterados**.
>
> Pendientes de Sol NO resueltos, declarados: el léxico es **solo ES** (no cubre EN —
> «And on Morley, how do I reset it?»); y el gate MT **no es fail-closed** (sin
> `CONVERSATION_POLICY=impl` reporta PENDING y sale 0 — mi baseline 48/48 SÍ se corrió con
> la variable puesta, pero hay que pinearlo).

**Qué queda de #70.** La etapa 1 (SHIPPEADA, DEC-198, viva en producción) cerró la causa
(1), ceguera de ruta: un switch EXPLÍCITO («pasemos a Morley») ya no arrastra. Queda la
causa (2), que el testigo `test_testigo_fallthrough_marca_sin_switch_explicito` mantiene
en `xfail(strict)`: **«¿y en Morley cómo se hace el reset?»** sigue arrastrando el producto
Kidde anterior.

**OBJETIVO + MÉTRICA de HOY**: que un turno que nombra OTRA marca y trae su propia pregunta
técnica no siga respondiendo del producto anterior. Gate doble, ambos $0:
`scripts/test_multiturn_vs_gold.py --contract` (**baseline medido hoy: 48/48 PASS, 21
flujos, 13/13 clases**) + el instrumento de transporte (el xfail debe pasar a XPASS).

**LEVER (Protocolo 2 §5)**: no es el lever de identidad-como-recall (SETTLED en
retrieval-miss, DEC-084/091b). Aquí no se añade filtro: se deja de arrastrar uno que el
usuario contradijo. DEC-154 declara que el veredicto respuesta-única NO transfiere a lo
conversacional ⇒ el eje es MT y el eval single-turn medirá **delta 0 por construcción**.

## El mecanismo, verificado en código

`conversation_policy_impl.py:381-410`, rama B. Con marca nombrada, sin token de modelo,
`same_mfr=False` e `in_window=True`, SIEMPRE devuelve
`carry_forward("brand_compatibility_in_window")`. El comentario dice «compatibility
follow-up (e.g. "¿es compatible con Hochiki?")» — correcto para ESA forma, y equivocado
para un cambio de tema. **La rama conflaciona marca-como-diana-de-compatibilidad con
marca-como-ámbito-de-una-pregunta-nueva.**

## Contrato congelado que NO se puede romper (leído, no supuesto)

Gold `mt13_compat_marca`, clase `compatibilidad_marca`, sobre estado CAD-250:
- t2 «¿es compatible con equipos Hochiki?» → `carry_forward` + CAD-250
- t3 «**¿y con Apollo?**» → `carry_forward` + CAD-250 ← **elíptica, SIN vocabulario de
  compatibilidad**. Mata cualquier discriminador basado solo en la palabra «compatible».
- t4 «¿y Detnov fabrica algo con más lazos?» → `carry_forward`. **Exento por construcción**:
  `_same_manufacturer(['detnov'], ('CAD-250',))` = **True** (verificado ejecutando) ⇒ corta
  en `if same_mfr: pass` antes de llegar a la rama que se toca.

## Recomendación: discriminar por INTENCIÓN, con dos señales medidas

Dentro de la rama (marca ajena + sin token de modelo + en ventana), seguir arrastrando
**solo** si el turno es de compatibilidad o elíptico:

```
arrastrar  ⇔  ( vocabulario_compat  OR  elipsis(≤4 tokens) )  AND NOT  adverbio_interrogativo
```

- `vocabulario_compat` = compatib | funciona con | admite | soporta | vale con/para |
  conecta con | encaja con
- `elipsis` = ≤4 tokens de contenido — cubre «¿y con Apollo?» y «¿y Apollo?», que no traen
  pregunta propia sino que continúan la anterior
- `adverbio_interrogativo` = cómo | dónde | cuándo | cuánto | por qué — la marca de que el
  turno trae **su propia** pregunta técnica

Si no se cumple ⇒ cae al `else` que YA existe (`new_brand_no_state`): `STANDALONE` con
`target_models=()`. No se inventa ruta nueva: se reusa la que la propia rama aplica cuando
no hay estado usable, que es exactamente la semántica correcta («marca nombrada, tema
nuevo»).

**Medición previa al diseño (10/10 casos conocidos, 0 golds alterados):**

| turno | arrastra | correcto |
|---|---|---|
| «¿es compatible con equipos Hochiki?» (gold t2) | sí | ✅ |
| «¿y con Apollo?» (gold t3) | sí | ✅ |
| «¿y Apollo?» | sí | ✅ |
| «¿admite detectores Apollo?» | sí | ✅ |
| «¿qué detectores Hochiki son compatibles?» | sí | ✅ |
| **«¿y en Morley cómo se hace el reset?»** (#70) | **no** | ✅ |
| «¿y con Morley cómo se hace el reset?» | no | ✅ |
| «en Morley, ¿cómo se silencia la sirena?» | no | ✅ |
| «Estoy con una central Morley ZXSe» | no | ✅ |

## Alternativas consideradas y descartadas

- **Discriminar por vocabulario de compatibilidad a secas**: lo mata el gold t3 «¿y con
  Apollo?», que no lo tiene. Fue mi primera idea; la descartó el contrato, no yo.
- **Discriminar por la preposición que rige la marca** («con» = compatibilidad, «en» =
  ámbito): lo MEDÍ y produce un falso positivo real — «Estoy con una central Morley ZXSe»
  casa «con … Morley» y arrastraría en un cambio de marca evidente. Retirado por medición.
- **Extender la guardia de la etapa 1** (grupo -1) a este caso: la guardia existe para
  switches EXPLÍCITOS y su calibración es precisión-primero; meterle detección implícita
  la volvería laxa justo donde ya demostró ser peligrosa (`FUEGO`).
- **CLARIFY en vez de STANDALONE** («¿de qué modelo Morley?»): más conservador, pero añade
  un turno de fricción donde el retrieval sin filtro puede responder; y estrena una ruta
  en la rama en vez de reusar la existente.

## Gaps / riesgos declarados

1. **Sigue siendo heurística.** El umbral de elipsis (4 tokens) y la lista de adverbios son
   elecciones, no medidas. Un falso negativo (compatibilidad tratada como switch) pierde
   contexto; un falso positivo (switch tratado como compatibilidad) deja el bug vivo.
   Asimetría asumida: el bug que se arregla es el segundo.
2. **La muestra es pequeña**: 2 golds en la rama + 8 casos construidos por mí. No hay
   consultas reales de producción en esta rama — `query_logs` tiene 68 distintas y ninguna
   la ejerce.
3. **Se toca un clasificador con contrato congelado.** El gate MT (48/48) es la red, pero
   cubre 21 flujos, no el espacio conversacional.
4. **No mide CALIDAD**: que no arrastre no prueba que la respuesta sea mejor. El eje MT de
   Fase 2 sigue siendo otro.
5. **`_matched_brands` usa `BRAND_TOKENS`** (seed), no la lista viva de la DB: una marca
   servida fuera del seed no entra en la rama. Es el mismo gap que la etapa 1 cerró en la
   guardia; aquí queda ABIERTO y declarado.

## Por qué BP + estructural + escalable

- **BP**: se mide ANTES de escribir (10/10 casos, 0 golds alterados, falso positivo propio
  cazado y retirado); reusa la ruta que la rama ya define para «tema nuevo» en vez de
  inventar una; y el gate del contrato existe y está en verde antes de tocar.
- **Estructural**: deshace la CONFLACIÓN en el punto donde se produce, en vez de compensarla
  aguas abajo. La rama pasa a decir lo que de verdad quiere decir.
- **Escalable**: la señal es de intención, no de marca ni de producto, así que no crece con
  el número de fabricantes.
