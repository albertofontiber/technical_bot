# S167 document-independent answer-ledger promotion gate

S167 is the first confirmatory test of the bounded many-to-many answer ledger
introduced by S166. It is not a target probe and cannot move frozen facts to
OK.

## Independence

The source-first packet was frozen before questions or gold labels existed. It
contains fourteen chunks from fourteen different manufacturers and fourteen
different documents: seven tables and seven prose excerpts. The builder
excludes every document used by S135, S146, S147 and the selected S114 holdout,
all documents containing known target UUIDs, and all S146/S147 manufacturer and
product pairs. Its measured overlap with prior documents, target documents,
target chunks and development product pairs is zero.

An independent Sonnet labeler receives one immutable excerpt per call and may
create one natural Spanish field question with two to four necessary,
exact-quote-backed answer points. It may mark an excerpt ineligible. Exact
quotes are verified locally; only a unique whitespace repair is allowed. There
are no retries and no manual label edits.

After the cohort is sealed, Haiku receives the question, bound product identity,
the frozen generic facets and header-aware evidence units. S166 validates its
many-to-many ledger and materializes the bounded stable union of source-unit
IDs. Haiku never writes claims, quotes or final answers.

## Frozen gates

- at least 12 eligible questions from 12 manufacturers;
- at least 5 eligible table and 5 eligible prose questions;
- at least 24 exact-quote answer points;
- claim recall at least 0.90;
- selected-unit precision at least 0.80;
- complete-question rate at least 0.75;
- zero invalid selector outputs and zero source-identity mismatches.

A pass authorizes only a separately frozen, bounded probe on the twelve genuine
synthesis residuals. It does not authorize production, deployment, prompt
replacement or fact credit. A failure closes the mechanism without threshold
changes or a same-cohort retry.

## Cost and stopping

There are at most 14 Sonnet author calls and 14 Haiku selector calls, one per
item and zero retries. The internal worst-case ceiling is USD 2.50. Sol/Fable
review is deliberately deferred until this cheap independent gate produces a
promotion signal.
