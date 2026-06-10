# DEC-021 §D — cierre: ¿DIFERIR el dual-judge? (lectura K=5) — REFUTA, es mi 3ª interpretación

## Por qué este review
He interpretado esta pregunta 3 veces y he fallado 2 (confirmation-bias hacia mi prior "diferir"; el dúo me refutó con hp006/hp003 que luego resultaron ruido). Ahora tengo dato K=5. Antes de cerrar §D, REFUTA esta lectura — sobre todo: ¿estoy pattern-matching a "diferir" otra vez?

## El experimento (medir-primero, DEC-021 §D)
Para decidir si construir un dual-judge (Claude+GPT votando el eje de SEGURIDAD factual), medí el desacuerdo GPT-5.5 (juez canónico) vs Claude-Opus sobre el eje FACTUAL del scorer, **K=5 corridas por modelo**, sobre las 22 respuestas del bot (`bot_vs_gold_results_k5.yaml`). Datos crudos: `evals/_s47_judge_kruns.json`. El eje es **contradicción-ONLY** (DEC-012, `atomic_scorer.py:104`: "NO es contradicción: (a) que el bot OMITA un hecho; (b) que el bot añada info extra").

## Resultado K=5 (frecuencia de flag, 0..1)
- **Acuerdo estable: 17/22.** 6 "sí-contradicción" ambos ≥0.8 (cat001, hp002, hp006, hp011, hp017, hp018 = los FALLO reales) + 11 "no" ambos ≤0.2.
- **DESACUERDO-ESTABLE: 5/22**, TODOS una dirección (Claude 0.8-1.0 / GPT 0.0): cat007, hp001, hp008, hp010, hp015.
- **0 casos** de "GPT marca estable / Claude no". GPT no caza NADA único.
- **hp003 y hp006 eran RUIDO de single-run:** hp003 GPT 0/5 (no era catch de GPT); hp006 ambos ~1.0 (no era catch único de Claude). Los 2 pilares de la refutación previa del dúo ("pro-ensemble") se disuelven a K=5.

## Qué SON los 5 flags estables de Claude (contenido verificado, 4 de 5)
- cat007: bot dice "los fragmentos no describen el fail-safe" → incompletitud/honesto-sobre-retrieval.
- hp008: bot dice "protocolo Notifier" sin nombrar "CLIP" → omisión/under-spec.
- hp001: bot añade "Mapas" + "Lazo" singular → "añadir info extra" (excluido por el contrato).
- hp010: bot dice "el paso-a-paso no está en los fragmentos recuperados" → honesto-sobre-retrieval.
- hp015: contenido NO capturado (flickea); 1/5 sin confirmar.
Patrón: Claude cuenta incompletitud/omisión/extra como "contradicción"; el contrato dice que NO lo son. GPT aplica el contrato bien.

## Mi argumento de robustez (el que más quiero que ataques)
Los 5 casos que Claude flagea **ya son no-PASS por OTROS ejes** (completitud / juez holístico): cat007=PARCIAL, hp006=FALLO, hp010=PARCIAL (verificados); creo que hp001/hp008/hp015 también son no-PASS. → añadir Claude **NO añade cobertura** (esos fallos YA se cazan), solo re-etiqueta incompletitud como "contradicción" + mete falsos-flags. Por eso "diferir" es robusto AUNQUE el contrato sea ambiguo sobre si "el bot dice falsamente que el manual no tiene X" es contradicción o incompletitud.

## Mi decisión — REFÚTALA
DIFERIR el dual-judge: GPT no tiene hueco demostrado (0 catches únicos a K=5); Claude tal-como-se-probó añade 5 falsos-flags y 0 cobertura nueva. El juez único GPT-5.5 + K-mayoría (DEC-015) es adecuado para §A. Un Claude con prompt alineado al contrato es opción futura SI GPT muestra un hueco; hoy no lo muestra.

## Ataca estos riesgos (y busca más)
1. **3ª interpretación → confirmation-bias:** ¿interpreto K=5 para volver a "diferir" otra vez?
2. **¿"Claude over-strict" o "GPT under-flagging"?** cat007/hp006/hp010: el bot afirma FALSAMENTE que el manual no tiene algo que SÍ tiene. ¿No es eso un fallo factual REAL que GPT pierde (→ pro-ensemble), y lo descarto llamándolo "incompletitud"?
3. **¿Aguanta "ya son no-PASS por otros ejes"?** Verifica los veredictos canónicos de los 5 en `bot_vs_gold_results_k5.yaml`. Si alguno es PASS, mi robustez se cae (Claude SÍ añadiría cobertura).
4. **¿K=5 / temp=1 bastan?** ¿El "0 catches únicos de GPT" es robusto o n pequeño?
5. **hp015**: 1/5 sin contenido. ¿Importa?
