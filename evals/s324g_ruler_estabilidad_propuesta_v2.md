# s324g — El ruler y la inestabilidad: lo que YA existe, lo que mi propuesta inventaba, y qué hacer

> **Sustituye a `evals/s324d_ruler_n1_propuesta_v1.md`, que el dúo r42 tumbó (Sol 8 hallazgos con
> 2 críticos · Fable 6, emparejado · veredicto conjunto NO SÓLIDO).** No es un ajuste de la v1: la
> v1 proponía **construir un mecanismo que ya está construido**, con un diseño que además tenía
> sesgo. Esta v2 recomienda algo mucho más pequeño, y **no gastar los 20 $ autorizados**.

---

## 1 · El hallazgo que lo cambia todo: el mecanismo YA existe

Sol lo ancló en `scripts/factlevel_assessment.py:1050`. El FULL, desde hace tiempo y por defecto
(`do_stability=True`, `K_STAB=3`):

- genera **2 réplicas** por gold con `gen_answer_only` **sobre la composición servida** —no sobre
  el top-k, para no medir churn de retrieval—;
- las adjudica con el **MISMO árbitro dual** que la clasificación (GPT → si miss, Opus). Su
  comentario lo dice: sin eso, «stable-miss» significaría «estable para GPT», no estable bajo el
  instrumento;
- estampa `stability = "stable-miss" | "flip"` en cada hecho.

**Mi «opción A» era eso.** La propuesta v1 pedía construir réplicas por hecho y estimaba +6-9 $ de
coste incremental; el coste ya está pagado y el dato ya está en el recibo. Es exactamente el fallo
que la «pregunta cero» de CLAUDE.md existe para evitar: montar un aparato para algo ya resuelto.

## 2 · Entonces, ¿de qué servía mi medición de s324d?

De confirmación independiente, y con una vara distinta — que es justo lo que Sol y Fable señalan
como defecto de framing. Comparado hecho a hecho:

| | FULL (N=3, árbitro **dual**) | sonda s324d (N=5, **sólo primario**) |
|---|---|---|
| coinciden | **9 / 15** | |
| discrepan | 6 | de los cuales **3** (`cat008#1`, `cat018#1`, `hp005#0`) el FULL los tiene como **OK rescatados por el dual**, no como no-OK |

O sea: **la mitad de la discrepancia no es discrepancia, es que yo metí en el universo hechos que
el FULL ya clasificaba OK.** Fable lo dijo exactamente así y lo he verificado ejecutándolo.

## 3 · Lo que la v1 afirmaba mal (confirmado por los dos revisores)

| Afirmación de la v1 | Qué es cierto |
|---|---|
| «los 15 hechos no-OK del FULL» | El FULL tiene **17** de clase no-OK (12 synthesis · 2 rerank · 3 retrieval). Los 15 que medí son los de `conveyed_yes < 4`, **y 3 de ellos son OK** por el rescate dual |
| «~60 % de sus no-OK son ruido» | Es 9/15 de una **cohorte primaria condicionada**, no el 60 % de los no-OK del ruler |
| «la cola real es 6» | Ni 15 ni 6: ignora los 5 upstream (deterministas, y defectos igual) e incluye hechos **ya adjudicados fuera de cola** — `hp009#0`/`hp011#2` fueron a gold-review de conducta y `hp017#2` está declarado no alcanzable |
| «vista congelada» | Es la vista de **HOY**, no la del FULL del 16-ago: mi propio recibo lo declaraba y la propuesta lo omitió |
| «determinista dado el pool» (eje de soporte) | El eje usa el mismo juez K=5 estocástico: **baja varianza ≠ determinista** |
| precedente «DEC-023» | Es **DEC-015** (K-mayoría en toda medición de lever). DEC-023 es el embargo/esquema de Track B |

## 4 · Y el diseño tenía sesgo (el crítico de Sol, con el número de Fable)

La opción A re-generaba **sólo los que fallaban**. Eso no es una mayoría de 3: acepta con
probabilidad `p + (1-p)p²` en vez de `3p² - 2p³`. En cristiano: **un hecho que acierta por suerte a
la primera se queda OK sin verificar** —el 20 % de las veces si su probabilidad real es 0,2—,
mientras que uno que falla necesita dos aciertos seguidos para recuperarse. El método **sube el
%OK por construcción**, no porque el bot mejore. Y por eso tampoco puede estampar `ESTABLE_OK`:
nunca mira los éxitos.

## 5 · Recomendación

**R1 · No construir nada y no medir nada. Usar el campo que ya se calcula.** `stability` distingue
`stable-miss` de `flip` con la vara correcta. Lo que falta no es dato: es que **el scoreboard y la
cola de trabajo no lo miran**. Exponerlo en `docs/FACTLEVEL_ASSESSMENT.md` cuesta una columna.

**R2 · Para PRIORIZAR, nunca para reclasificar.** Ésta es la línea que evita el sesgo de §4: un
`flip` **sigue siendo** `synthesis-miss` en la clase terminal —no se promueve a OK— pero baja en la
cola de defectos, porque atacar un fallo que la mitad de las veces no ocurre es gastar en ruido. Sin
promoción no hay sesgo direccional, y no hace falta romper la comparabilidad de la serie.

**R3 · Si algún día se quiere reclasificar de verdad**, entonces sí hace falta N=3 **simétrico**
(opción B: replicar TODOS los hechos, no sólo los que fallan), declarar serie nueva y pagar ~×3 el
coste de generación. Hoy no lo pide nada: ninguna decisión abierta depende de mover un `flip` a OK.

**Coste de esta v2: 0 $.** De los 20 $ autorizados no se gasta ninguno, porque el dúo demostró que
no hay nada que medir.

## 6 · Gaps declarados

1. `stability` sólo se calcula para los `synthesis-miss` **dual-confirmados** (está gateado). Los
   fallos upstream —rerank y retrieval— no llevan estabilidad, y son 5 de los 17.
2. `ESTABLE_MISS` es **cota superior** del defecto real, como decía el propio recibo de s324d: que
   falle 3/3 no prueba que sea estructural, sólo que no se recuperó en tres tiradas.
3. Esta v2 no re-mide nada: se apoya en el FULL del 16-ago y en la sonda de s324d, con las dos
   varas declaradas. Si el corpus cambia, ambos caducan.
