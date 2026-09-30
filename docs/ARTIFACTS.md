# 历史清理与恢复

2026-09-25，项目收敛为编码主线；当前目录包含 30 个 closed 原子任务、20 个用户修复任务和全交叉实验。

已移除的内容包括：

- `legacy/document_v1` 文档问答实验及其入口和测试；
- 旧业务 workloads、43 项旧目录和专用运行器；
- rotation 配对和旧格式审计分支；
- 重复的 Python 评分实现和历史运行目录。

清理前备份位于：

```text
/home/ubuntu/create_bench/poc-cleanup-backup-c7xxi7XE/
```

`source-before-cleanup.tar.gz` 保存清理前源码；`coding_runs/` 和 `verification_runs/`
保存历史运行。Git 清理前提交为 `2e11e4f`。旧产物可能包含原机器绝对路径，建议在独立目录中
配合旧版源码读取，不要用当前 runner 直接恢复。

当前新运行使用源码布局 6：三个 Python 包分别快照，任务材料保存到 `task_materials/` 并记录哈希。
结果目录默认不进入 Git。当前测试数量和通过情况应以
`python -m unittest discover -s tests -q` 的即时输出为准。
