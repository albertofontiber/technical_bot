"""Pipeline de re-ingesta (PLAN_RAG_2026 Fase 1).

Arquitectura en dos etapas con una frontera duradera:

  Etapa A — Extracción (cara, externa, se paga una vez):
    A1 inventory  — inventario del corpus + dedup nivel 1 (SHA-256)
    A2/A3 extract — LlamaParse multimodal → store duradero

  Etapa B — Indexación (barata, local, re-ejecutable):
    language, chunk, metadata, dedup, contextualize, embed, index

Ver docs/PLAN_RAG_2026.md §Fase 1 para el diseño completo.
"""
