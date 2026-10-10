#!/usr/bin/env bash
# run_bench_levels.sh — 分级相似度 benchmark 运行脚本
#
# 设计：以 host task 为中心，每个 host task 在 L3/L2/L1/L0 四个相似度
#       级别下各配 3 个 side task，共 25×4×3=300 个固定配对。
#       配对权威来源：pairs_levels.json（status=implemented 的条目）。
#
# 与 run_bench.sh 的关系：
#   - 入口独立，互不影响，输出目录严格隔离（coding_runs_levels/）
#   - 复用同一套 sidetaskbench run 命令和所有环境变量
#   - 不修改任何现有数据目录或 catalog 文件
#
# 用法：直接执行  bash run_bench_levels.sh
#       干跑预览  DRY_RUN=true bash run_bench_levels.sh
#       只跑某级  LEVELS="L3" bash run_bench_levels.sh
#       只跑某组  HOST_FILTER="coding-09 coding-10" bash run_bench_levels.sh
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# ===== 配置区（在这里修改，直接执行） =====
RUN_LABEL="levels_v1_wrapped_none_no-context"
OUTPUT_BASE="coding_runs_levels/$RUN_LABEL"

CONDITIONS=("wrapped")          # clean / length_control / direct / wrapped
DEFENSES=("none")               # none / boundary
REPEATS=4                       # 每对的运行次数；增加后只补新增次数
WORKERS=64
MAX_STEPS=70
VARIANT="compatibility_v5"
ENV_FILE=".env"
THINKING="default"              # default / enabled / disabled
SEED=20260924

# NO_COMPATIBILITY_CONTEXT=true 时，不在参考文档中预告 side task 的描述，
# 用于消融实验：去除 compatibility_context 的预告效果，单独测量领域相似性的影响。
# 分级实验必须设为 true：某个配对拿到的预告来自该主任务的 host-tailored 单元，
# 与实际配对的 side task 往往对不上，会混入额外变量。
# 对照组（原有行为）：NO_COMPATIBILITY_CONTEXT=false（默认）
# 消融组（去除预告）：NO_COMPATIBILITY_CONTEXT=true
NO_COMPATIBILITY_CONTEXT=true

# 要运行的相似度级别，可以是 L3 L2 L1 L0 的任意子集
# 留空表示全部四级
LEVELS="${LEVELS:-L3}"

# host task 过滤器：空=全部25个，否则只跑指定的 host task
# 示例：HOST_FILTER="coding-09 coding-10 coding-12"
HOST_FILTER="${HOST_FILTER:-}"

DRY_RUN="${DRY_RUN:-false}"
# ===== 配置区结束 =====

# ---------- 内部工具函数 ----------
log()  { echo "[run_bench_levels] $*"; }
die()  { echo "[run_bench_levels] ERROR: $*" >&2; exit 1; }

require_cmd() {
    command -v "$1" &>/dev/null || die "$1 不在 PATH 中，请先安装或激活环境"
}
require_cmd python3
require_cmd uv

# ---------- 从 pairs_levels.json 提取 implemented 配对 ----------
# 输出格式：每行  LEVEL HOST_TASK_ID:SIDE_TASK_ID
extract_pairs() {
    python3 - <<'PYEOF'
import json, sys

try:
    data = json.load(open("pairs_levels.json"))
except FileNotFoundError:
    print("ERROR: pairs_levels.json not found", file=sys.stderr)
    sys.exit(1)

for entry in data["pairs"]:
    host = entry["host_task_id"]
    for level in ["L3", "L2", "L1", "L0"]:
        for t in entry["levels"].get(level, []):
            if t.get("status") == "implemented":
                print(f"{level} {host}:{t['task_id']}")
PYEOF
}

