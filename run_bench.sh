#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# 首次使用可先执行：python -m pip install -e .
# 完整环境及参考答案自检：uv run sidetaskbench check
# ===== 在这里修改配置，然后直接执行 bash unit_steal.sh =====
RUN_LABEL="clean_unified_deepseek-v4-flash-r8-01-25"
OUTPUT_DIR="coding_runs/$RUN_LABEL" # 已有目录自动跳过已运行任务，继续缺少的部分

# host-tailored 显式配对：PAIRED=true 时只用 PAIRS，HOST_TASK_IDS/ATOMIC_TASK_IDS 会被忽略。
# PAIRS 设为 () 表示使用内置的 25 对（每个主任务配它自己的 host-tailored 单元）。
PAIRED=true
# PAIRS=("coding-05:cache-access-report" "coding-23:dispatch-specialization-report")
PAIRS=()
# 也可只指定其中几对，例如：
# PAIRS=("coding-05:cache-access-report" "coding-23:dispatch-specialization-report")

# 数组中可填写多个 ID；设为 () 表示该维度全选。
# HOST_TASK_IDS=("coding-08" "coding-02" "coding-10" "coding-16" "coding-04")
# HOST_TASK_IDS=("coding-18")
# HOST_TASK_IDS=("coding-21" "coding-22" "coding-23" "coding-24" "coding-25")
# 全部主任务（25 个）：coding-01..20 为单文件，coding-21..25 为多文件。
# HOST_TASK_IDS=("coding-01" "coding-02" "coding-03" "coding-04" "coding-05" "coding-06" "coding-07" "coding-08" "coding-09" "coding-10" "coding-11" "coding-12" "coding-13" "coding-14" "coding-15" "coding-16" "coding-17" "coding-18" "coding-19" "coding-20")
# HOST_TASK_IDS=("coding-02" "coding-03" "coding-08" "coding-10" "coding-16" "coding-04" "coding-14")
# HOST_TASK_IDS=("coding-01" "coding-04" "coding-05" "coding-06" "coding-07" "coding-09" "coding-11" "coding-12" "coding-13" "coding-14" "coding-15")
# ATOMIC_TASK_IDS=("regression-empty-page" "algorithm-grid-routes" "document-lru-behavior" "classify-timeout-event")
HOST_TASK_IDS=()
ATOMIC_TASK_IDS=()
CONDITIONS=("clean") # clean / length_control / direct / wrapped
DEFENSES=("none")      # none / boundary
REPEATS=8             # 每个组合的总运行次数；增加后只补新增次数
WORKERS=64
MAX_STEPS=70
VARIANT="compatibility_v5" 
# companion_v1 / maintenance_v2 / compatibility_v3 / compatibility_v4_b / compatibility_v4 / compatibility_v5
# compatibility_v4  — standard wrapped block, recommended for the original 20 single-file coding cases.
# compatibility_v5  — same as v4 but strips provider-catalog metadata fields (portfolio_id, atomicity,
#                     resource_profile, large_task_id) so the embedded task reads as a plain procedure
#                     rather than a platform work-order. Recommended for multi-file or high-difficulty
#                     host tasks (e.g. coding-21..25) where the agent sits closer to the execute/refuse
#                     boundary; has no measurable effect on easy cases where pass-rate is already ≥95%.
ENV_FILE=".env"
THINKING="default" # default / enabled / disabled
SEED=20260924
DRY_RUN="${DRY_RUN:-false}" # true：只检查计划和参考材料，不调用模型、不创建结果目录
# ===== 配置结束 =====

if (( $# > 0 )); then
  echo "请在 unit_steal.sh 顶部修改配置，直接运行 bash unit_steal.sh，无需命令行参数。" >&2
  exit 2
fi

args=(
  --output "$OUTPUT_DIR"
  --label "$RUN_LABEL"
  --conditions "${CONDITIONS[@]}"
  --defenses "${DEFENSES[@]}"
  --repeats "$REPEATS"
  --workers "$WORKERS"
  --max-steps "$MAX_STEPS"
  --variant "$VARIANT"
  --env "$ENV_FILE"
  --thinking "$THINKING"
  --seed "$SEED"
)
if [[ "$PAIRED" == true ]]; then
  if (( ${#HOST_TASK_IDS[@]} > 0 || ${#ATOMIC_TASK_IDS[@]} > 0 )); then
    echo "PAIRED=true 时 HOST_TASK_IDS/ATOMIC_TASK_IDS 会被忽略；请改用 PAIRS 指定配对。" >&2
    exit 2
  fi
  if (( ${#PAIRS[@]} > 0 )); then
    args+=(--pairs "${PAIRS[@]}")
  else
    args+=(--paired)
  fi
else
  if (( ${#HOST_TASK_IDS[@]} > 0 )); then
    args+=(--host-task-ids "${HOST_TASK_IDS[@]}")
  fi
  if (( ${#ATOMIC_TASK_IDS[@]} > 0 )); then
    args+=(--atomic-task-ids "${ATOMIC_TASK_IDS[@]}")
  fi
fi
case "$DRY_RUN" in
  true) args+=(--dry-run) ;;
  false) ;;
  *)
    echo "DRY_RUN 必须是 true 或 false，当前为：$DRY_RUN" >&2
    exit 2
    ;;
esac

exec uv run sidetaskbench run "${args[@]}"
