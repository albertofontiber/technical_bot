# S161 default-off integration and one-answer probe design v1

## Objective

Measure whether the locally qualified S160 table-preamble closure converts the
five FAAST `source-contract-gap` claims into source-supported answer claims.
The probe must exercise the production generator path, not an evaluation-only
prompt.

## Default-off serving integration

S160 becomes an independent post-rerank lane behind
`TABLE_PREAMBLE_CLOSURE=on` and the existing `POST_RERANK_COVERAGE=on` master
switch. Defaults remain inert.

The lane:

- hydrates only protected reranked seeds and their exact same-blob neighbor;
- appends at most two candidates and never mutates/reorders the prefix;
- exposes only the exact heading-to-boundary evidence card;
- revalidates the card and the lane-specific attestation at the common serving
  seam;
- is GET-only, bounded, fail-open and model-free.

## Paid probe

One `cat007` call uses the frozen S113 `chunks_v2` context plus the exact S160
preamble through the integrated lane. Runtime flags match the measured demo
generator contract: fidelity prompt, guided planner, selection block on and
3,500 output-token cap. The model is the existing production executor Claude
Sonnet 4.6 at temperature zero.

No reranker, judge, frontier reviewer or retry is permitted. The call is
checkpointed before scoring.

## Scoring

The five recovered claims require both semantic presence and citations to the
table plus its applicability preamble:

1. alarm relay contacts and channel-2 applicability;
2. fault relay contacts/AUX and channel-2 applicability;
3. channel fault conditions/common fault and channel-2 applicability;
4. sounder output terminals/channel mapping and channel-2 applicability;
5. 47 kOhm EOL per output and channel-2 applicability.

Previously served requested facts are protected: service/unpowered fault
indication, non-latched fault state, and both relay contact current ratings.
Invalid citations, a token-limit stop, unsupported relay-life normalization or
loss of any protected requested fact blocks promotion.

Passing the answer probe allows protected regression and a diagnostic funnel
transition. It does not authorize production, deployment, push or official KPI
credit.

