# Closed 原子任务

当前分为两套材料：[host_tasks](host_tasks/) 是主 Agent 的 25 个用户修复任务 U；
[provider_atomic](provider_atomic/) 是 93 个原子任务 t，分为六类：
函数改写、函数修复、算法实现、单行为回归场景、分类/转换、长文档生成。
其中 47 项参与全交叉配对；另有 46 项（25 个 host-tailored + 21 个 similarity-regression）
针对特定主任务撰写，只通过显式配对使用。

公开定义在 `provider_atomic/cases/<large_task_id>/<task_id>.json`。
每个 t 内联完整输入和输出契约；`dependencies=[]`、`material_paths=[]`，无需其他任务的结果。
根 `catalog.json` 记录稳定顺序和七个分组的元数据；`paired_only_task_ids` 按任务 ID
标记哪些单元只参与显式配对。`cases/` 下的子目录只用于整理和统计，不决定单元是否参与运行。

每个单元的形状必须与其评测器和 `category` 一致（`python_function`/`document` 收 `files`，
`exact_json` 收 `json`；分类与回归组用 `exact_json`，长文档组用 `document`，其余代码类用
`python_function`）。不一致时 `catalog.py` 会在加载时报错。

`provider_atomic/catalog.py` 负责加载校验和独立验收；私有参考成果和验收材料在
`provider_atomic/private/<task_id>/` 中，包括 `evaluation.json`、参考文件及必要的 `acceptance.py`。
Python 成果使用 [python_grading.py](python_grading.py) 在隔离沙箱中运行；
JSON 使用确定性 oracle，文档检查事实、标题、覆盖点与字符长度。
`sidetaskbench check` 会用每个单元自己的参考答案跑一遍评测器，任一失败即非零退出。

公开调用入口是 `public_atomic_tasks()`；私有评测入口为 `atomic_task_catalog()` 和 `grade_atomic()`。
`assemble_portfolio()` 仅汇总实际有效回执，记录各 T 的覆盖率和门槛，不用参考答案补缺。

旧的四个仓库案例及 43 个业务原子任务已从当前项目删除，可从清理前备份或 Git 版本恢复。
任务材料和运行器分离：本目录负责加载材料，实验统一由 coding 调用。

详细契约和分级实验说明见 [任务文档](../../docs/CODING_TASKS.md)。
