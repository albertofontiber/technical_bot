# s286 — Diseño de la limpieza de tachados `~~` + patch P2 (lane #5, adjudicación de Alberto)

## OBJETIVO + MÉTRICA
Eliminar del corpus servible la superficie corrupta `~~texto~~` (énfasis del PDF mal renderizado
como tachado — adjudicado por Alberto en las 3 clases, packet s285 con sus marcas; clase 3
verificada por arrastre LQAS n=12, 0 defectos, muestra en este brief §D) y patchear el chunk P2
`2113ac69` al píxel. MÉTRICA: hp011 re-traza K=3 sin artefactos t.Fi/ri-corrupto + 0 pares `~~`
residuales fuera de literales + no-regresión smoke en hp002/cat018/hp011. NO toca levers settled
(la política struck-OCR del EC queda como red para OCR real; su clase objetivo se encoge —
interacción declarada §F).

## A — TRANSFORMACIÓN DETERMINISTA (tokenizador de runs, NO regex simple)
Por cada línea del content (fences INCLUIDOS — evidencia §C):
1. Tokenizar runs de tildes: run de **exactamente 2** = marcador toggle; run de **exactamente
   4** = cierre+apertura adyacentes (caso AgileIQ `~~Retirado del~~~~servicio~~`); run de **3 o
   ≥5** = LITERAL intocable (arte ASCII del raíl CAD-201 `~~~~~~~~~~~`, subrayados-puntero CBE
   del AM-8200 `~~~~~~~~~~`).
2. Emparejar marcadores por línea (sin pares cross-línea); pares → retirar marcas CONSERVANDO
   el texto; marcador huérfano → se DEJA tal cual y se cuenta (4 chunks con conteo impar
   inventariados).
3. Idempotente: segunda pasada = 0 cambios (guard del applier).

## B — ALCANCE E INVENTARIO (en vivo, 29-jul)
840 chunks con `~~` (831 active + 9 no-active — se limpian TODOS por higiene, con conteo por
status declarado); ~150 docs, todas las marcas. 84 chunks con marcas dentro de tablas markdown
(strip seguro en celdas). El applier congela el inventario exacto (ids+sha256 de content antes)
como manifest.

## C — EVIDENCIA DE LOS CASOS-BORDE (leída en DB, ids en el applier)
- CAD-201 p18: `•~~~~~~~~~~~•` = dibujo del terminal (run 11 → literal ✓).
- AM-8200N p65/66: `~~~~~~~~~~` subrayando la expresión CBE prohibida (run 10 → literal ✓).
- AgileIQ p26: `F[~~Retirado del~~~~servicio~~…]` dentro de mermaid (pares + run-4 → SE limpia ✓).
- Kidde p127: `~~<ins>firesecurityproducts.com</ins>~~` (doble marca: strip deja el <ins>
  correcto ✓). MIE-MI-580 p14: `~~3000 µA~~` = numerador de fórmula subrayado (strip conserva
  el valor ✓).

## D — CLASE 3 POR ARRASTRE (pre-aprobada por Alberto) — LQAS n=12 seed=md5-order, 0 defectos
12/12 = énfasis (7 headings, 3 links, 1 header de tabla, 1 numerador de fórmula); 0 tachado
editorial real. Ids en `evals/s286_tachados_lqas_c3_v1.json` (los 12 de la consulta sellada).

## E — PATCH P2 `2113ac69` (HLSI-MA-103 p2) — AL PÍXEL (render leído: evals/s286_renders/HLSI-MA-103_p002.png)
Correcciones verificadas contra la página real (todas con el pixel delante):
1. «ri - **Resumen** inhibido» → «r.I - **Rearme** inhibido tras extinción»; apartado **4.12.2**
   (el chunk dice 4.1.2).
2. **Tabla r.I real** (el chunk tiene 3 filas duplicadas/contradictorias e INVIERTE el default):
   `- -` = Rearme inhibido hasta finalizar extinción o agotado tiempo configurado en t.A
   (t.A→0 seg.) · `00` = **Rearme permitido en cualquier momento (POR DEFECTO)** · `De 01 a 30`
   = Rearme inhibido durante intervalo definido (minutos). [El default corrupto del chunk decía
   00=inhibido — inversión con relevancia operativa.]
3. «rS - Retardo de Sirenas»: rango real **00 a 10 min** (defecto 00 min); el chunk dice
   «01 a 30» (contaminado por r.I).
4. «FE - Nivel fallo de tierra» → «**F.t** - Nivel fallo de tierra» (F.E es Repetición de
   extinción, p1 — colisión de etiquetas).
5. Nota final galimatías → nota real: «Con la central en modo de programación (nivel 3), para
   identificar si los caracteres del display LED de 7 segmentos representan un parámetro o un
   valor se utiliza, en el primer caso, un punto intermitente entre ambos dígitos.»
El patch es un REPLACE de content del chunk con before-image; texto propuesto completo en el
applier (revisable en el dúo).

## F — RE-EMBED + INTERACCIONES
- Los 841 contents cambiados (840 strip + P2; solapan) → **re-embed voyage-4-large** replicando
  EXACTAMENTE la construcción de input de `src/reingest/embed.py` (content + blurb contextual
  B7; verificar en build). Coste ~$0,10. Sin re-embed quedaría mismatch content↔vector.
- hyq/enunciados: sus embeddings son de PREGUNTAS/enunciados (no del content) → intactos;
  surrogates que CITEN texto con `~~`… verificación en build (grep en tablas hyq/enunciados; si
  hay, se listan y limpian igual con su propio manifest).
- STRUCK_OCR_CONTEXT (s283 P1, flag-off) y política struck-OCR del EC: clase objetivo se encoge
  a OCR-tachado real remanente; sin cambio de código.

## G — CEREMONIA DE APLICACIÓN (stop-line respetada)
1. Applier python genera: manifest (ids + sha antes/después + conteos por clase) + **SQL de
   content para el paste de Alberto** (staging + guards de conteo exacto + before-image a tabla
   `_s286_tachados_backup` persistente + rollback documentado) — el cambio SEMÁNTICO lo gatea él.
2. Tras su «ejecutado»: YO corro el re-embed (dato DERIVADO mecánico del content adjudicado)
   sobre los ids del manifest, con verificación 1:1 posterior (dims, no-nulls, conteo).
3. Verificación: 0 pares residuales · idempotencia · hp011 re-traza K=3 · smoke hp002/cat018 ·
   LQAS post-apply n=12 sobre la clase 3 limpiada.

## ALTERNATIVAS DESCARTADAS
- Regex simple `~~(.+?)~~`: rompe el arte ASCII y los subrayados-puntero (§C) — por eso el
  tokenizador de runs.
- Excluir fences del strip: dejaría el mermaid de AgileIQ corrupto (§C).
- No re-embed: mismatch content↔vector en 841 chunks servibles — deuda invisible.
- Re-render completo desde PDF (pipeline reingest): coste/riesgo desproporcionado para una
  transformación puntual reversible; el strip es determinista y auditable char-a-char.

## GAPS DECLARADOS
- El strip pierde la SEMÁNTICA de énfasis (el «no» enfatizado queda como texto plano) — pérdida
  aceptada: era ruido de render, el énfasis no es contrato.
- 4 huérfanos `~~` se quedan (declarados, no adivinamos su intención).
- El patch P2 corrige UN chunk; la página p2 tiene más chunks hermanos — se auditan en build
  (grep resto de chunks de HLSI-MA-103 p2 contra el render ya descargado) y si hay corrupción
  hermana se propone en el MISMO paquete.