# ---------- 验证配对在 catalog 中存在 ----------
validate_pairs() {
    python3 - "$@" <<'PYEOF'
import json, sys

catalog = json.load(open("compute_bench/workloads/provider_atomic/cases/catalog.json"))
all_ids = set()
for lg in catalog["large_tasks"]:
    all_ids.update(lg["task_ids"])

bad = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    _, pair = line.split(" ", 1)
    _, side = pair.split(":", 1)
    if side not in all_ids:
        bad.append(side)

if bad:
    print("ERROR: 以下 side task 不在 catalog 中，请检查 pairs_levels.json:", file=sys.stderr)
    for b in sorted(set(bad)):
        print(f"  {b}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ---------- 主流程 ----------

# 1. 提取全部 implemented 配对，并通过 catalog 验证
ALL_PAIRS=$(extract_pairs)
echo "$ALL_PAIRS" | validate_pairs

# 2. 按级别和 host 过滤
# 将过滤条件写入临时文件，避免子 shell 环境变量传递问题
_TMP_PAIRS=$(mktemp)
echo "$ALL_PAIRS" > "$_TMP_PAIRS"

FILTERED=$(python3 -c "
import sys

level_filter = sys.argv[1].split() if sys.argv[1] else []
host_filter  = sys.argv[2].split() if sys.argv[2] else []
pairs_file   = sys.argv[3]

with open(pairs_file) as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        parts = line.split(' ', 1)
        if len(parts) != 2:
            continue
        level, pair = parts
        host = pair.split(':', 1)[0]
        if level_filter and level not in level_filter:
            continue
        if host_filter and host not in host_filter:
            continue
        print(pair)
" "$LEVELS" "$HOST_FILTER" "$_TMP_PAIRS")

rm -f "$_TMP_PAIRS"
PAIR_COUNT=$(echo "$FILTERED" | grep -c . || true)

if [[ "$PAIR_COUNT" -eq 0 ]]; then
    die "过滤后没有可运行的配对。请检查 LEVELS 和 HOST_FILTER 配置。"
fi

log "配对总数: $PAIR_COUNT  级别: $LEVELS  host filter: '${HOST_FILTER:-all}'"
log "输出目录: $OUTPUT_BASE"
log "条件: ${CONDITIONS[*]}  防御: ${DEFENSES[*]}  重复: $REPEATS  workers: $WORKERS"

# 3. 按 level 分组运行（每个 level 一个独立输出目录，方便后续分层分析）
declare -A LEVEL_DIRS=( [L3]="l3" [L2]="l2" [L1]="l1" [L0]="l0" )

# 临时文件用于循环内的 per-level 过滤（与步骤 2 复用同一个文件）
_TMP_PAIRS_LOOP=$(mktemp)
echo "$ALL_PAIRS" > "$_TMP_PAIRS_LOOP"

for LEVEL in $LEVELS; do
    LEVEL_PAIRS=$(python3 -c "
import sys
level_filter = sys.argv[1].split()
host_filter  = sys.argv[2].split() if sys.argv[2] else []
with open(sys.argv[3]) as fh:
    for line in fh:
        line = line.strip()
        if not line: continue
        parts = line.split(' ', 1)
        if len(parts) != 2: continue
        level, pair = parts
        host = pair.split(':', 1)[0]
        if level not in level_filter: continue
        if host_filter and host not in host_filter: continue
        print(pair)
" "$LEVEL" "$HOST_FILTER" "$_TMP_PAIRS_LOOP")
    LEVEL_COUNT=$(echo "$LEVEL_PAIRS" | grep -c . || true)
    [[ "$LEVEL_COUNT" -eq 0 ]] && continue

    LEVEL_DIR="${OUTPUT_BASE}/${LEVEL_DIRS[$LEVEL]}"
    LEVEL_LABEL="${RUN_LABEL}_${LEVEL}"

    log ""
    log "=== 级别 $LEVEL: $LEVEL_COUNT 个配对 → $LEVEL_DIR ==="

    # 将配对转为 --pairs 参数数组
    PAIRS_ARGS=()
    while IFS= read -r pair; do
        [[ -n "$pair" ]] && PAIRS_ARGS+=("$pair")
    done <<< "$LEVEL_PAIRS"

    CMD_ARGS=(
        --output  "$LEVEL_DIR"
        --label   "$LEVEL_LABEL"
        --pairs   "${PAIRS_ARGS[@]}"
        --conditions  "${CONDITIONS[@]}"
        --defenses    "${DEFENSES[@]}"
        --repeats     "$REPEATS"
        --workers     "$WORKERS"
        --max-steps   "$MAX_STEPS"
        --variant     "$VARIANT"
        --env         "$ENV_FILE"
        --thinking    "$THINKING"
        --seed        "$SEED"
    )

    case "$DRY_RUN" in
        true)  CMD_ARGS+=(--dry-run) ;;
        false) ;;
        *)     die "DRY_RUN 必须是 true 或 false" ;;
    esac

    case "$NO_COMPATIBILITY_CONTEXT" in
        true)  CMD_ARGS+=(--no-compatibility-context) ;;
        false) ;;
        *)     die "NO_COMPATIBILITY_CONTEXT 必须是 true 或 false，当前为：$NO_COMPATIBILITY_CONTEXT" ;;
    esac

    log "uv run sidetaskbench run ${CMD_ARGS[*]}"
    uv run sidetaskbench run "${CMD_ARGS[@]}"
done

rm -f "$_TMP_PAIRS_LOOP"

log ""
log "全部级别运行完成。结果在 $OUTPUT_BASE/"
log ""
log "下一步：使用 cal_acc_levels.sh 计算分级指标。"
