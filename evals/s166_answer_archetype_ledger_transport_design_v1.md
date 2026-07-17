# S166 many-to-many facet transport

S166 is a transport-only successor to S165. It does not call a model and does
not change the prompt, facet vocabulary, evidence units, cohort, thresholds or
semantic selections.

The v1 validator incorrectly required one source unit to belong to only one
answer facet. Technical evidence is naturally many-to-many: one source row can
simultaneously encode a default, a limit and a warning. S166 therefore preserves
all facet assignments but materializes the evidence payload as the stable union
of unique source-unit IDs.

The contract remains fail-closed:

- facet names must be unique and belong to the frozen vocabulary;
- IDs must be unique inside each facet;
- every ID must exist in the immutable source packet;
- total facet-to-unit assignments are capped at 32;
- the union is capped at 12 unique units;
- output order is first appearance, making replay deterministic.

Replaying the immutable S165 outputs can yield only a local development result.
A pass requires the unchanged S165 recall, precision and complete-question
thresholds and authorizes only a separately frozen target-independent cohort.
