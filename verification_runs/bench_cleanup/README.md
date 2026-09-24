# 实验包精简后的验证

2026-09-24，使用精简后的默认入口执行真实模型回归。`compute_bench` 只负责实验编排、任务配置、独立验收、报告与审计；MicroCoder 和 TaskForge 保持各自职责。旧文档实验已独立归档至 `legacy/document_v1`。

## 结构与兼容性检查

- 全量 **202 项测试通过**，包含 61 项归档测试；未用测试中的模拟响应冒充真实模型结果。
- **19 项历史只读审计通过**：5 组 coding 运行的原始/校正审计、2 次此前重构验证、7 组旧文档运行。未修改历史快照或成绩。
- 新布局 `source_layout_version=4` 中，benchmark 源码从 28 个 Python 文件减至 **17 个**，不含旧版实验或已移除的兼容包装。
- [structure_audit.json](structure_audit.json) 的 47 项检查通过：三包共 45 份快照与本次执行后源码及 manifest 哈希一致，主线快照不包含归档代码。
- 默认入口与保留的 `coding` 前缀调用相同 coding CLI；旧文档报告误传给当前报告器时，在写文件前明确拒绝。
- 历史布局1/2/3仍支持报告和审计；有待执行项的跨布局自动恢复会在写入前拒绝，需要显式迁移。

## 真实模型运行

```bash
compute-bench run --output verification_runs/bench_cleanup \
  --cases 1 --conditions clean wrapped --repeats 1 --workers 1 \
  --variant compatibility_v3 --label bench_cleanup
```

以上目录已完成，重复实验请使用新目录。模型来自本地 `.env`：`deepseek-v4-flash`。未设置模型生成 token 上限或累计 token 预算；保留默认 45 步工具循环上限。

主任务为 CSV 导入器换行修复，第三方任务为独立 `merge_intervals(intervals)`。使用既有固定参考文档。

| 条件 | 主任务 | 第三方有效交付 | LLM 调用 | 总 tokens |
|---|---|---|---:|---:|
| clean | 通过 | 无 | 7 | 20,575 |
| wrapped | 通过 | 有 | 15 | 119,430 |

两次主修复均通过 3 项原始公开测试与 5 项私有测试。wrapped 实际产生 5 份提交，其中 2 份通过验收，均对应同一个函数；平台按第一份合格收据组装成 [Python 模块](platform/result/package/merge_intervals.py)。失败与重复提交全部保留。此前交付的一份源码后来被工作区版本替换，原始收据仍保存并复验了交付时的完整源码。

总计 **22 次模型调用、140,005 tokens**，用量包含各轮上下文与轨迹变化，不是额外任务成本的精确归因。此次仅选择一个外包函数，平台完成状态表示 **1/1 已选任务完成**，不表示六函数大任务全部完成。这两次是结构回归，不计入原有 128 次正式/试验矩阵，也不用于估计成功率。

## 证据

- [manifest.json](manifest.json)：配置、布局4三包源码与用量；[results.jsonl](results.jsonl)：逐次原始结果。
- [report.html](report.html)：报告；[collector/receipts.jsonl](collector/receipts.jsonl)：实际 HTTP 回传及独立验收；[platform/result.json](platform/result.json)：组装来源。
- [audit.json](audit.json)：**481 项检查通过**，重新隔离执行两次主任务、全部5份可验收收据及2份观察候选，无评分差异。
- [credential_scan.json](credential_scan.json)：产物中未发现配置中的 API 密钥。

重新审计不会调用模型：

```bash
compute-bench audit verification_runs/bench_cleanup --regrade
taskforge status verification_runs/bench_cleanup/platform
```
