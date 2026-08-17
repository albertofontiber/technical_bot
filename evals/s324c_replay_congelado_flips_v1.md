# s324c · Replay sobre COMPOSICIÓN CONGELADA de los 4 «flips» de etapa 3 (encargo dúo r33)

> JSON `evals/s324c_replay_congelado_flips_v1.json` (respuestas, juicios, vistas congeladas) · `scripts/s324c_replay_congelado.py` · git `e65b61b3` · corpus 26215 filas (sin cambio) · juez `judge_conveyed21` GPT-5.5 K=5, `THRESH_FIRM=4` (vara intacta) · `claude-sonnet-4-6`/`fidelity`. **Solo medición; ningún lever.**

**Método.** Por hecho: (1) un turno real por el seam (adapters del brazo base de la sonda s293); la vista que recibe `generate_answer` (prefijo + coverage) se CONGELA (ids, orden, hashes, filas) y se generan **N=5** respuestas sobre ella (rep0 en el seam; reps 1-4 = `gen_answer_only` de s289/DEC-168); (2) **N=3** turnos frescos independientes (= brazo base de la sonda). Misma vara. Clases pre-declaradas: SINTESIS_INESTABLE (0<firmes<N, misma vista) · SERVING (congelado estable, fresco cambia con vistas distintas) · ESTABLE_OK · ESTABLE_MISS · NO_CUADRA.

| hecho (`valor`) | FULL 16-ago / sonda base | vista congelada: filas (prefijo) · `hash_view` | firmes/N congelado (votos) | firmes/N fresco (votos) | vistas ≠ | clase | coste |
|---|---|---|---|---|---|---|---|
| `cat001#3` (`32 / 25 / 20`) | conveyed 0 `flip` / base [5, 5, 5] | 13 (10) · `8f161a4e7c4eb7be` | **3/5** [0, 5, 5, 0, 5] | **3/3** [5, 5, 5] | 3/3 | **SINTESIS_INESTABLE** | $1.54 |
| `cat008#3` (`1/2/3/4 lazo; 6-7 entrada A`) | conveyed 0 `flip` / base [5, 5, 5] | 12 (10) · `4d41810e27434e9a` | **1/5** [0, 2, 0, 5, 0] | **1/3** [0, 0, 5] | 3/3 | **SINTESIS_INESTABLE** | $1.25 |
| `cat016#1` (`menu ZONA + ELEMENTO`) | conveyed 0 `flip` / base [0, 5, 0] | 11 (10) · `c3e164688fbecb53` | **2/5** [0, 0, 5, 0, 5] | **0/3** [0, 0, 0] | 3/3 | **SINTESIS_INESTABLE** | $1.10 |
| `hp005#3` (`CIRCUITO SIRENA`) | conveyed 0 `stable-miss` / base [5, 0, 5] | 13 (10) · `ea06d62272ecfba9` | **4/5** [1, 5, 5, 5, 5] | **2/3** [4, 5, 3] | 3/3 | **SINTESIS_INESTABLE** | $1.55 |

## Lectura por hecho (qué falta en las reps no firmes)

- **`cat001#3`**: las 2 reps 0/5 sobre la MISMA vista dan dos de las tres cifras (rep0 omite «32», rep3 «25»); las 3 firmes dan las tres (F1+F9): se cae una componente del hecho compuesto.
- **`cat008#3`**: TODAS numeran los terminales de lazo 1-5 [F6]; las 0/5 nunca sitúan la Entrada A en los terminales 6-7 (solo hablan de 8-9 del M720); cong3 y fres2 (5/5) sí; cong1 también lo dice y sacó 2/5 (near-threshold del juez).
- **`cat016#1`**: todas dicen «menú ELEMENTOS»; solo las 2 firmes añaden «menú ZONA para crear/asignar la zona» [F1]; las 0/5 citan ZONA solo para PRUEBA. Carrier `294a778c` en F1 de la vista congelada.
- **`hp005#3`**: las 5/5 definen la salida de la matriz como «circuito de sirena» (o «salida de sirena») [F11/F12]; cong0 (1/5) y fres2 (3/5) escriben «asigna como salida la sirena» y dejan «circuitos de sirena» solo en la nota EVACUAR (vara borrosa en el borde: fres0 «salida de sirena» = 4/5). La vista congelada NO trae los carriers inyectados por la sonda (MPDT190 p76/78/80).

## Recuento y lectura transversal

- **SINTESIS_INESTABLE: 4/4** — `cat001#3`, `cat008#3`, `cat016#1`, `hp005#3`.
- 0/12 turnos frescos reprodujeron ids+orden de la vista congelada (rerank no determinista, DEC-096b) y aun así con la vista IDÉNTICA los firmes varían en los 4 hechos ⇒ la varianza dominante de estos «flips» es de SÍNTESIS, no de serving.
- Juez bimodal por respuesta (0/5 o 5/5 en 28/32 juicios): varía la RESPUESTA (una componente/detalle entra o no), no el voto. cat016#1 (fresco 0/3, congelado 2/5): con N=3 un full/sonda etiqueta «stable-miss» o «flip» por azar.

## Coste real (medido por llamada)

- **$5.44** en 208 llamadas: `claude-sonnet-4-6` 48× (624,883 in / 44,973 out) $2.55 · `gpt-5.5` 160× (273,950 in / 50,628 out) $2.89. Tarifas por M: Sonnet 4.6 $3/$15; GPT-5.5 $5.0/$30.0 (developers.openai.com/api/docs/pricing, 16-ago); embeddings/REST no medidos (centavos).

## Caveats

- Sello PARCIAL (el hub muta en la misma rama; corpus sin cambio). `hash_view` = cabecera + excerpt servido (proxy del user_message). rep0 congelada en el seam, reps 1-4 fuera sobre deepcopy previo. N pequeño (5/3): un 5/5 o 0/5 no prueba determinismo. Votos no válidos del juez (`n_fail`): 0.
