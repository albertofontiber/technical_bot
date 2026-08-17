# s324d · ¿Cuánto de los «no OK» del FULL es RUIDO de N=1? (estabilidad de SÍNTESIS)

> JSON `evals/s324d_estabilidad_sintesis_v1.json` · `scripts/s324d_estabilidad_sintesis.py` · git `a19929fd` · corpus 26216→26216 filas (sin cambio) · juez `judge_conveyed21` GPT-5.5 K=5, `THRESH_FIRM=4` (vara INTACTA) · `claude-sonnet-4-6`/`fidelity`. **Solo medición; ningún lever ni cambio de pipeline.**

**Pregunta.** El FULL etiqueta cada hecho con UNA generación. s324c mostró en 4 hechos que con la vista IDÉNTICA la respuesta varía. ¿Cuánto de los «no OK» es ruido de muestreo?

**Método.** Universo = hechos del FULL 16-ago con `conveyed_yes < THRESH_FIRM` (15: 12 `synthesis-miss` + 3 rescatados por el dual-judge). Por GOLD: un turno real por el seam; la vista que entra a `generate_answer` se CONGELA y se generan **N=5** respuestas sobre ella (rep0 en el seam; reps 1-4 = `gen_answer_only`, DEC-168). Cada respuesta se juzga para CADA hecho-diana del gold — igual que el FULL. **ESTABLE_MISS**=0/5 firmes · **INESTABLE**=0<firmes<5 · **ESTABLE_OK**=5/5.

| hecho | valor | FULL `conv`·`stability`·submotivo | vista: filas(pref)·`hash_view` | votos | firmes | clase | $gold |
|---|---|---|---|---|---|---|---|
| `cat001#3` | 32 / 25 / 20 | 0·dual0·flip·omitted | 13(10)·`49c89521` | 5,5,0,5,5 | **4/5** | **INESTABLE** | 0.94 |
| `cat008#3` | 1/2/3/4 lazo; 6-7  | 0·dual0·flip·omitted | 10(10)·`87ac0fc8` | 5,0,0,5,0 | **2/5** | **INESTABLE** | 1.22 |
| `cat016#1` | menu ZONA + ELEMEN | 0·dual0·flip·omitted | 11(10)·`c3e16468` | 0,5,0,0,0 | **1/5** | **INESTABLE** | 0.66 |
| `hp003#4` | magnetotermico | 0·dual0·stable-miss·omitted | 12(10)·`7865afac` | 0,0,0,0,0 | **0/5** | **ESTABLE_MISS** | 0.49 |
| `hp005#3` | CIRCUITO SIRENA | 0·dual0·stable-miss·omitted | 13(10)·`88d3faaf` | 1,5,3,1,0 | **1/5** | **INESTABLE** | 1.42 |
| `hp009#0` | Retorno | 0·dual0·stable-miss·omitted | 10(10)·`a3ce3d6a` | 0,0,0,0,0 | **0/5** | **ESTABLE_MISS** | 0.48 |
| `hp011#2` | 05 a 295 seg | 0·dual0·stable-miss·omitted | 13(10)·`48253cb3` | 0,0,0,0,0 | **0/5** | **ESTABLE_MISS** | 0.59 |
| `hp015#0` | convencional | 0·dual0·stable-miss·omitted | 11(10)·`6c586fc1` | 1,5,0,5,5 | **3/5** | **INESTABLE** | 0.76 |
| `hp015#2` | 32 | 0·dual0·flip·omitted | 11(10)·`6c586fc1` | 0,0,0,5,0 | **1/5** | **INESTABLE** | 0.76 |
| `hp017#1` | instruccion de ent | 0·dual0·stable-miss·omitted | 12(10)·`a8ff38ee` | 0,0,0,0,0 | **0/5** | **ESTABLE_MISS** | 1.13 |
| `cat020#1` | 0-100 % normalizad | 0·dual0·stable-miss·contradicted | 10(10)·`6b714d49` | 5,0,0,5,5 | **3/5** | **INESTABLE** | 0.54 |
| `hp017#2` | Editar Configuraci | 0·dual0·stable-miss·hedged | 12(10)·`a8ff38ee` | 0,0,0,0,0 | **0/5** | **ESTABLE_MISS** | 1.13 |
| `cat008#1` | 47 kΩ | 0·dual5·rescatado·— | 10(10)·`87ac0fc8` | 5,0,0,5,2 | **2/5** | **INESTABLE** | 1.22 |
| `cat018#1` | pestana Programaci | 0·dual5·rescatado·— | 12(10)·`ce9fe288` | 0,0,0,0,0 | **0/5** | **ESTABLE_MISS** | 0.88 |
| `hp005#0` | Matriz de control | 0·dual5·rescatado·— | 13(10)·`88d3faaf` | 5,0,5,3,5 | **3/5** | **INESTABLE** | 1.42 |

## Recuento por clase

- **ESTABLE_MISS (defecto real): 6/15** — `hp003#4`, `hp009#0`, `hp011#2`, `hp017#1`, `hp017#2`, `cat018#1`.
- **INESTABLE (el FULL etiqueta al azar): 9/15** — `cat001#3`, `cat008#3`, `cat008#1`, `cat016#1`, `hp005#3`, `hp005#0`, `hp015#0`, `hp015#2`, `cat020#1`.
- **ESTABLE_OK (no-OK por mala suerte): 0/15**.

## La cifra

**De los 15 hechos no-OK medidos (de 15 no-OK del FULL): 6 son DEFECTO ESTABLE (40%) y 9 son RUIDO DE MUESTREO (60%).**

- Cruce con el `stability` del propio FULL (3 reps, primario+dual): coincide en 9/12 de los `synthesis-miss`; declarados `stable-miss` allí y NO estables aquí: `hp005#3`, `hp015#0`, `cat020#1`.

## Alcance

- Medidos **15/15**. Cobertura total. Fuera de alcance por diseño: las clases upstream (`retrieval-miss`, `rerank-miss`, `corpus-gap`), sin `conveyed_yes`.

## Coste real (`scripts/usage_meter.py`)

- **$9.12** en 441 llamadas: `claude-sonnet-4-6` 66× (886,732 in/56,938 out) $3.51 · `gpt-5.5` 375× (559,195 in/93,552 out) $5.60. Presupuesto duro $25; tarifas/M $3/$15 y $5/$30; embeddings/REST no medidos.

## Caveats

- **Asimetría de vara (declarada):** «firme» aquí = juez PRIMARIO ≥4/5, como en s324c; el FULL además rescata con el dual (Opus 4.8). Como `OK_FULL(rep) ⊇ firme_primario(rep)`, **ESTABLE_MISS es COTA SUPERIOR del defecto estable, y el ruido COTA INFERIOR**.
- N=5 no prueba determinismo: con probabilidad real p=0,2 un hecho sale 0/5 el 33% de las veces. Las clases extremas son estimaciones.
- Sello PARCIAL. `hash_view` = cabecera + excerpt servido. Votos no válidos del juez: 0. La vista de HOY no es la del FULL 16-ago (hoy cambiaron corpus y `product_model`): mide estabilidad de síntesis, no reproduce el turno del FULL.
