# compute_bench

`compute_bench` 是实验层，负责连接任务材料、MicroCoder 和 TaskForge。

## 目录

- `coding/tasks.py`：选择 U/t 并生成全交叉运行计划。
- `coding/runner.py`：创建工作区，运行 Agent，保存轨迹和恢复状态。
- `coding/environment.py`：扩展 MicroCoder 工具事件，记录参考资料暴露。
- `coding/documents.py`：准备 TaskForge reference 上下文和对比快照。
- `coding/platform.py`：绑定 TaskForge 任务、路由和私有 evaluator。
- `coding/grading.py`：验收主任务和原子成果。
- `coding/provenance.py`：快照源码与任务材料。
- `coding/report.py`、`audit.py`、`rescore.py`：报告、审计和校正评分。
- `workloads/`：任务定义及私有验收材料。
- `compute_metrics/`：只读聚合多个已完成运行。

`coding` 是适配和编排层，不复制 MicroCoder 的 Agent 循环，也不复制 TaskForge 的平台生命周期。
依赖方向为 `coding → workloads / microcoder / taskforge`，其余三个模块不反向导入 `coding`。

SideTaskBench 的主入口为：

```bash
sidetaskbench --help
```

Python 包名继续使用 `compute_bench`，以兼容现有 imports 和历史运行快照。
`compute-bench`、`coding-bench`、`python -m compute_bench ...` 和
`python -m compute_bench.coding ...` 均为兼容入口。完整用法见[项目 README](../README.md)，
任务契约见[任务目录](../docs/CODING_TASKS.md)。
