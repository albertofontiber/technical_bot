# S149 selector-only target probe

S148 permits a local implementation probe of the general evidence-ID selector.
S149 makes four cheap Haiku calls over the already frozen served contexts for
cat018, hp002, hp011 and hp017. It does not generate answers. The 13 currently
missing synthesis relations are used only as a local coverage oracle after each
selection; the selector sees only the technician's question and immutable
source units. All 13 relation anchor sets must be present before any answer call
is permitted. Unknown IDs, more than six IDs, drift or a partial result fail
closed. No retrieval, rerank, database or production state is touched.
