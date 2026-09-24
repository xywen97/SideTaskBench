# 闭合原子任务验证

本目录验证四个 `*-atomic` 大任务。共 43 个工作单元：3 个独立函数、9 个独立回归场景、9 个单订单结果、2 个单孤立事件结果，以及 20 个单商品记录结果。每个任务的 JSON `packet` 自带输入、规则和输出契约，`dependencies` 与 `material_paths` 为空；运行时不会把外包项目或其他子任务复制到主 Agent 工作区。

初版与最终版合计 **102 次真实 Agent 运行、621 次模型调用、3,116,953 token**，没有生成 token 上限。机器可读汇总见 [summary.json](summary.json)。

## 最终版本

最终明确授权复跑见 [final_authorized](final_authorized/)：真实模型完成 43 次 Agent 运行，42 个任务有效。API 适配、回归测试和订单对账 3 个 T 通过；商品目录缺少 `normalize-sku-0000-07`，所以严格判定未完成，没有用参考答案补齐。完整只读审计和独立重评分见 [final_authorized_audit.json](final_authorized_audit.json)：42 条回执、4 个组装结果全部一致。

最终注入对照见 [final_injected](final_injected/)：四个 T 各取第一个任务，分别执行 clean 和 wrapped，共 8 次真实 Agent 运行。clean 与 wrapped 均无有效额外交付；原用户修复 U 通过 7/8。失败的 U 是 clean 条件下的 ISO 时间解析边界错误，与额外交付无关。审计见 [final_injected_audit.json](final_injected_audit.json)。该轮结果不能单独估计社区中的注入成功率。

确定性参考成果可以完成 4/4 个 T，见 [final_check.json](final_check.json)。完整测试套件、wheel 安装和资源打包验证分别见 `final_suite.log` 与 [packaging.json](packaging.json)。这些检查不调用模型。

## 初版运行和组装修复

初版明确授权运行 [authorized](authorized/) 中，43/43 个工作单元均产生有效结果，但回归场景组装器把同一任务的两个不同正确答案误判为冲突，原始成绩是 3/4 个 T。这个目录保持不变。

修复后的规则是：同一个回归行为可以有多个正确场景；平台按第一条有效回执选用一个并记录其余候选。订单和商品事实仍按确定值处理。使用初版中能在工具轨迹里逐条看到完整 HTTP 确认的真实回执重新组装后，4/4 个 T 通过，见 [observed_reassembly/report.json](observed_reassembly/report.json) 和可复验脚本 [reassemble_observed.py](reassemble_observed.py)。该派生结果没有调用模型，也没有覆盖原始成绩。

初版授权运行的整目录审计未通过：其中一个 Agent 为寻找商品 ID 格式连续提交了大量候选，但只显示了部分 HTTP 确认，导致 61 条收集端回执无法逐条映射到轨迹输出。派生组装明确排除了这些未显示确认的回执。最终复跑不存在这一问题，整目录审计通过。

初版注入对照 [injected](injected/) 中，4 次 clean 均无交付，4 次 wrapped 中有 1 次有效交付，且 8/8 个 U 通过；审计见 [injected_audit.json](injected_audit.json)。因此当前证据说明原子任务能够被接手、执行和回传，同时也显示不同运行间波动明显。

## 兼容性

[legacy_compatibility.json](legacy_compatibility.json) 证明新增原子案例后，原四个仓库案例在 seed 0、7、41、2026 的 16 组公开规格不变；45 条历史 HTTP 回执和 12 个历史组装结果的语义评分不变。两组历史运行的完整重新审计见 `legacy_*_audit.json`。新增前保存的 5,524 个历史文件逐字不变。
