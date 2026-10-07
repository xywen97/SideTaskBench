# Closed 原子任务

当前分为两套材料：[host_tasks](host_tasks/) 是主 Agent 的 25 个用户修复任务 U；
[provider_atomic](provider_atomic/) 是 38 个原子任务 t，分为六类：
函数改写、函数修复、算法实现、单行为回归场景、分类/转换、长文档生成。
其中原 30 项（六类各五项）用于全交叉配对；另有 `host-tailored-pack` 一组 8 项，
针对特定主任务的参考文档领域撰写，只通过显式配对使用。

公开定义在 `provider_atomic/cases/<large_task_id>/<task_id>.json`。
每个 t 内联完整输入和输出契约；`dependencies=[]`、`material_paths=[]`，无需其他任务的结果。
根 `catalog.json` 记录稳定顺序和六个 T 的元数据；`paired_only_groups` 标记不参与全交叉的组。
原 30 项的数量和六类分布是 v1 契约，新增单元不改变它。

`provider_atomic/catalog.py` 负责加载校验和独立验收；私有参考成果和验收材料在
`provider_atomic/private/<task_id>/` 中，包括 `evaluation.json`、参考文件及必要的 `acceptance.py`。
Python 成果使用 [python_grading.py](python_grading.py) 在隔离沙箱中运行；
JSON 使用确定性 oracle，文档检查事实、标题、覆盖点与字符长度。

公开调用入口是 `public_atomic_tasks()`；私有评测入口为 `atomic_task_catalog()` 和 `grade_atomic()`。
`assemble_portfolio()` 仅汇总实际有效回执，记录五个 T 的覆盖率和门槛，不用参考答案补缺。

旧的四个仓库案例及 43 个业务原子任务已从当前项目删除，可从清理前备份或 Git 版本恢复。
任务材料和运行器分离：本目录负责加载材料，实验统一由 coding 调用。

详细的 30 项契约和六组成果说明见 [任务文档](../../docs/CODING_TASKS.md)。
