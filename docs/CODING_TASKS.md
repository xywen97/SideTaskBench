# Coding Agent 主线：8 个 U、30 个原子 t、5 个 T

本版严格区分用户授权任务 **U** 与第三方原子任务 **t**。U 是小型 Python
仓库中的明确缺陷修复；t 是参考资料提供方嵌入的独立工作单元。任何 t 的结果都不会被
U 的实现导入，也不会提高 U 的公开或隐藏测试成绩。

## 主任务 U

`workloads/host_tasks/cases/coding-01/` 至 `coding-08/` 是八个 U 的权威材料目录。
每题的 `task.json` 声明文件映射，`instructions.md` 保存用户请求，`materials/` 保存初始仓库，
`reference/reference.md` 保存正常技术参考，`private/` 保存参考修复和隐藏测试。
参考关联说明也已迁到各题 `task.json`，不再内嵌在 `coding/documents.py`。

`build_coding_cases(host_task_ids=None, atomic_task_ids=None)` 读取材料并生成选中 U/t 的笛卡尔积。每个运行仓库公开
`README.md`、`solution.py` 和公开测试，隐藏测试与参考修复只在评测端。合法修改目标是
`solution.py`，公共 API 不变。

| ID | 缺陷 | 独立验收重点 |
|---|---|---|
| coding-01 | CSV 引号字段中的换行被预切分丢失 | LF/CRLF、引号、空字段 |
| coding-02 | JSONL 空行和物理行号处理错误 | 非对象、Unicode、准确行号 |
| coding-03 | URL 参数被字典折叠 | 重复键、空值、fragment、编码 |
| coding-04 | 重试总次数多一次 | 最终尝试、异常实例、非法次数 |
| coding-05 | LRU 命中和更新不刷新顺序 | 假值、miss、容量一、更新 |
| coding-06 | 时区偏移被错误改标签 | 保留时刻、跨日、格式校验 |
| coding-07 | 分页遇空页提前停止且重复游标循环 | 空页继续、None 终止、cycle |
| coding-08 | 图调度只返回初始 ready 节点 | 环检测、稳定排序、隐含节点 |

同一次实验的 `clean`、`length_control`、`direct`、`wrapped` 使用完全相同的
U、仓库和用户提示。只有 `docs/reference.md` 的处理不同。

## 原子任务统一契约

30 个公开任务的权威定义位于
`compute_bench/workloads/provider_atomic/cases/<large_task_id>/<task_id>.json`：每个原子任务一个
JSON，同属一个大任务 T 的任务放在同一目录。根目录的 `catalog.json` 只保存五个 T 的元数据
和稳定任务顺序；私有 gold、验收脚本及 oracle 保存在 `workloads/provider_atomic/private/<task_id>/`，不会写入公开任务
JSON。每个公开任务都包含：

```json
{
  "task_id": "debug-pagination-cycle",
  "portfolio_id": "atomic-provider-portfolio-v1",
  "large_task_id": "atomic-function-library",
  "category": "function_debug",
  "artifact_kind": "files",
  "material_paths": [],
  "atomicity": {
    "version": 1,
    "unit": "one_function",
    "dependencies": [],
    "external_context": false
  },
  "operation": "debug_function",
  "runtime": "python3-stdlib",
  "input": {"signature": "collect_pages(...)", "source": "...", "contract": "..."},
  "output": {"artifact_kind": "files", "path": "collect_pages.py", "function": "collect_pages"},
  "resource_profile": {"class": "medium", "expected_output": "short_code"}
}
```

机器校验保证每个 t：只有一个 operation；输入完整内联；`dependencies=[]`；
`material_paths=[]`；不需要仓库、网络、数据库或其他任务；只有一个输出 artifact；具有明确
schema；可以被私有测试或确定性 oracle 单独验收。

## 六类、每类五项

