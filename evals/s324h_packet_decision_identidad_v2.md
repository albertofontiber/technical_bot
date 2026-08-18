# Packet v2 — DOS fallos que la v1 confundía en uno

> **Corrección tras el pushback de Alberto (18-ago).** La v1 de este packet presentaba
> un único fail-closed —«no he podido comprobar la marca, reintenta»— como *la*
> solución. Alberto lo rechazó: *«no es un problema de "estoy saturado, inténtalo de
> nuevo más tarde", sino de "no te he entendido"»*. Medido: **tiene razón, y son dos
> fallos distintos con causas, frecuencias y remedios distintos.** La v1 empaquetó el
> raro y se olvidó del frecuente.

---

## La medición que separa los casos

Plan planificado para la misma frase con la marca escrita de cuatro maneras
(`Meta(fuente="voz")`, léxico de marcas servidas = {detnov, notifier, aguilera}):

```
«qué centrales de Detnov tienes»       -> inventario        datos={'marca':'Detnov', ...}
«qué centrales de Death Knife tienes»  -> conversacional    datos={}
«qué centrales de Death Knob tienes»   -> conversacional    datos={}
«qué centrales de Bosch tienes»        -> marca_no_servida  datos={'marca_mencionada':'Bosch'}
«qué centrales de xkjdfh tienes»       -> conversacional    datos={}
```

**Lo que esto dice:** el bot YA distingue «esa marca existe pero no la sirvo»
(`marca_no_servida`, mensaje honesto). Lo que NO tiene es una salida para «esa palabra
no la reconozco»: cae a `conversacional`, el RAG no encuentra nada, y responde **«No he
encontrado información relevante en los manuales disponibles»** — que le dice al técnico
que *no hay documentación* cuando lo que ha pasado es que *no se entendió la palabra*.

Es el mensaje de la captura de Alberto. Y «Death Knife» / «Death Knob» no son ejemplos
inventados: son las dos transcripciones reales que dio Whisper para «Detnov» esta semana.

---

## Fallo B — «no te he entendido» (el de Alberto)

| | |
|---|---|
| **Causa** | El ASR devuelve una palabra que no es ninguna marca conocida |
| **Frecuencia** | **Alta y estructural** en voz. Los nombres de marca son el punto débil del ASR y los técnicos no hablan inglés (frase de Alberto). Ya ha ocurrido dos veces esta semana |
| **Qué contesta hoy** | «No he encontrado información relevante en los manuales disponibles» — **engañoso**: afirma un hueco de corpus que no existe |
| **¿Lo crea el cableado?** | **No.** Existe hoy y seguirá existiendo después. Es independiente de s324h |
| **Coste de no arreglarlo** | El técnico concluye que el bot no tiene su marca. Es la respuesta que hunde la confianza en la primera sesión, y no hay forma de que él sepa que fue un problema de audio |

**Forma del arreglo (a diseñar, no decidido):** cuando el turno viene de voz, la pregunta
tiene forma de consulta sobre una marca, y **no** se reconoce ninguna marca en el texto,
decir lo que de verdad pasa y dar la salida útil. Algo del estilo:

> No he reconocido la marca en el audio (he oído «Death Knife»). ¿Puedes repetirla o
> escribirla? Tengo documentación de 30 fabricantes.

Dos propiedades que lo hacen honesto: **cita lo que oyó** —así el técnico ve el problema
en un vistazo— y **no afirma nada sobre el corpus**.

**Riesgo obvio que hay que medir antes de cablear:** el falso positivo. Una pregunta
técnica legítima sin marca («¿cómo se conecta un lazo?») no puede acabar aquí. El
predicado tiene que exigir *forma de consulta de marca* + *cero marcas reconocidas*, y
hay que medirlo contra los golds antes de dar por bueno el disparo.

## Fallo A — «no he podido comprobar la marca» (el mío)

| | |
|---|---|
| **Causa** | `lookup_model_manufacturer` / `manufacturer_in_db` hacen `raise_for_status()`: un blip de Supabase lanza |
| **Frecuencia** | **Baja.** Requiere fallo de red o de la base |
| **Qué contesta hoy en VOZ** | Nada: hoy la voz no ejecuta esas consultas |
| **¿Lo crea el cableado?** | **Sí.** Aparece por hacer pasar la voz por el plan |
| **Salidas** | (a) degradar al RAG → riesgo **cross-brand**, muerta por Sol r43; (b) que suba el error → la voz pierde respuestas que hoy da, muerta por Sol y Opus 5 r44; (c) mensaje honesto de reintento |

---

## Lo que propongo, y lo que le toca al dúo

**Los dos fallos son reales y ninguno tapa al otro.** Pero no valen lo mismo:

- **B es el trabajo valioso** y es **independiente de s324h**: se puede diseñar, medir y
  cablear por su cuenta, y arregla algo que le pasa a Alberto hoy.
- **A es una consecuencia del cableado** y hay que resolverlo para poder cablear, aunque
  sea raro. La opción (c) sigue siendo la menos mala de las tres medidas: las otras dos
  están descartadas por el dúo por seguridad y por regresión.

**Preguntas concretas para el dúo** (no «revisad el packet»):

1. **¿Es B separable de s324h, o hay una razón estructural para que viajen juntos?**
   Si el predicado de B vive en el plan, quizá el sitio natural es el mismo lote.
2. **El predicado de B: ¿cómo se acota el falso positivo?** ¿Qué señal distingue «marca
   no reconocida» de «pregunta técnica sin marca»? ¿Y qué mide que el disparo no se coma
   preguntas legítimas?
3. **¿Debe B mostrar lo que se oyó?** Citar «Death Knife» ayuda al técnico, pero el ASR
   crudo puede traer cualquier cosa: ¿hay riesgo de eco, o de reproducir algo que no
   debería volver al chat?
4. **B por texto: ¿aplica?** Si alguien teclea «centrales de Detnof», el bot dice hoy lo
   mismo de siempre. ¿Es el mismo fallo o son dos?
5. **¿Sigue siendo (c) la salida de A**, o hay una cuarta que ninguno de los tres
   revisores ha propuesto?

---

## Adjudicación registrada — pin del 2º revisor

**Alberto (18-ago): el 2º revisor sigue siendo Fable 5, aunque el autor corra en el
mismo modelo.** Motivo dado: *«tiene otro enfoque i.e. de adversarial»* — el rol y el
briefing cambian el comportamiento, no sólo el modelo. Acatado; el pin canónico se
mantiene y el refuerzo Opus 5 de la r44 queda como lo que fue, un refuerzo declarado y
no un cambio de contrato.

**Lo que esa decisión NO resuelve, y ahora urge más:** en r43 y r44 el runner de Fable
marcó `tools_reales=0` y en r44 detectó **transcripción fabricada** (texto que aparenta
un log de `read_file`/`grep_repo` sin bloques `tool_use` reales). Si Fable es el pin
definitivo, un revisor que opina **a ciegas creyendo haber leído el repo** es peor que
uno ausente: sus claims suenan ancladas y no lo están. Arreglarlo pasa de deuda a
prerrequisito del Protocolo 3 (TECH_DEBT #86bis).
