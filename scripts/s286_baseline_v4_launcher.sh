#!/usr/bin/env bash
# s286 — LA re-baseline (vara v4, config-de-ship) — línea de salida del OBJETIVO MARCO.
# Config = paridad prod + los levers medidos del arco (guard A'+C', conducta c/d/e).
# Los flags equivalentes se encienden en Railway en el lote de ONs de Alberto tras el verde.
set -euo pipefail
cd "$(dirname "$0")/.."

export CHUNKS_TABLE=chunks_v2
export HYQ_TABLE=on
export VISUAL_ASSETS_REGISTRY=on
export COVERAGE_RELEASE_PROFILE=coverage_c1_v4
export IDENTITY_RESOLVE=on
export IDENTITY_RESOLVE_POLICY=replace
export MUST_PRESERVE_CONTRACT=on
# vara
export JUDGE_VARA=v4
# guard hp018 (A/B GO 0/20)
export ANTI_DIAGRAM_INVENTION=on
export WIRING_TOPOLOGY_GUARD=on
# conducta (A/B adjudicado)
export GENERATOR_DIRECT_FIRST=on
export GENERATOR_FOLLOWUPS=off
export VISUAL_ASSETS_LISTING_GATE=on

export OUTPUT_OVERRIDE=evals/bot_vs_gold_39_baseline_shipconfig_v4judge_s286.yaml
python scripts/test_bot_vs_gold.py
