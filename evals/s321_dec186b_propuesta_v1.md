# s321 — DEC-186b: el veredicto SUSTITUTIVO del «techo del modelo» · PROPUESTA v1 (nada escrito)

**Estado**: `DEC-186` lleva desde s320c (12-ago) un banner «EN REVISIÓN — NO citar la cifra» sin veredicto
sustitutivo. Los recibos que lo sustituyen **ya existen y están versionados**; falta escribir qué dicen sin
repetir el pecado original (concluir más de lo que la medición sostiene). Impacto **MEDIO** — cambia el
veredicto de un lever ⇒ dúo (Protocolo 3, cierre §2 del CLAUDE.md).

## 1 · Los dos recibos, y qué mide cada uno

| recibo | qué es | resultado |
|---|---|---|
| `evals/s320c_rejudge_s305_stored_v1.json` | re-juicio con el juez canónico (GPT-5.5, K=5, THRESH_FIRM=4) de las 9 `oracle_answer` que s305 **guardó** (truncadas a 1.500 chars ⇒ **lower bound**) | sonnet-4-6 **2/3** firmes (5,5,0) · sonnet-5 **0/3** (0,0,0) · opus-5 **2/3** (0,5,5). Correlación 9/9 con la aparición literal de «295». El recibo roto decía 2 en las 9. |
| `evals/s320c_techo_modelo_ab_v2.json` | el A/B **re-corrido** con el instrumento arreglado (lee `["yes"]`, respuestas sin truncar, n=**5** por brazo, mismo carrier inyectado `f18362c6+2d45a70a`, brazo base) | sonnet-4-6 **1/5** · sonnet-5 **1/5** · **opus-5 4/5** — todas las reps son **0/5 o 5/5**, ninguna intermedia. Base 0 en todos salvo una rep de opus (2). |

Hecho-diana: `hp011#2` (t.A «duración de la descarga»: 05-295 s / «--» = hasta rearme, por defecto), en
la clase «elemento vecino» (DEC-185).

## 2 · Lo que DEC-186 afirmaba y qué cae

**Afirmaba**: «el techo de la clase elemento-vecino NO es del modelo» (los tres brazos 0/3 firmes) ⇒ «no
hay lever de modelo» ⇒ cierre de la vía. **Cae entero**: la cifra nunca salió del juez (TECH_DEBT #75).
Con el instrumento arreglado, los tres brazos **SÍ transmiten** al menos una vez, y opus-5 lo hace 4/5.

## 3 · Veredicto sustitutivo que PROPONGO (prudente a propósito)

> **DEC-186b — El hecho es ALCANZABLE con evidencia perfecta en los tres modelos; el A/B v2 muestra una
> DIFERENCIA ENTRE MODELOS (opus-5 4/5 vs 1/5 y 1/5) que es SUGERENTE, NO CONCLUYENTE: n=5, un solo hecho,
> y patrón binario 0/5-o-5/5 que apunta a SELECCIÓN del chunk más que a capacidad de expresión. NO se
> declara «lever de modelo»; se declara «hipótesis a medir» — y como opus-5 YA es el modelo de producción
> (DEC-219), la medición correcta no es cambiar de modelo sino el FULL de factlevel con el ruler nuevo,
> que ya se está corriendo.**

Por qué prudente: (a) **n=5 y un hecho** no dan potencia — es exactamente el error de s305 (n=3) al revés;
(b) el patrón **binario** es informativo: si fuera capacidad de expresión veríamos 2/5, 3/5; ver solo 0 o
5 dice que el modelo **decide usar o no usar** el chunk inyectado — eso es un fenómeno de atención/selección
sobre el que un lever de serving (orden, marcado del carrier) SÍ podría actuar, y que un cambio de modelo
solo mueve estadísticamente; (c) la pregunta «¿es del modelo?» está mal planteada si producción ya corre el
mejor de los tres — lo que importa es «¿qué hace opus-5 con el ruler nuevo en el FULL?», y eso se mide, no
se infiere de 5 reps.

**Qué NO se toca**: DEC-173 (recibo s293, válido), DEC-185 (la clase existe), la fila «Etapa 3» del
LEVER_DIGEST (ya dice REABIERTA por población — coherente). **Qué se toca**: DEC-186 (banner → veredicto
sustitutivo, apuntando a 186b), PLAN l.369 («pendiente de reescritura» → «reescrita 186b»), TECH_DEBT #75
(la deuda de la RAÍZ del bug sigue abierta — el consumo del dict del juez — pero la parte «DEC-186 sin
número» se cierra).

## 4 · Alternativas descartadas

- **Declarar «SÍ hay lever de modelo: opus-5»** — sería repetir DEC-186 con el signo cambiado y la misma
  falta de potencia. Y no accionable: producción ya es opus-5.
- **Dejar el banner «EN REVISIÓN» indefinidamente** — es lo que hay; el PLAN lo llama «pendiente» desde
  hace 4 días y la sesión anterior ya lo puso en su lista de siguientes.
- **Re-correr el A/B con n=20** (~$15) — mide un solo hecho de una clase que el FULL ya cubre con 39 golds;
  gasto sin cambio de decisión (pregunta cero).

## 5 · Lo que el dúo tiene que atacar

1. ¿El patrón binario 0/5-o-5/5 justifica decir «selección, no expresión», o es sobre-lectura de 15 reps?
2. ¿Es honesto cerrar «DEC-186 sin número» dejando abierta la RAÍZ (#75)? ¿O deben ir juntas?
3. ¿Falta algún doc que siga citando el techo como vigente? (grep: PLAN l.369 y TECH_DEBT l.2688 son los
   únicos fuera de DECISIONS/HISTORY; el LEVER_DIGEST no lo cita).
4. ¿El veredicto sustitutivo dice ALGO que un recibo no sostenga?
