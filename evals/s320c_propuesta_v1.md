# s320c — Retirada de la evidencia de DEC-186 y re-medición · propuesta para revisión adversarial

> **Encargo específico, y no es el habitual.** No te pido que verifiques si el bug es real —eso ya
> está ejecutado y es aritmética. Te pido que ataques **la proporcionalidad de la retirada**: si me
> he pasado de frenada, si he sobre-leído una medición sucia, y si al corregir he introducido
> afirmaciones nuevas tan poco sostenidas como la que retiro. El riesgo que quiero que persigas es
> el **error simétrico**: diagnostiqué que alguien sobre-leyó un número; puede que yo esté haciendo
> lo mismo en sentido contrario, y con la confianza extra de haber acertado en lo primero.

Todo lo descrito está COMMITEADO en la rama `claude/s320c-s305-instrumento` (commit `5c5ba85`,
ramificada de `main` tras el merge de la PR #248). El árbol está limpio: lo que leas en el repo YA
incluye mis cambios. Para ver qué cambié, compara contra `main` o lee los ficheros citados abajo.

---

## 1. El hallazgo (lo doy por establecido; atácalo solo si ves algo)

`scripts/s305_techo_modelo_ab.py` consumía `judge_conveyed21` —que devuelve
`{"yes": int, "n_fail": int}` (`scripts/factlevel_assessment.py:497-502`)— con
`sum(1 for v in <dict> if v)`. Iterar un dict recorre sus CLAVES: dos strings no vacías ⇒ la suma
vale **siempre 2**, sin consultar al juez, e incluso con la API del juez caída.

Consecuencias verificadas: `evals/s305_techo_modelo_ab_v1.json` tiene `base_yes = oracle_yes = 2`
en las 9 reps de los 3 brazos; `oracle_firme` (≥ `THRESH_FIRM`=4) era 0 por construcción; las ramas
«MONTAJE NO COMPARABLE» y «EL TECHO ERA DEL MODELO» eran inalcanzables; el script solo podía
imprimir «INCONCLUYENTE» o «TECHO CONFIRMADO». **DEC-186 se apoyó en esa cifra.**
`scripts/s293_reachability_probe.py:183` usa el mismo juez correctamente.

Verificación adversarial previa (3 refutadores + 3 barridos, misma familia que yo): 0 refutaciones.
Radio de la clase medido: los 20 llamadores restantes de los tres jueces-dict consumen por clave, y
un detector de campo-constante sobre los 886 JSON del nivel superior de `evals/` encontró s305 como
único fichero con un campo de juez invariante.

## 2. Las mediciones nuevas

**(a) Re-juicio de las respuestas guardadas** (`evals/s320c_rejudge_s305_stored_v1.json`, script
`scripts/s320c_rejudge_s305_stored.py`): sonnet-4-6 2/3 firmes · sonnet-5 0/3 · opus-5 2/3;
correlación 9/9 entre «firme» y la aparición literal del valor. Dos corridas independientes con los
9 votos idénticos. **Limitación declarada**: las respuestas del recibo v1 están truncadas a 1.500
chars ⇒ lower bound; no hay brazo base guardado.

**(b) Re-medición fresca** (`evals/s320c_techo_modelo_ab_v2.json`, 5 reps/brazo, 0 votos de juez
fallidos, respuestas sin truncar): **los tres brazos ALCANZABLES** — sonnet-4-6 **1/5** firmes ·
sonnet-5 **1/5** · opus-5 **4/5**, max 5/5 los tres. El script dispara **MONTAJE NO COMPARABLE**.

## 3. Lo que AFIRMO ahora, que es lo que debes atacar

1. El «NO alcanzable» de DEC-173 **no describe el sistema de hoy**, y su corolario «la
   pair-completion que s292 iba a diseñar NO pagaría» queda **CONTESTADO**.
2. La clase real no es «techo» sino **transmisión INESTABLE**: 6/15 firmes con evidencia perfecta.
3. `base` = 0/5 en 14 de 15 ⇒ el hueco es de **serving**, no de generación.
4. opus-5 4/5 frente a 2/10 **apunta** a un eje de modelo pero **no lo establece** (Fisher agrupado
   p=0,089; C vs A p=0,206).
5. DEC-173 **no cae** (su recibo es medición válida); lo que hay es tensión empírica 2-ago vs 12-ago.
6. El ítem 2 del packet de gold-review **sale**: el gold se queda como está y no hay nada que
   adjudicar. Los otros 8 ítems están sanos porque ninguno cita s305.

## 4. Debilidades que declaro de entrada (no esperes a encontrármelas)

- **3 de las 15 reps corrieron con canal degradado** (2 fail-open de hyq-table en el brazo B, 1 de
  enunciados en el C por `ReadError` 10054) y **las tres dieron 0/5**, incluida la única no-firme de
  opus-5. La atribución rep-a-rep sale del ORDEN DEL STDOUT, no de un campo del recibo. La corrida
  **no es un freeze-contract limpio**.
- **La divergencia con s293 sigue sin explicar**: mismo modelo de control, mismo hecho, mismos dos
  portadores inyectados; 2-ago dio 0/5 en 3/3 con «295» ausente en las 3 respuestas, y hoy da
  alcanzable. Corpus (doc_map 861→887 en #248), composición servida o varianza: no lo sé.
- **n=5 por brazo no tiene potencia** para el eje modelo, y el diseño original (n=3) menos aún.
- El recibo v1 no guarda `base_answer` ⇒ el delta base→oráculo de aquella corrida es irrecuperable.
- El `git_sha` que estampaba el recibo v1 no contiene el script que corrió (estaba untracked).

## 5. Qué he escrito en el repo (el objeto de la revisión)

- `TECH_DEBT.md` #75 — la entrada de deuda, redactada sobre la CLASE.
- `docs/DECISIONS.md` — banner EN REVISIÓN sobre DEC-186 (la entrada original se conserva intacta
  debajo).
- `docs/LEVER_DIGEST.md:44` — fila de etapa 3 anotada en sus tres celdas.
- `docs/PLAN_RAG_2026.md` — bullet de s305 reescrito + bloque «Qué sigue» corregido a 8 ítems.
- `evals/s312_goldreview_b2_packet_v3.md` — ítem 2 retirado con su porqué.
- `evals/s294_goldreview_b2_packet_v1.md` — ⛔ sobre el ítem 10 (antepasado del 2).
- `evals/s294_cad171_menu_avanzado_v1.md` — pregunta del techo RE-ABIERTA.
- `evals/s318_sentada_adjudicacion_packet_v1.md` — puntero corregido.
- `scripts/s305_techo_modelo_ab.py` — fix + endurecimiento (lectura por clave, `n_fail`, respuestas
  enteras, volcado parcial por brazo, salida a fichero nuevo, detector de aguja atascada).

Suite completa: 3.833 passed / 46 skipped.

## 6. Preguntas concretas que quiero que respondas

1. **¿Es proporcionada la retirada?** ¿Marcar ocho documentos es lo correcto, o he contaminado
   documentos que no lo necesitaban? ¿Hay alguno que debí marcar y no marqué?
2. **¿Está licenciada la afirmación «la pair-completion queda CONTESTADO»?** Con 3 de 15 reps
   degradadas y la divergencia con s293 sin explicar, ¿tengo derecho a reabrir esa línea, o debería
   limitarme a «DEC-186 no es interpretable» y callarme sobre DEC-173/DEC-175?
3. **¿He creado afirmaciones nuevas mal sostenidas** en los textos que escribí? Léelos como si
   fueran de otro y busca el mismo pecado que denuncio.
4. **¿Es correcto el marco «MONTAJE NO COMPARABLE / inconcluyente»**, o hay una lectura mejor de
   los datos que se me escapa?
5. **¿El endurecimiento del instrumento introduce algún problema nuevo?** En particular el detector
   de aguja atascada: ¿puede dar falsos positivos que bloqueen una medición legítima (p.ej. un
   0/5 genuino en todos los brazos, que es un resultado real y esperable)?
6. **¿Qué NO he verificado y debería antes de mergear?**

Si tras leer el repo concluyes que la propuesta es sólida, dilo — un `SÓLIDO` es una respuesta
válida y prefiero eso a un hallazgo fabricado.
