# S214 — fresh Kidde multi-source gold cohort

## Purpose

S213 established a clean causal failure: independent per-shard selection removed
global competition but accumulated 18,956 characters for one question and hit
the frozen 12,000-character compiler bound after 26/260 calls. The next mechanism
therefore needs a fresh population on which relevance and compression can be
developed without looking at the 12 official residual questions.

S214 creates that population. It does **not** change the 157-fact denominator,
earn official fact credit, touch production, call the target bot, or authorize a
target run. A later stage may use only S214 support-validated questions to develop
a generic upstream relevance/compression mechanism before any target
preregistration.

## Frozen cohort

- 4 candidate questions, 9 distinct Kidde PDFs, 16 visually inspected pages.
- Every source identity is absent from the official gold and from every string in
  S203-S209 packets, including secondary sources and citations.
- Every candidate is a natural multi-document comparison or selection predicate.
- 168 gap-free, non-overlapping evidence units are derived deterministically from
  the existing immutable extractions; authors and pixel reviewers never see them.
- Same-source S99 augmentation questions and all official questions/facts are
  disclosed for semantic-duplicate veto. S99 rows remain retrieval augmentation,
  not benchmark gold.

The four candidates cover NC panel-family tradeoffs, 2X-A interface tradeoffs,
standalone-versus-KIT MCP packaging, and ModuLaser display-versus-detector roles.
Known source conflicts are frozen before authorship. In particular, 2X-AF1 loop
cardinality is excluded, and the standalone MCP sheet cannot be interpreted as
proving that no compatible back box exists.

## Frontier roles

- Principal author/reviewer/mapper: `gpt-5.6-sol`, reasoning `xhigh`.
- Independent author/reviewer: `claude-fable-5`.
- Both models independently author every candidate from pixels only.
- Each item is reviewed reciprocally, one call per model and item. Fable must PASS
  the principal Sol candidate. Sol's review of the Fable candidate is an
  independent material-disagreement probe; Fable wording is never merged.
- Sol maps every published fact to minimal deterministic evidence units. Fable
  independently verifies pixels, source-page equality, minimality and all
  alternative support paths.

No cheaper model performs gold judgment. No Frontier model is used for local
rendering, hashing, evidence partitioning, schema checks, gating or scoring.

## Item-isolated fail-closed execution

The runner always makes exactly 8 zero-retry authorship calls. An item becomes
review-eligible only if both authors independently return schema-valid,
`SUFFICIENT` candidates. Each eligible item then receives two zero-retry reciprocal
reviews. Each published item receives a Sol mapping call; only a schema-valid
mapping receives a Fable support-review call.

An ambiguity, duplicate, malformed response, disagreement or bad support mapping
rejects only that item. There is no retry, repair, merge, prompt change, threshold
change or replacement item. This avoids a single weak item invalidating evidence
from independent source families while preserving fail-closed semantics.

GO requires at least 3/4 items after both:

1. pixel publication gate; and
2. exact source-page support mapping plus independent support review.

Otherwise the stage closes NO-GO with all completed receipts. Provider transport
or incomplete/model-mismatch failures close HOLD. The maximum is 24 Frontier calls
(8 generation + 8 reciprocal review + 8 support); actual calls stop when a gate
cannot reach three items. Conservative execution budget is USD 100, below the
user's USD 200 bandwidth. Provider retries are zero.

## Invariants

- Packet, PDF, extraction, image, prior-packet and code identities are frozen.
- Pixels are the authority for gold correctness; extraction text is used only
  after publication for deterministic support mapping.
- Each sufficient question must cover the frozen number of distinct PDFs and
  contain at least one genuinely cross-source atomic fact.
- Citation PDF-page pairs must equal evidence-receipt pairs and later equal every
  mapped unit set's source-page pairs.
- Minimum support-validated cohort size is frozen at 3 before model output.
- No official gold mutation, denominator change, target call, database write,
  retrieval, runtime integration or production change.
- `chunks_v2` remains active/read-only.
- `chunks_v3` remains `FINAL_NO_GO_CHUNKS_V3_WHOLESALE`; S214 is not a route to
  reopen it.
- Railway is a demo and is never a PR, merge or scientific gate.

## Frontier design decision requested

PASS unless a concrete defect can let an incorrect/duplicate/unsupported gold or
support mapping satisfy the 3-item GO, leak extracted text into authorship, reuse
a closed source/question, or violate the zero-retry/item-isolation contract. Do
not request another cohort, external validation, style work, deployment or an
additional review round at this gate.
