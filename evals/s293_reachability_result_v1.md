# s293 · Sonda de ALCANZABILIDAD sobre la cola de síntesis — 2 levers confirmados, 2 muertos

> ⚠️ **SUPERSEDIDO EN PARTE (s321) — este documento sigue titulando «2 muertos» y ESO YA NO ES
> CIERTO.** Los dos «NO alcanzable» de la tabla han caído:
> - **`hp017#2`**: su fila dice «pre-guard (DEC-172)» — y eso NO es una medición de alcanzabilidad
>   (sin inyección, sin ids admitidos). La **primera sonda real** es de s321:
>   `evals/s293_reachability_hp017_hp017_2.json` → base 0/5 → **oráculo 5/5 en 3/3**, `alcanzable: true`.
> - **`hp011#2`**: su 0/5 era medición VÁLIDA del 2-ago y ha **caducado** — s320c da los tres brazos
>   alcanzables (6/15 firmes: alcanzable pero inestable).
>
> Los dos **ALCANZABLE** (`cat017#2`, `hp003#4`) no se cuestionan. El **procedimiento** de la sonda
> sigue siendo el canónico (CLAUDE.md, Protocolo 4), con la salvedad de que **aún no está endurecido
> para emitir un NO**: falta prueba de entrega obligatoria y sellado de freeze-contract completo.
> Detalle y adjudicación: banners de **DEC-173 / DEC-175** y `docs/LEVER_DIGEST.md`.


**Qué es.** Antes de diseñar un lever de serving/síntesis, medir si el hecho-diana transmitiría
**con la evidencia ideal ya delante del modelo**. Si no transmite ni así, ningún lever de
serving puede pagarlo. Generaliza lo que en esta misma sesión mató el lever A (DEC-172,
lección #58). Instrumento: `scripts/s293_reachability_probe.py`.

**Vara.** Juez canónico `judge_conveyed21` (K=5, `THRESH_FIRM=4`) — la métrica del objetivo,
no un regex propio. **Brazos.** `base` (turno real por el seam del harness, flags-demo) vs
`oracle`:
- modo **`serve`** — el carrier del dato NO se sirve ⇒ se inyecta en la vista del generador
  (fila real de DB, `similarity` al máximo de las servidas). Pregunta: «¿y si el modelo lo
  hubiera visto?», no «¿por qué lane entraría?».
- modo **`appendix`** — el carrier YA se sirve y el modelo lo omite ⇒ se simula el apéndice
  determinista añadiendo el span VERBATIM con su cita (formato `must_preserve.render_appendix`).

## Resultados (N=3 por hecho, `THRESH_FIRM=4`)

| hecho | modo | base | oráculo | veredicto | lectura |
|---|---|---|---|---|---|
| **cat017#2** licencia CLIP por lazo | serve (`4c186fb2`) | 0/5 | **5/5 · 3/3** | **ALCANZABLE** | servir el carrier convierte el hecho. El lever B (referencia gobernada) tiene retorno garantizado de +1 hecho |
| **hp003#4** magnetotérmico | appendix (span mandatorio) | 0/5 (**1 de 3 dio 5/5**) | **5/5 · 3/3** | **ALCANZABLE** | el apéndice lo convierte de forma estable. Caveat: el «stable-miss» del recibo NO es estable con composición fresca |
| **hp011#2** t.A 05 a 295 seg | serve (label + valor) | 0/5 | **0/5 · 3/3** | **NO alcanzable** | con AMBAS mitades admitidas la respuesta ni menciona el «295»: el modelo tiene el dato y contesta con otro parámetro (`r.i`). **La pair-completion que s292 iba a diseñar NO pagaría** |
| **hp017#2** Editar Configuración | pre-guard (DEC-172) | 0/5 | máx **3/5** | **NO alcanzable** | falta la mitad «borrar la Regla 1», que el modelo no escribe |

Recibos: `s293_reachability_cat017_cat017_2.json` · `s293_reachability_hp003_hp003_4.json` ·
`s293_reachability_hp011_hp011_2.json` · `s293_hp017_conveyed_preguard_v1.json`.

## Regla-C sobre esta sonda (3 fallos propios cazados antes de reportar)

1. **hp011#2, oráculo INCOMPLETO**: la v1 inyectaba solo el chunk de la etiqueta; el del valor
   no estaba servido en esos turnos ⇒ el 0/5 no probaba la hipótesis. Corregido inyectando
   **ambas** mitades y verificando en la respuesta que el modelo las tenía delante.
2. **hp011#2, carrier EQUIVOCADO**: el censo de s292 daba `4581dc4b` («idx 75») como portador
   del label `t.A`; **no lo contiene**. El documento tiene `chunk_index` DUPLICADOS y el
   portador real es `f18362c6` (mismo idx 75, otro chunk). Sin verificarlo, la sonda habría
   dado un «no alcanzable» falso por inyectar el gemelo equivocado.
3. **hp003#4, patrón CIEGO**: el manual de la CAD-150 escribe «magneto térmico» **con
   espacio**, así que `/magnetot/` no encontró el span y la sonda abortó — con la falsa
   apariencia de «el corpus no lo tiene». El span existe y está SERVIDO (`eaa39792`, p.8,
   §2.3): «Desconecte siempre la magneto térmico bipolar exterior antes de manipular la
   central.» (`feedback_corpus_gap` otra vez en lo cierto: el hueco era mío.)

## Limitaciones declaradas

- N=3 por hecho: suficiente para separar 5/5 de 0/5, insuficiente para estimar tasas finas.
- El oráculo `serve` eleva `similarity` para forzar la admisión: mide «si lo viera», no la
  viabilidad de la lane que lo traería (esa es la pregunta del diseño, no de la sonda).
- El oráculo `appendix` reproduce el formato del apéndice, no su selección: dice que el span
  BASTA, no que el lever lo elegiría.
- Un «alcanzable» NO es un GO: dice que el techo no está en el hecho. El diseño del lever
  sigue necesitando dúo, flag-off y su propio gate.
