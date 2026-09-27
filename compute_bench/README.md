# compute_bench

实验层仅维护 closed 原子任务、用户修复任务及运行和评测适配。

- [workloads/provider_atomic/](workloads/provider_atomic/)：30 个 t 的定义、独立验收与五组成果汇总。
- [workloads/python_grading.py](workloads/python_grading.py)：共享 Python 范围检查和沙箱验收。
- [workloads/host_tasks/](workloads/host_tasks/)：16 个 U 的独立任务目录；每题包含公开材料、参考说明和私有验收。
- [coding/tasks.py](coding/tasks.py)：按 ID 选择 U 与原子任务并生成全交叉配对，不内嵌任务材料。
- [coding/runner.py](coding/runner.py)：模型运行、轨迹、结果与启动失败恢复。
- [rewriting/](rewriting/)：独立准备 prompt、调用改造模型并保存可替换参考材料；[prompt.md](rewriting/prompt.md) 可直接查看。
- [coding/environment.py](coding/environment.py)、[coding/platform.py](coding/platform.py)：连接 MicroCoder 和 TaskForge。
- [coding/report.py](coding/report.py)、[coding/audit.py](coding/audit.py)、[coding/rescore.py](coding/rescore.py)：报告、证据一致性检查和独立重评分。

依赖方向为 coding → workloads，实验层 → MicroCoder / TaskForge。
workloads 不反向导入 coding，两个执行组件不导入实验层。

`python -m compute_bench --help` 查看唯一实验主线的命令；`coding` 前缀和 `coding-bench` 保留为同一入口的别名。
旧 `workloads` 业务实验 CLI 和 `document-v1` 已移除。

新运行使用源码布局 6；运行代码按三个包保存，任务原始文件单独保存到运行目录的 `task_materials/` 并记录哈希。
布局 5 的 clean 基线仍可只读审计；恢复未完成的旧布局运行需要明确迁移。
完整任务契约见 [任务说明](../docs/CODING_TASKS.md)，环境和用法见 [项目 README](../README.md)。
