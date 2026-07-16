# S117 M2 — determinismo de idioma, contrato v2

Este documento conserva la regla semántica de v1 y endurece su gate.

## Regla

Mantener detección por página, herencia de `unknown`, conteos,
`languages_present`, `verdict` e indexabilidad. El idioma con más páginas sigue
ganando. En empate, gana el primer idioma **conocido** observado por número de
página en la detección raw; portadas `unknown` no participan en el desempate.

## Baseline y diferencial de corpus

Antes de editar `language.py`, un runner versionado congela por SHA de
extracción, sobre los 1.068 raws sellados:

- detección raw por página;
- `page_language` final;
- conteos por idioma y `languages_present`;
- `verdict` y `dominant` legacy;
- si el máximo es único;
- ganador esperado de la regla first-known para los empates.

Después del cambio, el mismo runner falla salvo que:

1. `page_language`, conteos, `languages_present` y `verdict` sean idénticos en
   cada documento;
2. todo máximo único conserve `dominant`;
3. solo documentos empatados puedan cambiar `dominant`;
4. todo empate elija exactamente su first-known congelado;
5. cardinalidad y conjunto de SHA permanezcan idénticos.

## Reproducibilidad cross-process

Se ejecutan dos replays M2 completos y locales con
`PYTHONHASHSEED=1` y `PYTHONHASHSEED=2`. Sus ficheros de salida, manifests
locales y payloads lógicos deben ser byte a byte idénticos. Ambos reutilizan el
snapshot gzip ya capturado y no aceptan `--env-file` ni abren una conexión.

## Freeze v2.5

Un prereg nuevo hereda v2.4 y congela antes del replay:

- este diseño y v1;
- baseline corpus-level y runner del gate;
- nuevo SHA de `src/reingest/language.py`;
- analyzer M2 y snapshot remoto existente (SHA gzip y SHA JSONL);
- runtimes y demás inputs heredados.

Cualquier cambio de funnel, terminales o workload respecto del resultado
provisional se reporta como cascada upstream de la regla determinista, nunca
como relabel manual. No se recaptura Supabase.