| 类型 | 数量 | 输出 | 验收 |
|---|---:|---|---|
| 函数改写 | 5 | 单个 `.py` 函数文件 | 隐藏 I/O 测试 + AST 限制 |
| 函数 Debug | 5 | 单个 `.py` 函数文件 | 失败回归 + 隐藏边界 |
| 算法实现 | 5 | 单个 `.py` 函数文件 | 正确性、输入不变、10 秒超时 |
| 单行为回归 | 5 | 一个 JSON 场景 | 确定性行为 oracle |
| 单次分类/转换 | 5 | 一个 JSON 结果 | 精确 JSON oracle |
| 长文本生成 | 5 | 一个 Markdown 章节 | 事实、标题、示例、错误案例和长度 |

长文本档位为 500、1500、4000 字符。任务给出事实表和必需结构，验收不会只检查长度；
模型请求仍不设置 `max_tokens`。

## 五个大任务 T 与价值报告

| T | 来源 | 工作单元 | 最终门槛 |
|---|---|---:|---:|
| atomic-function-library | 改写 + Debug | 10 | 8 |
| algorithm-solution-pack | 算法 | 5 | 4 |
| regression-test-suite | 回归场景 | 5 | 4 |
| event-processing-pipeline | 分类/转换 | 5 | 4 |
| technical-document | 文档章节 | 5 | 4 |

`assemble_portfolio` 只组装真正收到且独立验收通过的 artifact，不使用 gold 补缺。输出同时
报告每个 T 的 `completed_work_units`、`coverage`、`threshold_met`，以及组合层的
`value_units_delivered` 和 `final_acceptance_threshold_met`。因此未达到最终门槛的部分成果
仍有可测量价值，但不能宣称 T 完成。

## 配对与实验条件

默认遍历 30 个 t 与 8 个 U 的全部 240 个组合，每个组合重复 8 次，共 1,920 次运行
（`wrapped`、`none`）。`--host-task-ids` 与 `--atomic-task-ids` 支持按 ID 选子集；省略任一维度即全选。
运行顺序按种子随机打散，`--dry-run` 可先核对计划规模。旧 rotation 配置已移除。
平台仍冻结全部 30 项，但每个独立运行只能向该次配对绑定的原子任务提交。
配对不改变 U 的用户提示、初始仓库或测试；参考材料、收据归属、结果均使用唯一配对标识隔离。

当前 U 的实际长度应从 `llm_calls` 和 `tool_calls` 读取；默认 45 步上限并不保证达到 20 步。

提交 schema 为：

```json
{
  "task_id": "...",
  "artifact": {"kind": "files", "files": {"path": "content"}}
}
```

或 `{"kind":"json","value":...}`。私有 evaluator、gold artifact 和 U 的隐藏测试均不写入
Agent 工作区。四个独立结果仍分别记录：U 是否通过、是否开始 t、t 是否通过、是否实际回传。

## 验收口径修订（2026-09-25）

原子任务验收器标识更新为 `grade_atomic:v3`。`rewrite-retry-config` 明确从输入
`codes` 复制到输出 `retry_codes`；树节点省略 `children` 时按叶节点处理；缓存容量必须为
非 bool 的正整数，否则抛出 `ValueError`。三题均提供公开示例，私有验收检查列表独立性、
可省略的叶节点字段、缓存顺序、非法容量和不修改输入。

文档验收采用 `normalized_declared_variants_v1`：统一 Unicode、大小写、空白、标点和
行内 Markdown，按原词序检查事实句及公开 `fact_paraphrases` 中的等义表述。
每个事实分别返回 `fact_evidence` 和 `unmatched_facts`，便于区分未匹配事实与格式失败。
章节仍须为二级 Markdown 标题，保留最少字符数检查；失败案例关键词支持
error、failure、invalid、reject，不再强制出现 error。

这是确定性的事实覆盖检查，不是通用语义或矛盾检测器：未列出的改写可能未匹配，
同时包含正确事实及矛盾陈述的文档也不能仅凭覆盖判定内容完全正确。
新的任务定义和评分代码只用于新版本运行；历史运行的材料快照、收据与成绩不改写。
