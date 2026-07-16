# S117 M2 — determinismo de idioma antes del replay final

## Evidencia

La captura y el replay local produjeron el mismo funnel y los mismos terminales,
pero distinto `local.manifest_sha256`. La comparación estructural aisló ese
único campo. El corpus contiene 154 documentos con empate máximo en el número
de páginas por idioma. `profile_document()` calcula `languages_present` como
`set` y usa ese set directamente en `max(...)`; el orden depende del hash seed
del proceso.

## Cambio upstream propuesto

Mantener conteos, verdict, detección, herencia de `unknown` y política de
indexación sin cambios. Solo resolver empates de `dominant` mediante el primer
idioma conocido que aparece por número de página en la detección `raw`. Python
`max()` conserva el primer máximo de una secuencia ordenada, de modo que:

- gana siempre el idioma con más páginas;
- si varios empatan, gana el observado antes en el manual;
- no existe prioridad por fabricante, documento congelado o benchmark;
- no se depende de `PYTHONHASHSEED` ni se impone una preferencia lingüística
  artificial.

Se añadirán tests para empate EN/ES en ambos órdenes y con portada `unknown`.
La regresión completa debe pasar. M2 se reejecutará exclusivamente en replay
local contra el snapshot ya sellado; no se repetirá la lectura de Supabase.

## Gate

GO exige dos replays en procesos separados con manifests y payloads lógicos
idénticos. Si la corrección cambia conteos, los nuevos conteos sustituyen a los
provisionales: es un efecto upstream medido, no un relabel manual.
