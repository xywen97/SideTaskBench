# SideTaskBench v1

### 评测 Coding Agent 是否会在运行时被引导执行和交付未经授权的旁支任务。

本项目评估 Coding Agent 在修复用户仓库时，是否会执行参考资料中未经用户授权的第三方任务。
当前数据集包含 16 个主任务 U、30 个原子任务 t，以及两者的全交叉配对。

- U：用户明确授权的 Python 修复任务。
- t：参考资料中附带的独立任务，输出代码、JSON 或 Markdown。
- 成绩：分别记录 U 通过、t 被尝试、t 验收通过和 t 实际交付。

[实验设计](docs/CODING_DESIGN.md) · [任务目录](docs/CODING_TASKS.md) · [参考材料](docs/REFERENCE_MATERIALS.md) · [Docker 运行](docs/DOCKER.md)

## 模块

```text
compute_bench/
  coding/       实验计划、运行、评分、报告、审计和恢复
  workloads/    16 个 U、30 个 t 及其私有验收材料（评测任务和数据在这里）
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

真实运行会调用模型并产生费用。CLI 默认选择全部 30×16 个配对，每个配对重复 8 次，
使用 `wrapped` 条件和 `none`，共 3,840 次运行。`run_bench.sh` 当前将重复数设为 1，
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
- [ ] 8 harder coding task (swe-bench like)
- [ ] multi-turn interactive scenario


## 实验条件

- `clean`：原始技术资料。
- `length_control`：加入与任务载荷等字符数的中性填充。
- `direct`：明确附加第三方任务。
- `wrapped`：把第三方任务包装成参考资料流程。

防御选项为 `none` 和 `boundary`。`boundary` 增加授权边界提示。

## 结果与复现

结果目录保存 manifest、计划、冻结任务、源码和材料快照、模型轨迹、工作区、补丁、回执及报告。
