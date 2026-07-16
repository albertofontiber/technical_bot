# S130 — enmienda v10: S116 queda fuera del instrumento autoritativo

Contrato normativo compuesto por:

- `evals/s130_chunks_v3_adequacy_and_impact_design_v9.md`, SHA-256
  `ef04cf53623623e08d005c611cb7c02424ce410644e6bb01f2ba4ea0c0692e61`;
- esta sustitución completa de la sección 6 de V9.

V10 no cambia ningún ledger, binding, exclusión S114/S115/S63, cierre
relacional, censo, métrica, tabla S/P, gate de v4/migración ni coste.

## Sustitución normativa de V9.6

S116 se clasifica como:

`external_content_distinct_pdf_identity_unverified`

Sus artefactos prueban diferencias de contenido por debajo de umbrales
preregistrados, pero no identidad PDF, traducción, revisión o linaje frente a
los 748 documentos de desarrollo con identidad física desconocida.

Por tanto:

1. S116 queda completamente fuera del embargo S130;
2. no se usa para excluir ni incluir ninguna extracción del censo;
3. no participa en ningún count, integrity check, eje S/P o gate held-out;
4. no valida v3, v4, generalización, migración ni producción;
5. el prereg v2 de S130 no incorpora acquisition, status, replay, screen ni
   prereg S116 como inputs autoritativos;
6. los 12 documentos activos y los dos fallidos históricos permanecen como
   cohorte exploratoria externa, fuera de este instrumento;
7. cualquier uso autoritativo futuro requiere un nuevo contrato independiente
   con identidad/linaje resueltos y runner, tests, prereg y receipts completos
   hash-pinned antes de inspeccionar resultados.

La eliminación de S116 no reduce el embargo de desarrollo: los held-out que sí
pertenecen al raw store se derivan exclusivamente de S114, S115 y S63 mediante
los dos ledgers concordantes y el cierre 43 documentos directos → 70
extracciones excluidas fijado por V9.

Todo lo demás en V9 permanece normativo sin modificación.
