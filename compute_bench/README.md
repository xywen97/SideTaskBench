# compute_bench

`compute_bench` 是实验层：定义任务和实验条件，编排真实运行，执行独立验收，并保存、报告、审计证据。Agent 的实现归 [MicroCoder](../microcoder/README.md)，第三方任务平台归 [TaskForge](../taskforge/README.md)。本包通过少量适配器连接它们，不复制模型客户端、Agent 循环、通用工具、沙箱或 HTTP 收集器。

新增 [workloads/](workloads/README.md) 定义四个完整的大任务 T：[API 迁移](workloads/cases/api_migration/task.json)、[回归测试生成](workloads/cases/regression_tests/task.json)、[订单对账](workloads/cases/order_reconciliation/task.json)、[目录归一](workloads/cases/catalog_normalization/task.json)。每个案例以 `task.json` 为权威任务定义，静态公开文件在同目录的 `materials/`；Python 后端保留 seed 数据生成、私有测试、参考成果及组装策略。通用成果协议属于 TaskForge，业务规则与评分属于本实验层。

[真实验证记录](../verification_runs/workloads/README.md) 保留全部 20 条新增轨迹，与原有 coding 矩阵分开统计。

## 从这里 review

原子化首版使用四个 `*-atomic` 案例，定义仍在 `workloads/cases/*/task.json`。每个 t 的 `packet` 包含全部输入和输出约定，`dependencies`、`material_paths` 均为空；`packets.py` 校验这一结构，运行器只分发当前包，不向主 Agent 工作区复制外包项目。四案分别拆成 3 个函数、9 个测试场景、11 个订单／事件结果和 20 个商品观察值，详见[原子任务说明](workloads/README.md#原子化首版主线)。

```text
compute_bench/
├── cli.py、__main__.py、__init__.py  # 默认 coding 命令入口
├── io.py                           # 实验 JSON 文件写入
├── coding/
│   ├── tasks.py                    # 八个用户修复仓库及公开/私有验收
│   ├── documents.py                # 实验参考内容与包装参数
│   ├── environment.py              # 仓库夹具、MicroCoder 接触指标适配
│   ├── platform.py                 # TaskForge 公开契约与私有评分器绑定
│   ├── runner.py                   # 固定矩阵、会话、Agent、验收及记录
│   ├── grading.py                  # 隔离验收与纯函数候选范围检查
│   ├── provenance.py               # 源码快照及来源检查
│   ├── report.py                   # 从记录计算统计与生成报告
│   ├── audit.py                    # 原始/校正证据核验、可选重新执行验收
│   ├── rescore.py                  # 独立校正评分，不覆盖原始记录
│   └── cli.py、__main__.py          # coding-bench 与兼容入口
└── workloads/
    ├── provider_atomic/            # 新 provider portfolio：5 T / 30 t
    │   ├── cases/*/*.json          # 30 个公开 t 的权威定义
    │   └── catalog.py              # 加载校验、私有验收与价值组装
    ├── cases/*/task.json           # 目标、贡献规格、材料声明及后端 ID
    ├── cases/*/materials/          # README、SDK、公开实现与测试等静态材料
    ├── definitions.py、registry.py # JSON 校验/加载与受控后端白名单
    ├── packets.py                 # 闭合工作单元的输入/输出契约校验
    ├── evaluators/                # seed 生成、私有验收、参考成果及组装
    └── runner.py、audit.py、cli.py # 大任务运行、证据审计与命令入口
```

建议先看 [tasks.py](coding/tasks.py)，了解到底验收什么，再看 [runner.py](coding/runner.py) 的运行顺序；两侧边界分别看 [environment.py](coding/environment.py) 与 [platform.py](coding/platform.py)。判定是否可信，继续读 [grading.py](coding/grading.py)、[provenance.py](coding/provenance.py) 和 [audit.py](coding/audit.py)。

四个大任务从上面的 `task.json` 开始 review，再查看所指向的公开材料和 `evaluators/`。JSON 的 `materials` 映射静态文件，`generated_materials` 声明由已登记 `generator_id` 按 seed 生成的公开文件；`bindings` 把业务角色对应到任务 ID、输出路径等参数。加载器只接受 `registry.BACKENDS` 中的后端，不从 JSON 执行任意 Python 导入。字段与扩展流程见 [workloads 说明](workloads/README.md#任务文件与后端)。

数据流是：冻结实验计划 → 准备主任务仓库 → TaskForge 分配参考与接收端 → MicroCoder 执行用户修复 → 独立验收主任务及实际交付 → 保存记录与报告。任务正确答案、私有测试和统计指标属于实验层，不能复制进 Agent 工作区或 TaskForge 的公开契约。

## 命令

从 PoC 目录运行：

```bash
python -m pip install -e .
compute-bench --help
compute-bench check
compute-bench run --output coding_runs/my_pilot \
  --cases 2 --repeats 1 --workers 2
```

**默认 `run`、`report`、`audit` 等命令现在都属于 coding 主线。** 以下编码入口等价，参数含义一致：

```bash
compute-bench run ...
python -m compute_bench run ...
python -m compute_bench coding run ...
coding-bench run ...
python -m compute_bench.coding run ...
```

保留的 `coding` 前缀只做命令转发。旧文档问答实验使用独立入口 `python -m legacy.document_v1 ...`；其结果目录不要交给 coding 的报告或审计命令。

大任务的原有 CLI 保持兼容：

```bash
python -m compute_bench workloads list
python -m compute_bench workloads packet api-migration-atomic rewrite-order-record
python -m compute_bench workloads show api-migration --definition
python -m compute_bench workloads show api-migration --seed 7
python -m compute_bench workloads export api-migration /tmp/migration-export --seed 7
```

`show --definition` 输出原始任务定义；普通 `show` 输出已按 seed 展开的公开实例。`export` 保持现有结构：展开后的 `case.json`、平台 `request.json` 和该 seed 的公开 `materials/`，不包含参考答案或私有验收代码。

| 命令 | 行为 |
|---|---|
| `run` | 使用本地模型配置真实执行固定实验矩阵，输出目录必须为空 |
| `resume` | 仅补本版本尚无模型轨迹的计划项；已有结果保留 |
| `check` | 探测真实沙箱并验收八个 U 配对的参考 artifact，不调用 LLM |
| `report` | 从已有结果重建报告；`--corrected` 选择独立校正评分 |
| `audit` | 核对原始证据；`--corrected` 核对校正产物，`--regrade` 在沙箱复验 |
| `rescore` | 先核对原始证据，再另存校正评分、差异和有效成果 |

`run` 与确有待执行项的 `resume` 会调用配置中的真实模型。其他命令不调用 LLM；`check`、`rescore`、`audit --regrade` 会运行隔离验收代码。默认不设置模型生成 token 上限或累计 token 预算，Agent 循环与 shell 超时仍各自生效。

```bash
compute-bench report coding_runs/validation_main
compute-bench audit coding_runs/validation_main
compute-bench audit coding_runs/validation_main --corrected --regrade
```

## 模块边界与扩展

| 需要修改的内容 | 位置 |
|---|---|
| 八个用户修复题目与主任务验收 | `coding/tasks.py` |
| provider atomic portfolio v1（5 T / 30 t）的公开契约 | `workloads/provider_atomic/cases/<large_task_id>/<task_id>.json` |
| provider portfolio 的私有验收与组装 | `workloads/provider_atomic/` |
| legacy/business atomic suite（4 T / 43 t） | `workloads/cases/*_atomic/task.json`；原 case ID 与 CLI 保持不变 |
| 四个大任务的目标、贡献描述、材料声明、角色绑定 | `workloads/cases/*/task.json` |
| 大任务的公开静态 README、SDK、实现和测试 | `workloads/cases/*/materials/` |
| seed 材料生成、独立业务验收及组装规则 | `workloads/evaluators/`，后端登记在 `workloads/registry.py` |
| 条件、固定参考上下文、矩阵参数 | `coding/documents.py`、`coding/runner.py`、CLI |
| 参考接触指标、第三方契约到评分器的绑定 | `coding/environment.py`、`coding/platform.py` |
| 评分、统计、证据或校正记录 | `coding/grading.py`、`report.py`、`audit.py`、`rescore.py` |
| Agent 提示词、工具与模型循环 | `microcoder/` |
| 通用规划、投放会话、HTTP 接收与组装 | `taskforge/` |

依赖方向为 `compute_bench → microcoder` 和 `compute_bench → taskforge`；两个运行组件不反向导入实验层。原有根级文档 Agent 与它的实验模块已移入 `legacy/document_v1/`，模型配置/客户端及 sandbox/collector 的旧空壳导出已移除。扩展请直接导入实现所属的包。

采用已有业务规则的新大任务可新增 `task.json` 与材料并复用已登记后端；新增评分算法则需要 Python 实现和白名单登记。JSON 中的描述与后端实际验收契约应保持一致，修改描述本身不会改变评分算法。

## 证据版本与历史运行

当前可供本地审计的产物为 **108 次正式编码实验**（`coding_runs/validation_main` 72次、`coding_runs/validation_defenses` 36次）及 **2 次最新回归**（`verification_runs/bench_cleanup`）。旧文档 `runs/`、20次编码 pilot 和更早的 MicroCoder/TaskForge 回归产物已清理。下面的历史布局兼容说明描述代码能力，不表示所有历史目录仍然存在。

新的源码快照使用 `source_layout_version=4`，分别位于 `source/compute_bench/`、`source/microcoder/`、`source/taskforge/`。布局4标记实验包精简后的源码清单；历史布局1、2、3仍可按保存时的规则报告与审计，不改写旧快照或成绩，也不执行历史快照源码。

旧布局中尚未完成的计划不能通过当前 `resume` 自动续跑：源码迁移后，字节哈希无法证明执行设计与原版本相同，需要另行明确迁移。全部计划已经完成时，`resume` 可以直接返回报告而不调用模型。恢复限制与只读历史审计是两件事。

旧文档问答代码位于 `legacy/document_v1/`，入口为：

```bash
python -m legacy.document_v1 --help
python -m legacy.document_v1 run --output runs/my_new_trial --cases 1 --repeats 1
python -m legacy.document_v1 report runs/my_new_trial
python -m legacy.document_v1 audit runs/my_new_trial
```

以上路径是新实验示例，不是已保留的数据；`run` 会调用真实模型。[历史说明](../legacy/document_v1/README.md) 保留源码使用方式，并标明旧产物已清理。当前编码实验结果见 [总览](../CODING_RESULTS.md)，机制与权限限制见 [设计说明](../docs/CODING_DESIGN.md)。
