# S155 question-conditioned claim map design v1

S155 is the sole bounded successor permitted by the S154 gate. It preserves
S154's question-conditioned, one-chunk map architecture, 51 target jobs,
14 pre-existing independent jobs, exact-quote validation, no retries and
post-checkpoint oracle isolation.

The only semantic-output-independent correction is transport cardinality:

- the application cap increases from 10 to 16 claims per chunk;
- the system instruction explicitly says “at most sixteen claims” because the
  provider schema does not support `maxItems`;
- output budget rises from 1,600 to 2,200 tokens;
- actual spend remains capped below $2.50.

No S154 claim text was inspected before freezing this version. All coverage
and independent gates are unchanged: at least 11/13 target relations, at least
80% independent gold coverage, at least 80% useful-claim precision, and 13/13
before any composition probe. Failure closes this architecture permanently.

