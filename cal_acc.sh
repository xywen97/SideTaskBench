#!/usr/bin/env bash
set -euo pipefail

# Edit only these paths when experiment directories change. Paths are relative to this file.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${ROOT_DIR}/coding_runs"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/metric_outputs}"

cd "${ROOT_DIR}"
python3 -m compute_bench.compute_metrics \
  --output "${OUTPUT_DIR}" \
  --main-repeat 1 \
  --main-run DeepSeek-V4-Flash clean "${RUNS_DIR}/clean_unified_deepseek-v4-flash" \
  --main-run DeepSeek-V4-Flash length_control "${RUNS_DIR}/length_control_unified_deepseek-v4-flash-r1" \
  --main-run DeepSeek-V4-Flash direct "${RUNS_DIR}/direct_unified_deepseek-v4-flash" \
  --main-run DeepSeek-V4-Flash wrapped "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r1" \
  --main-run DeepSeek-V4-Flash wrapped_boundary "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r1-boundary" \
  --main-run Qwen3.8-Max clean "${RUNS_DIR}/clean_unified_qwen3.8-max" \
  --main-run Qwen3.8-Max length_control "${RUNS_DIR}/length_control_unified_qwen-3.8-max" \
  --main-run Qwen3.8-Max direct "${RUNS_DIR}/direct_unified_qwen-3.8-max" \
  --main-run Qwen3.8-Max wrapped "${RUNS_DIR}/wrapped_unified_qwen-3.8-max-r1" \
  --main-run Qwen3.8-Max wrapped_boundary "${RUNS_DIR}/wrapped_unified_qwen-3.8-max-r1-boundary" \
  --analysis-run DeepSeek-V4-Flash "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r8" \
  --analysis-run Qwen3.8-Max "${RUNS_DIR}/wrapped_unified_qwen-3.8-max" \
  --analysis-run Qwen3.8-Max "${RUNS_DIR}/wrapped_unified_qwen-3.8-max_missing_5" \
  --pass-run DeepSeek-V4-Flash 1 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r1" \
  --pass-run DeepSeek-V4-Flash 4 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r4" \
  --pass-run DeepSeek-V4-Flash 8 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r8"
