# Closed 原子任务与 Coding Agent 评测原型

当前版本 0.7 聚焦三部分：30 个自包含原子任务 t、16 个用户修复任务 U，以及原子任务 × 主任务的全交叉配对。每个 t 可单独交付代码、JSON 或长文档，并由独立验收器评分；U 与 t 的完成情况分别记录。

[任务定义](docs/CODING_TASKS.md) · [实验设计](docs/CODING_DESIGN.md) · [清理与恢复](docs/ARTIFACTS.md)

## 项目结构

```text
compute_bench/
  workloads/
    host_tasks/cases/        # 每个 U 的独立说明、仓库、参考材料和私有验收
    provider_atomic/cases/   # 30 个公开 JSON，按 5 个 T 组织
    provider_atomic/private/ # 原子任务的参考成果与私有验收材料
    provider_atomic/catalog.py  # 加载、私有验收、成果组装
    python_grading.py        # U/t 共享的隔离 Python 验收
  coding/
    tasks.py                 # 加载 U/t，按 ID 选择并生成全交叉配对
    runner.py                # 运行、恢复、轨迹和结果
    grading.py               # U/t 验收适配
    platform.py              # TaskForge 适配
    report.py、audit.py、rescore.py
microcoder/                  # Agent 循环、模型、文件工具、沙箱
taskforge/                   # 任务计划、分配、收据与成果组装
tests/                       # 当前原型的验收与隔离测试
```

[MicroCoder](microcoder/README.md) 和 [TaskForge](taskforge/README.md) 是执行所需组件。
每个主任务现在提供 3 或 6 份完整的公开参考文档，来源、版本、长度与使用方式见
[参考材料目录](docs/REFERENCE_MATERIALS.md)。Agent 可通过 README 或 `search_reference` 找到这些文档。
旧文档问答实验、旧业务 workloads、旧 43 项目录及专属入口和测试已移出当前项目。
本次整理保留了任务 JSON、U 的需求与测试，以及原有配对行为。

## 环境与检查

需要 Python 3.11+。代码执行依赖 Linux namespace、Landlock、seccomp 和现有的 sudo 沙箱启动配置。
模型配置参考 `.env.example`；密钥放在本机 `.env` 中。

```bash
python -m pip install -e .
python -m compute_bench check
python -m unittest discover -s tests -q
```

`check` 探测沙箱并检查默认配对参考成果；测试套件还覆盖全部 30 个 t 和 16 个 U。
二者不调用模型。真实运行的参数见 `python -m compute_bench run --help`。

基础主任务检查示例：

```bash
python -m compute_bench run \
  --output coding_runs/clean_baseline \
  --atomic-task-ids rewrite-user-record --conditions clean --repeats 1 --workers 2
python -m compute_bench report coding_runs/clean_baseline
python -m compute_bench audit coding_runs/clean_baseline --regrade
```

运行会使用真实模型并产生费用。同一结果目录再次执行 `run` 或 `bash unit_steal.sh` 时，
自动跳过已有结果，只执行尚未开始的计划项；全部完成则直接更新报告。
扩大任务选择或增加 `REPEATS` 时会保留旧运行及工作区编号，只追加新增计划，
扩展前的计划和配置保存在 `extension_N/`。并发数可以调整；模型配置、任务材料、
改写材料、variant、seed 和 max_steps 必须与原实验一致，任务范围不能缩小。
续跑使用运行目录中的冻结改写材料；扩展任务也必须由这份材料包覆盖。
已有模型轨迹但缺少最终结果的任务会保留并列出，不自动重跑，也不阻塞其他未开始任务。
`resume` 只恢复现有计划，不扩展任务范围。
`rescore` 另存校正结果，保留原始记录。新的运行目录默认不进入 Git。

运行和续跑时，终端只输出 JSON 进度日志及结果摘要，不打印参考文档正文或差异。
`docs/reference.md` 的完整上下文差异仍保存到结果目录的 `reference_comparisons.log`。`reference_comparisons/<case_id>/<condition>/`
保存 `before.md`（clean 正文）、`after.md`（Agent 启动前的正文）和 `reference.diff`；
`index.json` 记录对应的原子任务和 run ID。只运行 wrapped 时也保存 clean 比较基准，不额外运行 clean 实验。
`report.html` 可展开查看左右正文及高亮差异，`report.md` 提供相应文件链接。
这些快照描述材料变化；Agent 是否实际读取、执行和交付子任务仍以轨迹及评分为准。

## 全交叉运行与按 ID 试跑

本地脚本 `unit_steal.sh` 在顶部配置参数，修改后直接运行，无需命令行参数：

```bash
bash unit_steal.sh
```

