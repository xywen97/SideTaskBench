# 实验产物保留范围

2026-09-24 按精简要求清理早期产物，随后新增四个大任务的验证。目前保留以下运行目录：

| 目录 | 用途 | 运行数 |
|---|---|---:|
| [coding_runs/validation_main](../coding_runs/validation_main/) | 冻结后的正式主矩阵 | 72 |
| [coding_runs/validation_defenses](../coding_runs/validation_defenses/) | 正式防御对照 | 36 |
| [verification_runs/bench_cleanup](../verification_runs/bench_cleanup/README.md) | 当前三包结构与默认入口的最新真实回归 | 2 |
| [verification_runs/workloads](../verification_runs/workloads/README.md) | 四个大任务：12 次明确授权＋8 次参考注入对照 | 20 |
| [verification_runs/atomic](../verification_runs/atomic/README.md) | 四个原子版本：初版及修复后的验证分别保留，每轮 43 次授权＋8 次参考对照 | 102 |

`verification_runs/json_cases/` 保存 JSON 格式迁移的离线验证，不含新增模型运行。原子任务目录另有使用已收到回执生成的派生组装结果；这些不算新的 Agent 运行，也不覆盖原成绩。

正式结果总览只统计前两组的 **108 次运行**。结构回归与新增任务验证单独报告，不计入正式成绩。每个保留矩阵的全部成功、失败、拒绝及恢复记录均完整保留，未按结果筛选。

已删除：旧文档实验的 `runs/`，编码开发试跑 `coding_runs/pilot_v1`、`pilot_v2`、`pilot_v3`，旧重构验证 `verification_runs/microcoder_refactor`、`taskforge_refactor`，以及依赖旧文档产物的根目录 `RESULTS.md`、`RESULTS.html`、`RESULTS.json`。共删除 1,756 个文件，文件内容合计 15,828,511 bytes。

保留运行的所有原始轨迹、源码快照、工作区、收据、评分、校正记录和审计数据均完整保留。清理前后 **4,549 个文件**的清单与 SHA256 比对一致；顶层 `CODING_RESULTS.*` 根据保留的结果重新生成，不回写单次实验报告。以下 **5 项离线审计均通过**，当前15份文档/顶层HTML的本地链接检查也通过：

```bash
compute-bench audit coding_runs/validation_main
compute-bench audit coding_runs/validation_main --corrected
compute-bench audit coding_runs/validation_defenses
compute-bench audit coding_runs/validation_defenses --corrected
compute-bench audit verification_runs/bench_cleanup
```

保留的最新验证记录描述的是当时执行的检查，其中“19 项历史审计”“128 次正式/试验矩阵”等数字保留历史语境；本地当前可复验的范围以上表为准。旧源码仍位于 `legacy/document_v1/`，可用于重新生成实验，但已删除的旧产物不再随项目提供。

后续新实验写入 `coding_runs/<实验名>`；代码改动的回归写入 `verification_runs/<验证名>`。仅保留仍需复验的实验及最新回归即可。
