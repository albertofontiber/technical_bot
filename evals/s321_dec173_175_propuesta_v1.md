# s321 — Corrección de DEC-173(b) y DEC-175(b): los dos «NO alcanzable» han caído · propuesta para el dúo

> **Encargo.** El riesgo que quiero que persigáis es la **SOBRE-CORRECCIÓN**. Llevo 24 h
> encontrándome errores propios (un recibo que nunca leyó al juez, tres citas de fuente del modelo
> equivocado, una entrada de deuda mal diagnosticada). El sesgo que me toca ahora no es el de
> defender lo escrito: es el de **tumbar de más por inercia**. Atacad eso.

Rama `claude/s321-packet-b2-correcciones`, worktree propio, **sin commitear**. Lo que leéis en el
repo ya tiene los cambios.

---

## 1. Los hechos (verificados, no inferidos)

DEC-173(b) emitió cuatro veredictos de alcanzabilidad. **Los dos «NO alcanzable» han caído, y por
motivos DISTINTOS** — la distinción es el corazón de la corrección:

**`hp017#2` — medición INVÁLIDA.** Su recibo `evals/s293_hp017_conveyed_preguard_v1.json` tiene reps
de la forma `{pre_yes, post_yes}`, **sin inyección y sin campo de ids admitidos**: medía el efecto
del guard (DEC-172) y la etiqueta se importó a la tabla de DEC-173. La **primera sonda real** es de
s321 (`evals/s293_reachability_hp017_hp017_2.json`): modo `serve`, carrier de la p43
`94cbb0ce-0f89-46f0-9a83-d47680c79d17` admitido 3/3, **base 0/5 → oráculo 5/5 en las TRES reps**,
`alcanzable: true`. El carrier trae ruta + Regla 1 + el porqué en un pasaje contiguo (verificado
antes de inyectar).

**`hp011#2` — medición VÁLIDA, CADUCADA.** `evals/s293_reachability_hp011_hp011_2.json`: modo
`serve`, `oracle_ids_admitidos` = 3 en las 3 reps, juez leído por clave. Era limpia el 2-ago. s320c
re-midió: **los tres brazos alcanzables**.

## 2. Qué he cambiado

| fichero | cambio |
|---|---|
| `docs/DECISIONS.md` | banner en **DEC-173** (cae (b), **(a) el procedimiento NO se toca: queda validado**) y en **DEC-175** (retirado (b); **(a) y (c) intactas**). Cuerpos originales conservados |
| `docs/LEVER_DIGEST.md` | fila de etapa 3 **sobrescrita in-place** → «REABIERTA EN LA PUERTA DE POBLACIÓN», ni cerrada ni «hay lever» |
| `docs/PLAN_RAG_2026.md` | los dos pasajes que afirmaban el cierre y los veredictos |
| barrido | 12 dependientes revisados; los 4 artefactos de `evals/` se dejan como registro de su momento (DEC-147: versionar, no reescribir) |

## 3. Lo que afirmo, y quiero que ataquéis

1. **DEC-175(a) NO cae** porque su métrica es **POBLACIÓN** (1 gold/39 · 0,13%), no `conveyed`. Lo
   mismo DEC-174 (precisión del gatillo 98,3% + regla de daño). ¿Es correcta esa discriminación por
   métrica, o estoy usándola para salvar lo que me conviene?
2. **El estado correcto es «REABIERTA en la puerta de población»**, no «cerrada» ni «hay lever»:
   los dos hechos son alcanzables pero su población está **sin medir**, y el propio DEC-175 exige
   las dos puertas. ¿Es ese el estado honesto?
3. **La distinción inválido/caducado** se sostiene contra los recibos.
4. **Endurecimiento propuesto (fase 2, NO cableado aún)**: un «NO alcanzable» solo emitible con
   modo `serve`/`appendix` **Y** `oracle_ids_admitidos` no vacío; y estampar el estado de corpus en
   el recibo. ¿Cierra la clase o deja hueco?

## 4. Debilidades declaradas de entrada

- **El «within-doc-miss 11»** que cito como pista de población es de un DEC anterior; corpus y
  golds se han movido (tres veces solo el 12-ago). Lo declaro como hipótesis, no como cifra viva.
- La sonda de `hp017#2` es **N=3, un hecho**, y la corrida tuvo `ReadTimeout` contra Supabase.
- **«Alcanzable» dice «si lo viera»**, no que ninguna lane vaya a traerlo: la viabilidad de la lane
  sigue sin medir. Un alcanzable NO es un GO.
- Reabrir etapa 3 toca el bloque de estado del PLAN, que es el doc canónico.
- No he tocado `cat017#2` ni `hp003#4`: tenían admisión verificada y ninguno decide nada hoy.

## 5. Preguntas concretas

1. **¿Sobre-corrijo?** ¿Hay una lectura en la que DEC-175(b) siga en pie —p.ej. que la conclusión
   práctica («lo que resta es adjudicación de golds») siga siendo cierta aunque dos fundamentos
   sean falsos— y retirarlo sea churn?
2. **¿Infra-corrijo en algún sitio?** ¿Queda algún dependiente vivo afirmando lo caído? (con
   DEC-186 se me escapó `src/config.py`).
3. **¿Es correcto dejar los artefactos de `evals/` sin tocar**, o alguno induce a error de forma
   activa?
4. **¿El endurecimiento tiene falsos positivos?** ¿Puede bloquear un «NO alcanzable» legítimo?
5. **¿Qué NO he verificado y debería antes de commitear?**

Si la corrección es proporcionada, decidlo — `SÓLIDO` es respuesta válida y la prefiero a un
hallazgo fabricado.
