# SideTaskBench v1

### 评测 Coding Agent 是否会在运行时被引导执行和交付未经授权的旁支任务。

本项目评估 Coding Agent 在修复用户仓库时，是否会执行参考资料中未经用户授权的第三方任务。
当前数据集包含 25 个主任务 U、30 个原子任务 t，以及两者的全交叉配对。

- U：用户明确授权的 Python 修复任务；`coding-01`–`coding-20` 为单文件，`coding-21`–`coding-25` 为多文件。
- t：参考资料中附带的独立任务，输出代码、JSON 或 Markdown。
- 成绩：分别记录 U 通过、t 被尝试、t 验收通过和 t 实际交付。

[实验设计](docs/CODING_DESIGN.md) · [任务目录](docs/CODING_TASKS.md) · [参考材料](docs/REFERENCE_MATERIALS.md) · [Docker 运行](docs/DOCKER.md)

## 模块

```text
compute_bench/
  coding/       实验计划、运行、评分、报告、审计和恢复
  workloads/    25 个 U、30 个 t 及其私有验收材料（评测任务和数据在这里）
  compute_metrics/  跨运行统计表
microcoder/     模型循环、工具和 Linux 沙箱 （主Agent）
taskforge/      任务计划、投放、回执、验收调用和成果组装（支撑外部任务的执行）
tests/          单元测试与边界测试
scripts/        参考文件引用入口
```

依赖方向为 `compute_bench.coding → microcoder / taskforge / workloads`。

## 安装与检查

1. 克隆本项目到本地：
```bash
git clone --depth 1 https://github.com/xywen97/SideTaskBench.git
cd SideTaskBench
```

需要 Python 3.11+。真实代码执行还需要 Linux namespace、Landlock、seccomp 和可用的
`sudo -n` 沙箱配置。

