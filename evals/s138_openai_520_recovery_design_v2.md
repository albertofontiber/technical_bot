# S138 v2 - bounded recovery after pre-response OpenAI 520

Status: recovery design frozen after the failed S138-v1 transport attempt and
before any new provider call.

## Incident

The S138-v1 preflight passed. Its first paid step, the Sol primary request,
ended with an OpenAI/Cloudflare HTTP 520 marked retryable. The client returned
no model response, response ID, token usage, or judge output. Therefore no S138
semantic result exists and none of the three Fable calls ran.

The incident is infrastructure failure, not an adverse semantic judgement. It
cannot be silently retried under the v1 zero-retry contract.

## Recovery contract

Recovery reuses the byte-identical frozen packet, private mapping, rubric,
models, caps, validators, aggregation and v1 runner. It authorizes exactly one
new logical execution attempt. It is legal only while all v1 judge-response
and aggregate outputs remain absent; this prevents replaying a completed or
partially completed measurement.

If the recovery attempt raises another provider/transport exception, the
wrapper persists a sanitized failure receipt and stops. No further retry is
authorized. Structured but invalid/truncated paid responses continue to use
the v1 runner's `PAID_INVALID_NO_RETRY` receipts.

## Cost treatment

The failed 520 reported no usage. For budget safety, recovery nevertheless
reserves USD 0.93485625, as if the failed Sol request had consumed its counted
34,377 input tokens and the full 24,000-token output cap. Adding that reserve
to the v1 measured worst case yields USD 5.88938250 for S138 and USD 9.40325000
including S137, below the stricter S138 USD 10 ceiling.

This recovery changes no retrieval, chunks, facts, thresholds, production data
or deployment state.
