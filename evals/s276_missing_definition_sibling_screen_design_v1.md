# S276 — diseño del screen offline `missing-definition-sibling`

**Estado:** congelado antes del GET seed-278. Este artefacto autoriza solo un
screen local determinista; no implementa el mecanismo en runtime, no llama
modelos y no vuelve a medir los seis targets S274.

## Pregunta de decisión

¿Existe suficiente prevalencia fresca y una gramática estructural lo bastante
cerrada para justificar diseñar —con revisión adversarial posterior— una card
default-off que complete un único hermano definicional omitido?

El screen puede responder «la forma existe y el cierre mecánico no cruza los
límites congelados». No puede responder «mejorará respuestas» ni «tiene 0 falsos
positivos semánticos».

## Contrato candidato que se somete al screen

La unidad es un bloque Markdown explícito de entre 2 y 5 ítems top-level:

```text
* Etiqueta alfa: descripción completa

* Etiqueta beta: descripción completa
```

Se exige el mismo marcador, cero indentación, etiqueta y descripción no vacías,
y contigüidad: entre ítems solo puede haber whitespace. Heading, tabla, fence,
blockquote, lista numerada, prosa intermedia, indentación o más de cinco ítems
cortan/rechazan el bloque. La v1 rechaza continuaciones multilínea porque no hay
un límite de registro inequívoco sin un parser Markdown más amplio.

Una card base debe tener receipt exacto contra el padre inmutable. Dentro de un
bloque aceptado:

- todos los ítems salvo uno deben estar intersectados por cards base;
- cada card de soporte debe incluir el inicio del bullet y el `:` de su etiqueta;
- el hermano ausente debe tener cero solape con la vista y medir como máximo 600
  caracteres;
- debe existir exactamente un bloque candidato en el chunk; cualquier ambigüedad
  devuelve cero cards.

El resultado máximo es una card completa en el campo propio
`missing_definition_sibling_cards`, con `local_semantic_validated=false`, span
exacto y rederivación byte-a-byte. No muta `served_coverage_cards`, no hereda la
validación semántica del selector y flag-off es byte-idéntico en la referencia
offline.

## Población fresca y disjunta

- Semilla 278; orden round-robin estratificado por fabricante ya usado por el
  harness S269.
- Primeros 80 documentos de la reserva elegible después de excluir los packets,
  golds y artefactos target-adjacent del builder S269, más todos los documentos
  de las cohortes v1 y seeds 270–277.
- Censo de todos los fragmentos parent de esos 80 documentos; ningún modelo ni
  ranker elige casos.
- Se congelan contenido, spans, hashes, documento y fabricante de cada bloque
  parsable. El hermano omitido se elige por hash(seed, fragment, inicio), no por
  términos de los golds.

## Casos y controles

Por bloque se ejecutan dos positivos de forma:

1. todos los hermanos salvo uno tienen su ítem completo servido;
2. la misma omisión, pero una card hermana termina dentro de la descripción
   después de cubrir bullet+etiqueta (`ítem truncado`).

El resultado solo es correcto si el span emitido coincide exactamente con el
hermano congelado. Se ejecutan además: todos-los-ítems-servidos (clean), heading,
prosa y tabla entre dos definiciones, hermano >600, receipt manipulado y
flag-off. Cualquier card fuera del span hermano cuenta como cross-record FP.

## Gates congelados

- frescura: solape de documentos con v1/seeds270–277 = 0;
- población: ≥60 documentos realmente leídos, ≥20 bloques, ≥10 documentos y ≥3
  fabricantes con bloques elegibles;
- recall de forma full = 100 % y truncada = 100 %;
- 0 clean FP, 0 boundary FP, 0 oversize FP, 0 cross-record FP;
- 0 receipts manipulados aceptados y 0 drift flag-off.

Un único fallo produce `NO_GO_OFFLINE_SCREEN`. Los umbrales miden seguridad de
forma, no relevancia semántica.

## Alternativas descartadas para este screen

- **Expandir el chunk completo:** viola el presupuesto y mezcla colas no
  seleccionadas; no aísla el registro.
- **Lista de términos PEARL/hp017:** target-specific y no escala a fabricantes.
- **Clasificador/LLM de relevancia:** añade coste y convierte un screen $0 en una
  medición semántica no preregistrada.
- **Probe #5 sobre los seis residuales:** cerrado por S274; produciría más
  optimización sobre targets consumidos.
- **Acreditar 98 % por simulación de spans:** el screen no genera respuestas y no
  puede otorgar crédito de conversión.

## Lectura permitida del resultado

`GO_OFFLINE_SCREEN` solo significa: la forma es material en una población fresca
y la referencia cumple los invariantes estructurales congelados. Habilita preparar
un diseño runtime default-off, pasarlo por el dúo adversarial y, si procede, medir
una A/B orgánica/disjunta. No habilita ship, banking ni inferir que la única diana
causal conocida vaya a convertir.

Limitación central: la cohorte se localiza con la misma gramática explícita que se
somete al screen. Por tanto, no mide falsos negativos fuera de esa gramática y sus
«0 FP» son de límite estructural, no una estimación de daño en preguntas reales.
