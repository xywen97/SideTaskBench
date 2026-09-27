#!/usr/bin/env bash
set -euo pipefail

# Edit only these paths when experiment directories change. Paths are relative to this file.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_DIR="${ROOT_DIR}/coding_runs"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/metric_outputs}"

# --main-run：主表；每个模型至少需要 clean，再添加想比较的 condition。（clean是必须的）
# --analysis-run：参考材料数量及 LLM-call 分析，可删除。
# --pass-run：pass@k 分析，可删除。

# DeepSeek-V4-Flash clean 或者 Qwen3.8-Max clean 是必须的，其他 condition 是可选的。
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
  --analysis-run Qwen3.8-Max "${RUNS_DIR}/wrapped_unified_qwen-3.8-max-r1" \
  --pass-run DeepSeek-V4-Flash 1 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r1" \
  --pass-run DeepSeek-V4-Flash 4 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r4" \
  --pass-run DeepSeek-V4-Flash 8 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r8"


# 可以单独分析：
# 1. 分析 DeepSeek-V4-Flash 的 wrapped 和 wrapped_boundary 的准确率
# cd "${ROOT_DIR}"
# python3 -m compute_bench.compute_metrics \
#   --output "${OUTPUT_DIR}" \
#   --main-repeat 1 \
#   --main-run DeepSeek-V4-Flash clean "${RUNS_DIR}/clean_unified_deepseek-v4-flash" \
#   --main-run DeepSeek-V4-Flash wrapped "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r1" \
#   --main-run DeepSeek-V4-Flash wrapped_boundary "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r1-boundary"

# 2. 分析 Qwen3.8-Max 的 direct 和 wrapped 的准确率
# cd "${ROOT_DIR}"
# python3 -m compute_bench.compute_metrics \
#   --output "${OUTPUT_DIR}" \
#   --main-repeat 1 \
#   --main-run Qwen3.8-Max clean "${RUNS_DIR}/clean_unified_qwen3.8-max" \
#   --main-run Qwen3.8-Max direct "${RUNS_DIR}/direct_unified_qwen-3.8-max" \
#   --main-run Qwen3.8-Max wrapped "${RUNS_DIR}/wrapped_unified_qwen-3.8-max-r1" \

# 3. 分析 Qwen3.8-Max 的 参考材料数量及 LLM-call 分析
# cd "${ROOT_DIR}"
# python3 -m compute_bench.compute_metrics \
#   --output "${OUTPUT_DIR}" \
#   --main-repeat 1 \
#   --main-run Qwen3.8-Max clean "${RUNS_DIR}/clean_unified_qwen3.8-max" \
#   --analysis-run Qwen3.8-Max "${RUNS_DIR}/wrapped_unified_qwen-3.8-max-r1"

# 4. 分析 DeepSeek-V4-Flash 的 pass@k 分析
# cd "${ROOT_DIR}"
# python3 -m compute_bench.compute_metrics \
#   --output "${OUTPUT_DIR}" \
#   --main-repeat 1 \
#   --main-run DeepSeek-V4-Flash clean "${RUNS_DIR}/clean_unified_deepseek-v4-flash" \
#   --pass-run DeepSeek-V4-Flash 1 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r1" \
#   --pass-run DeepSeek-V4-Flash 4 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r4" \
#   --pass-run DeepSeek-V4-Flash 8 "${RUNS_DIR}/wrapped_unified_deepseek-v4-flash-r8"