# S169 transport-only adversarial review v2

V1 stopped before any paid judge call because Anthropic's structured-output
schema rejects JSON Schema integer `minimum` and `maximum` keywords. V2 changes
only that transport: the provider schema accepts integers and the runner applies
the identical 1–30/1–30/0–100 bounds locally after parsing.

The packet, system prompt, options, model vintages, xhigh effort, convergence
rule, output limits, cost ceiling, zero retries and zero additional rounds are
unchanged from v1. V2 is still one Sol call plus one Fable call and can authorize
only design of a new local independent experiment.
