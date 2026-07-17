# S147 fresh per-item header-aware gate

S146 failed before evidence selection because one batch author call produced a
valid table population but rejected six useful prose excerpts. S147 changes only
the authoring topology: each fresh source is handled in an isolated Haiku call.
This prevents cross-item omission and keeps every call cheap and bounded.

The source packet excludes the 36 S135 documents and all 14 S146 documents. It
again contains 14 manufacturers split 7/7 between tables and prose. The
header-aware unitizer, runner, thresholds and zero-retry policy are frozen before
question authoring. Passing permits only a local implementation probe on the 13
known synthesis targets; no fact, deployment or production status changes.