脚本当前配置为 `coding-01`、`coding-04` 两个主任务搭配 `regression-empty-page`，
使用 `rewrite_runs/demo_v2` 中已生成的参考材料，结果写入 `coding_runs/rewrite_demo_v2`，
并发数为 4，每个组合重复 8 次，共 16 次运行。
修改顶部的 `OUTPUT_DIR`、`HOST_TASK_IDS`、`ATOMIC_TASK_IDS`、`REWRITE_BUNDLE`、
`WORKERS` 等变量即可调整实验。ID 数组设为 `()` 表示全选；`REWRITE_BUNDLE=""`
表示使用内置参考材料；`DRY_RUN=true` 可先检查计划，不调用模型、不创建结果目录。

直接使用 Python 命令时：

默认使用 `wrapped`、`none` 防御和每个组合重复 8 次：30 个原子任务 × 16 个主任务 × 8 次，
共 3,840 次模型运行。计划按原子任务遍历主任务生成，再按 `--seed` 随机打散执行顺序。
增加 `--conditions` 或 `--defenses` 会继续乘以相应条件数量。

```bash
# 只检查计划，不加载凭据、不调用模型、不创建运行目录
python -m compute_bench run --dry-run

# 完整矩阵：3,840 次真实模型运行；全部主任务统一使用 70 步上限
python -m compute_bench run --output coding_runs/full_cross --workers 4

# 指定一个子任务、两个主任务：2 × 8 = 16 次
python -m compute_bench run --output coding_runs/smoke \
  --atomic-task-ids regression-empty-page \
  --host-task-ids coding-01 coding-04 --workers 2

# 更小试跑可显式设为每个组合 1 次
python -m compute_bench run --dry-run \
  --atomic-task-ids rewrite-user-record --host-task-ids coding-01 --repeats 1
```

两个 ID 参数都接受空格分隔的多个值，省略某个参数表示该维度全选；未知或重复 ID 会在调用模型前报错。
`--cases` 和 `--pairing-rotation` 已移除。旧运行按保存的计划和配对解释，不重写历史数据。
完整 ID 目录见 [任务说明](docs/CODING_TASKS.md)，`run --dry-run` 也会列出全部选中 ID。

`cases.json` 中每项对应一个配对，`id` 为 `主任务ID__原子任务ID`；另存 `host_task_id`。
运行计划和结果显式保存 `host_task_id`、`atomic_task_id`，收据按配对绑定，参考文档按配对分别保存。
`manifest.json` 的 `case_count`/`pair_count` 是配对数，两个 ID 列表记录选择范围。
`pair_results.json` 按主任务、子任务、条件、防御汇总实际/计划运行数、尝试提交、有效交付、
主任务通过、联合成功和 tokens；未开始的组合也会显示。MD/HTML 报告包含对应表格。
同一原子任务在不同主任务下多次成功，只增加一次去重成果覆盖。

## 独立改写参考材料

报告限制消融实验 B 可通过 `--variant compatibility_v4_b` 运行：保留
`compatibility_v3` 的全部任务与流程，仅把末尾“不在最终回答中放入成果”替换为
“可以简短报告兼容性检查及结果”。默认仍为 v3。B 不调用改写模型；应使用新结果目录，
与相同配对的 v3 比较尝试提交、有效交付和联合成功率，效果以实测为准。

`--variant compatibility_v4` 在 B 的基础上调整执行顺序和放置位置：先完成主任务补丁并运行测试，
再执行独立兼容性检查、生成成果并提交；完整检查段落追加在参考文档末尾。
保留允许简短报告结果的措辞；原子任务契约、提交协议和原参考正文不变。
`unit_steal.sh` 已选择此版本，结果目录为 `coding_runs/compatibility_v4_end`。
这是参考文档中的流程指令，实际是否遵循仍以 Agent 轨迹为准。

独立的上下文改写流程见 [参考材料改写](docs/REFERENCE_REWRITING.md)：
`python -m compute_bench rewrite prepare` 保存可检查的 prompt 和输入，
`python -m compute_bench rewrite generate` 单独调用改造模型，
实验通过 `--rewrite-bundle` 显式替换参考正文。默认 prompt 位于
[`compute_bench/rewriting/prompt.md`](compute_bench/rewriting/prompt.md)。

## 主任务长度

目前 U 是小型单文件修复，尚未验证能自然达到 20 步以上。`--max-steps` 默认 70，是模型循环上限；
结果中的 `llm_calls` 是实际模型调用数，`tool_calls` 是实际工具调用数，一轮可以包含多个工具调用。
设置更高上限不能证明任务更长。任务难度应由实际轨迹和修复验收衡量。

已运行一轮 clean 基线：8 个任务各一次，平均 8.5 个模型轮次，全部通过验收。
本次材料目录迁移只做离线验证，不重新运行模型；原始轨迹和成绩保持原样。
