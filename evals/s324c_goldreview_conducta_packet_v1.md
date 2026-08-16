# s324c — Packet de GOLD-REVIEW: la clase «negar la premisa» (3 hechos del FULL 16-ago que ningún lever de serving paga)

> **Para Alberto (16-ago noche, s324c). Nada aplicado.** Tres hechos «no OK» del ruler cuya sonda de alcanzabilidad
> (evidencia perfecta delante del generador, juez canónico K=5, THRESH_FIRM 4) dio **NO_ALCANZABLE** o **inestable**:
> el modelo tiene el dato servido y aun así no lo transmite, porque la pregunta lleva una PREMISA que el manual
> contradice, y el modelo contesta lo que sí existe en vez de negar la premisa. Son decisiones de **gold** o de
> **producto** (conducta), no de retrieval ni de serving. Cada uno lleva sus tres opciones; marca una.
> Referencia de método: DEC-224 (sentada B2 vía `gold_store`, verificación completa) y DEC-221 (el gold se ancla en el
> pasaje que da el MECANISMO). No re-litiga DEC-173/175.

---

## 1 · `hp009#0` — Morley ZXe, «¿qué resistencia de fin de línea para los lazos?»
- **Hecho gold (core)**: «El lazo analógico direccionable de la ZXe se cablea como BUCLE CERRADO (Inicio Lazo +/− OUT →
  Retorno +/−); NO se cierra con resistencia de fin de línea» · valor `Retorno` · MIE-MI-530 p19.
- **Sonda (s324b, `serve` con `a8d7b1a4` p19 + `dadab3e0` admitidos 3/3, cobertura atestada)**: base 0/5 ×3 → oráculo
  0/5, 0/5, **3/5**. Con el carrier delante, el modelo responde: «RFL para sirenas 6.800 Ω [F1]; para el lazo RS-485 150 Ω
  [F7]…» y en la mejor rep «el lazo analógico no utiliza RFL, se instala en bucle cerrado (retorno al panel)» — sin
  nombrar los terminales `Retorno` (3/5, no firme). Recibo `evals/s293_reachability_hp009_hp009_0.json`.
- **Lectura**: la pregunta presupone que HAY una RFL; el modelo contesta las RFL que existen (sirenas, RS-485) y relega
  el lazo a una nota. El hecho exige **negar la premisa** y nombrar `Retorno`.
- [ ] **(a) Mantener el gold tal cual** → queda como diana de CONDUCTA (el bot debe negar premisas falsas): decisión de
      producto, fuera del ruler; sigue contando como no-OK.
- [ ] **(b) Reescribir el hecho para que la vara acepte «bucle cerrado / retorno al panel» sin exigir el literal
      «Retorno»** (la rep 3/5 lo tenía) → gold-edit vía `gold_store`, con marca tuya (DEC-025).
- [ ] **(c) Bajar el hecho a `supplementary`** (la RFL de sirenas y RS-485 sí las da; el «no lleva RFL» pasa a
      complementario).

## 2 · `hp013#1` — Detnov ADW535, «¿cómo se cambia la batería tampón sin perder configuración?»
- **Hecho gold (core)**: «El ADW535 se alimenta externamente con entrada REDUNDANTE PWR-R; el respaldo es esa
  alimentación redundante, NO una batería tampón; la única batería es de litio (LMB 35) para el RTC» · valor `PWR-R`.
- **Sonda (s321, `serve` con `a19e8735` p56 tabla de bornes + `2365dfaa` p12 glosario, entrega 3/3, cobertura
  atestada)**: base 0/5 → oráculo **0/5 ×3**. Las tres veces: «el procedimiento de sustitución de la batería de litio
  del ADW535 no está descrito en los fragmentos…» — sin mencionar `PWR-R` ni «redundante». Recibo
  `evals/s293_reachability_hp013_hp013_1.json` (DEC-175 banner).
- **Lectura**: la pregunta dice «batería tampón» y el modelo se ancla en «batería»; el hecho exige negar la premisa
  («no es una batería, es la alimentación redundante»). Además el FULL 16-ago lo bajó a `retrieval-miss` (`raw=0`).
- [ ] **(a) Mantener** → diana de conducta (negar premisa), fuera del ruler.
- [ ] **(b) Reescribir la pregunta** para que no presuponga batería tampón (p. ej. «¿qué respaldo de alimentación tiene
      el ADW535 y qué batería lleva?») — cambia el gold, exige nueva localización (DEC-025).
- [ ] **(c) Bajar a `supplementary`** el hecho PWR-R y dejar core «batería de litio LMB 35 para el RTC» (que sí transmite).

## 3 · `hp011#2` — Morley RP1r-Supra, «tras la descarga no vuelve a normal al resetear: ¿qué comprobar?»
- **Hecho gold (core)**: «Parámetro t.A “Duración de la descarga” (soak time): 05 a 295 seg; “--” = activado hasta el
  rearme (por defecto)» · valor `05 a 295 seg` · p56.
- **Sonda (s293, `serve` con AMBAS mitades admitidas)**: 0/5 → 0/5 ×3 en s293; en s320c (re-medición fresca, 5 reps/brazo)
  ALCANZABLE pero **INESTABLE**: sonnet 1/5 · sonnet-5 1/5 · opus-5 4/5 (DEC-186 EN REVISIÓN — no citar «techo»).
  El oráculo contesta con «rearme inhibido por `r.i`», ABORT enclavado, etc.: comprobaciones correctas de la respuesta
  gold, y **el soak time aparece o no según la rep**.
- **Lectura**: la vara pide un parámetro concreto (`t.A` 05-295 s) dentro de una lista de comprobaciones; el modelo
  tiene el dato y responde con OTRO parámetro válido de la misma lista. Es «transmisión inestable», no serving.
- [ ] **(a) Mantener** → objetivo de estabilidad de síntesis (fuera de este packet; sin lever de serving: DEC-173 vigente).
- [ ] **(b) Reescribir el hecho como «la duración de descarga (t.A) es un parámetro a comprobar»** sin exigir el rango
      literal (05-295 s) — gold-edit.
- [ ] **(c) Bajar a `supplementary`** (la respuesta gold ya cubre ABORT/rearme/inhibición como core).

---
**Qué NO decide este packet**: nada de retrieval ni de serving (los levers de esa clase están medidos en el
LEVER_DIGEST); ni el ítem 2 del packet B2 (DEC-186 sigue EN REVISIÓN). Cuando marques, se aplica vía `gold_store` con
la verificación completa de DEC-224 y se re-mide el factlevel (smoke primero).