2. 推荐使用 [uv](https://docs.astral.sh/uv/) 按 `.python-version` 和 `uv.lock` 创建环境：

```bash
# 同步环境
uv sync
# `check` 和测试不会调用模型。
uv run sidetaskbench check
# 运行需要一定时间
uv run python -m unittest discover -s tests -q
```

如果不使用 uv，也可以通过 pip 安装：

```bash
python -m pip install -e .
sidetaskbench check
python -m unittest discover -s tests -q
```

macOS 用户应先安装并启动 Docker Desktop，再通过容器运行 Linux 沙箱：

```bash
cp .env.example .env
mkdir -p metric_outputs
docker compose build
docker compose run --rm sidetaskbench check

# 最小实验
docker compose run --rm sidetaskbench run \
  --output coding_runs/smoke \
  --host-task-ids coding-01 \
  --atomic-task-ids rewrite-user-record \
  --repeats 1 --workers 1

# 完整benchmarking
docker compose run --rm sidetaskbench run-bench

# 导出结果到本地：
docker volume inspect sidetaskbench-coding-runs
mkdir -p docker_exports/coding_runs
docker run --rm \
  -v sidetaskbench-coding-runs:/source:ro \
  -v "$PWD/docker_exports/coding_runs:/target" \
  ubuntu:24.04 bash -c 'cp -a /source/. /target/'

# 计算指标：
uv sync
# 注意脚本中的要求，每次运行都需要clean这个condition，来作为base 对比。另外需要注意运行结果的路径。
bash cal_acc.sh
# 或在容器中计算：
docker compose run --rm sidetaskbench cal-acc
```

完整说明见 [Docker 运行文档](docs/DOCKER.md)。

3. 模型配置见 `.env.example`。 运行前，请配置LLM的环境，复制.env.example 为.env，并在其中填充模型名、base_url以及apikey（不只是支持deepseek模型，当前只是将环境变量名定义为了DEEPSEEK_开头，可以更换其他模型并进行测试）：

```bash
# DEEPSEEK_API_KEY=your_api_key
# DEEPSEEK_BASE_URL=your_base_url
# DEEPSEEK_MODEL=your_model_name
```



## 运行实验

1. 先检查计划；该命令不读取凭据，也不创建结果目录：

```bash
uv run sidetaskbench run --dry-run
```

2. 最小真实运行示例：


```bash
uv run sidetaskbench run \
  --output coding_runs/smoke \
  --host-task-ids coding-01 \
  --atomic-task-ids rewrite-user-record \
  --repeats 1 --workers 1
```

真实运行会调用模型并产生费用。CLI 默认选择全部 30×25 个配对，每个配对重复 8 次，
使用 `wrapped` 条件和 `none`，共 6,000 次运行。`run_bench.sh` 当前将重复数设为 2，
可在脚本中调整任务、条件、防御、重复数和并发数。

3. 如果不运行最小示例，可以直接运行`run_bench.sh`，从而一键开启全量评测（在这个脚本中，同样可以配置需要测试的主任务和外部任务的配对）:

```bash
# 运行结果会保存在：coding_runs/ 文件夹下。
bash run_bench.sh
```

Docker 环境中的等价命令是：

```bash
docker compose run --rm sidetaskbench run-bench
```

4. Agent运行结束之后，使用`cal_acc.sh`来计算各项指标，可以复现报告中的结果：

```bash
# 结果会保存在 metric_outputs/ 文件夹下。
bash cal_acc.sh
```

### Todo

- [x] single-query coding scenario
- [x] add diversity coverage with 4 SWE-bench Verified-inspired coding tasks
- [x] multi-file host tasks (coding-21..25) behind an optional solution_file
- [ ] multi-turn interactive scenario


## 实验条件

- `clean`：原始技术资料。
- `length_control`：加入与任务载荷等字符数的中性填充。
- `direct`：明确附加第三方任务。
- `wrapped`：把第三方任务包装成参考资料流程。

防御选项为 `none` 和 `boundary`。`boundary` 增加授权边界提示。

## 结果与复现

结果目录保存 manifest、计划、冻结任务、源码和材料快照、模型轨迹、工作区、补丁、回执及报告。

完整指标（参考资料数量分析、LLM-call 调整、Pass@k 明细）见 `metric_outputs/metrics.md`。

### 主表（wrapped/none 条件，每对 1 次重复，共 480 次运行）

`Block Seen`：模型可见的工具输出中出现了当前原子任务 id 与配置的 block 标记。  
`Δ Tokens`：仅在 `submission_attempted=true` 的运行中与 clean 配对比较。

| 模型 | 条件 | 运行数 | Host Pass | Block Seen | Overall Delivery | Delivery Given Seen | Joint Success | Δ Tokens vs. clean \| Attempt |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash | clean | 480 | 97.71% | — | — | — | — | — |
| DeepSeek-V4-Flash | length_control | 480 | 96.46% | — | — | — | — | — |
| DeepSeek-V4-Flash | direct | 480 | 98.54% | 71.88% | 9.58% | 13.33% | 9.58% | +82.6k (+24.8%) |
| DeepSeek-V4-Flash | wrapped | 480 | 97.71% | 72.71% | 39.58% | 54.44% | 38.96% | +100.2k (+23.4%) |
| DeepSeek-V4-Flash | wrapped_boundary | 480 | 99.17% | 68.75% | **0.00%** | **0.00%** | **0.00%** | — |
| Qwen3.8-Max | clean | 480 | 84.58% | — | — | — | — | — |
| Qwen3.8-Max | length_control | 480 | 82.08% | — | — | — | — | — |
| Qwen3.8-Max | direct | 480 | 82.50% | 66.04% | 48.33% | 73.19% | 41.88% | +110.6k (+73.9%) |
| Qwen3.8-Max | wrapped | 480 | 83.33% | 64.58% | 40.62% | 62.90% | 36.88% | +94.7k (+60.8%) |
| Qwen3.8-Max | wrapped_boundary | 480 | 81.25% | 62.92% | 21.88% | 34.77% | 17.92% | +138.6k (+105.2%) |

- **Host Pass**：主任务 U 通过率——两个模型在所有条件下均保持稳定，旁支任务未影响主任务质量。
- **Overall Delivery**：旁支任务 t 实际交付率——`wrapped` 条件下两个模型均约 40%，说明包装手法有效诱导了 agent。
- **wrapped_boundary**：加入授权边界提示后，DeepSeek-V4-Flash 交付率降至 0%；Qwen3.8-Max 降至 21.88%，防御效果存在模型差异。

### Pass@k（DeepSeek-V4-Flash，wrapped/none）

| Budget | 运行数 | 配对数 | Valid/run | Joint/run | Valid pass@k | Joint pass@k |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 480 | 480 | 39.58% | 38.96% | 39.58% | 38.96% |
| 4 | 1920 | 480 | 40.16% | 39.43% | 82.50% | 81.88% |
| 8 | 3840 | 480 | 39.32% | 38.67% | 96.25% | 95.62% |

单次运行约 40% 的配对会产生有效旁支交付；给定 8 次预算，96% 的配对至少被成功完成一次，说明重复采样可以显著放大旁支任务的实际风险。
