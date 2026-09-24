# JSON 案例迁移验证

四个 benchmark 大任务 T 已改为 `cases/<name>/task.json` 和独立公开材料。Python 后端保留生成、验收、参考成果和组装逻辑。本轮只迁移任务定义的存储方式，未新增 LLM 调用或注入实验。

## 验证结果

- 完整测试套件：**311 项全部通过**，见 [tests.log](tests.log)。
- 四个案例的确定性验收：**4/4 通过**，见 [check.json](check.json)。
- seed 0、7、41、2026：**16 组公开规格和参考成果与迁移前严格相同**。
- 历史实际提交：**45 条 HTTP 回执的评分、12 个组装成果及最终评分相同**，包括无效提交；仅排除运行耗时等 `execution` 诊断字段。见 [migration_validation.json](migration_validation.json)。
- 历史 workload 完整审计并重新评分：授权组 **40 条回执 + 4 个 T**，注入组 **5 条回执 + 8 个 T + 8 个 U**，全部一致。见 [authorized_audit.json](authorized_audit.json)、[injected_audit.json](injected_audit.json)。
- wheel 打包及安装后的 CLI：**35 项检查通过**，全部 18 份定义、schema、静态材料和迁移证书资源均完整；四案均从安装目录完成查看和 seed 7 导出。见 [packaging.json](packaging.json)。
- 原有四组结果目录共 **5,509 个文件**，文件清单和全部字节保持不变；已扫描本轮材料和输出，没有发现已知凭据值。详见 [summary.json](summary.json)。

重评分使用当前受信任代码。迁移证书锁定旧代码、当前代码、JSON/材料和公开规格的哈希；不导入历史运行目录中的 Python 快照。后续定义或后端变更不会自动获得本次迁移的兼容授权。

## 更早 coding 实验的补充检查

三项原始记录审计和两项校正记录的一致性审计均通过。另尝试的两项校正记录重执行，被原有 `current_grader_matches_correction` 校验拒绝，候选执行数为 0；相关失败报告保留在 `coding_*_corrected_audit.json`，一致性报告为 `coding_*_corrected_consistency_audit.json`。

这一差异早于本轮迁移：旧校正器使用 `from .sandbox import Sandbox`，当前使用 `from microcoder.sandbox import Sandbox`。迁移前的 workload 源码快照已经保存了当前版本。本轮没有修改 coding 验收器、放宽该校验或改写历史证据。这不影响上述四个 workload 的 JSON 迁移验证结果。
