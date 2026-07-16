# S117 M2.5 — addendum de unicidad inversa y reconciliación semántica v3

Este addendum conserva íntegramente el binding primario y la precedencia forward
de v2. Cierra los huecos encontrados por la revisión adversarial antes de
ejecutar ninguna proyección sembrada.

## Unicidad inversa fail-closed

Después de clasificar cada raw con la precedencia de v2, se aplica una segunda
regla global y agnóstica al fabricante: cada `document_id` candidato debe estar
asociado a exactamente un `extraction_sha256` raw dentro de los bindings
provisionalmente seguros.

Si dos o más raws apuntan al mismo `document_id`, todos caen en
`fallback_shared_document_id_across_extractions`. No se crea alias para ninguno
de ellos. El terminal conserva como diagnóstico el ID observado y la lista
ordenada de SHA en colisión, pero su `document_id` autorizable es `null`.

Esta regla evita afirmar que un único documento legacy está ligado
criptográficamente a dos extracciones distintas. No contiene excepciones por
fabricante, producto, nombre de fichero o posición en el corpus.

## Evidencia congelable del snapshot M2

La aplicación de la regla general al snapshot ya congelado produce:

- 596 candidatos forward `backfill`, 593 IDs distintos;
- tres IDs compartidos por seis raws y 144 filas legacy;
- 590 raws seguros con 16.396 filas legacy;
- 19.572 filas locales de esos 590 raws, de las que 16.894 son policy-eligible
  y 2.678 quedan excluidas por idioma.

Estos conteos son expectativas del probe sobre este snapshot, no condiciones de
la lógica productiva. Se preregistran para impedir que un no-op o una deriva del
corpus pueda recibir GO.

## Preservación del snapshot

La proyección derivada debe demostrar por lectura posterior que:

1. todos los chunks originales son byte-lógicamente idénticos y conservan su
   orden y cardinalidad;
2. todos los documentos originales son byte-lógicamente idénticos y conservan
   su orden y cardinalidad;
3. las únicas filas añadidas son exactamente los 590 aliases seguros;
4. el snapshot fuente conserva sus hashes gzip y JSONL congelados.

El snapshot derivado sigue siendo un artefacto analítico local. No modela una
escritura autorizada en `documents` ni concede GO de schema, load o serving.

## Reconciliación exacta upstream → downstream

Sea `E = 16.894`, el número preregistrado de filas locales policy-eligible de la
cohorte segura. Frente al baseline M2 exacto, la proyección debe cumplir:

- `total_local` y `policy_eligible`: delta cero;
- `target_document_unresolved`: `-E`;
- `target_document_resolved`, `target_document_active` y `extraction_hit`: `+E`;
- exclusiones de policy, `document_status_excluded` y `no_extraction_donor`:
  delta cero;
- todos los deltas de terminales downstream son no negativos y suman `E`;
- cada escalón del funnel reconcilia exactamente con su terminal de caída:
  content, structure, metadata, uniqueness, context y embedding.

Así, M2.5 solo puede recibir GO si demuestra que ha resuelto exactamente la
fase documental de la cohorte autorizada y que las mismas filas se han
redistribuido, sin desaparecer, hacia las fases downstream.

## Semántica de GO

`status=GO` se deriva exclusivamente de `all(checks.values())`. GO significa:

- proyección local determinista e internamente válida;
- línea base primaria y análisis M2 originales invariantes;
- efecto documental exacto y auditable;
- cero DB, red, modelos o vectores.

GO no significa reuse admitido, mejora causal de facts OK, ni autorización de
migración, carga o despliegue. Solo habilita diseñar la siguiente validación
independiente del binding.
