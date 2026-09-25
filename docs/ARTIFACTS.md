# 精简记录与恢复

2026-09-25，项目收敛为 30 个 closed 原子任务、8 个用户修复任务及现有 rotation 实验。

从当前工作目录移除：

- 旧 `legacy/document_v1` 文档问答实验、入口、测试与汇总脚本。
- 旧业务 workloads 的四个仓库案例、43 个原子任务、独立运行器、验收后端、迁移文件和测试。
- 被新目录覆盖的六函数任务生成代码、旧格式审计兼容分支。
- 两套重复 Python 评分代码中的一套，现统一在 `workloads/python_grading.py`。
- 旧结果总览及过期审查文档；历史运行目录移到项目外。

本机恢复目录：

`/home/ubuntu/create_bench/poc-cleanup-backup-c7xxi7XE/`

其中 `source-before-cleanup.tar.gz` 保存清理前的代码、文档、测试和旧结果总览；
`coding_runs/`、`verification_runs/` 保存完整历史运行目录。
备份不包含本机模型密钥。Git 清理前提交为 `2e11e4f`，也可从版本历史查看已跟踪文件。

恢复时建议解压到新目录，使用清理前版本处理历史记录。
旧记录中可能含原工作区的绝对路径，移动后不能直接假定原命令仍可复验。
当前版本不再提供旧文档实验或旧业务 workloads 命令。

新实验写入独立输出目录；`coding_runs/`、`rewrite_runs/`、`verification_runs/`、
`microcoder_runs/` 和 `taskforge_runs/` 均不进入 Git，运行结果、轨迹和报告只保存在本地。
自定义输出路径应放在这些目录下，或先将对应输出目录加入 `.gitignore`。
本次精简没有发起真实模型实验。

验证：保留的 130 项测试全部通过，沙箱检查和独立目录安装包加载通过。
精简前后全部 30 个 t、15 组 rotation 的 U/t 数据哈希一致；备份中 3315 个已跟踪
运行文件的 Git blob 哈希与清理前一致。源码与测试 Python 文件从 126 个降至 68 个。
