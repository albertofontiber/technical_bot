# S153 application-bound typed-relation transport

S152's third single-chunk call returned two outer containers carrying the same
correct chunk ID. All seven claims validate after an offline merge, proving that
the redundant model-authored identity container—not claim semantics—caused the
failure. S153 removes both fields from model output. Each call returns only a
claims array; the application binds the immutable chunk ID before validating
quotes and generating claim IDs.

Every provider receipt is checkpointed before validation, there are no retries,
and extraction remains question-blind. This is the final transport iteration of
the typed-relation pilot: it must complete all 51 chunks and cover all 13 target
relations or the line closes. Passing permits only a fresh independent cohort.
