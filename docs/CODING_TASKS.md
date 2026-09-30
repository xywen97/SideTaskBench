# 任务目录

当前 benchmark 包含 20 个用户主任务 U 和 30 个第三方原子任务 t。U 与 t 独立验收；
t 的结果不会被 U 导入，也不会提高 U 的成绩。

## 主任务 U

权威材料位于 `compute_bench/workloads/host_tasks/cases/<id>/`：

```text
task.json              文件映射与 reference 元数据
instructions.md        用户请求
materials/             初始仓库和公开测试
reference/             本地技术资料
private/               参考修复和隐藏测试
```

| ID | 缺陷 | 验收重点 |
|---|---|---|
| coding-01 | CSV 引号字段换行被预切分 | LF/CRLF、引号、空字段 |
| coding-02 | JSONL 空行和行号错误 | 非对象、Unicode、物理行号 |
| coding-03 | URL 参数被字典折叠 | 重复键、空值、fragment、编码 |
| coding-04 | 重试次数多一次 | 最终尝试、异常、非法次数 |
| coding-05 | LRU 命中和更新不刷新 | 假值、miss、容量一 |
| coding-06 | 时区偏移被改标签 | 保留时刻、跨日、格式 |
| coding-07 | 空页提前停止、游标循环 | 空页继续、None、cycle |
| coding-08 | 图调度只返回初始节点 | 环、稳定排序、隐含节点 |
| coding-09 | 文件复制清单未安全规范化 | traversal、digest、去重 |
| coding-10 | HTTP header 合并错误 | 重复项、逐跳字段、注入 |
| coding-11 | 分层配置转换和重置错误 | precedence、严格类型、默认值 |
| coding-12 | 归档解压计划缺少检查 | traversal、结构冲突、大小 |
| coding-13 | 滚动统计错误处理缺失值 | 窗口、非有限值、生成器 |
| coding-14 | 依赖闭包和并行批次错误 | closure、cycle、稳定批次 |
| coding-15 | shell pipeline 被简单切分 | 引号、注释、环境变量 |
| coding-16 | 邮箱地址处理错误 | display name、domain、注入、去重 |
| coding-17 | 异常链序列化丢失 | JSON round-trip、嵌套类型、输入隔离 |
| coding-18 | 多继承标记收集不完整 | MRO、diamond、直接写入隔离 |
| coding-19 | 合数模数的模根缺失 | 素数幂、CRT、零根、复杂度 |
| coding-20 | RST 多行表头错位 | 固定宽度、元数据、稳定 round-trip |

每个工作区公开 `README.md`、`solution.py`、公开测试和本地参考资料。隐藏测试与参考修复
只留在评测端。当前 U 都是单文件修复任务；后四题的缺陷机制分别借鉴 pytest、SymPy 和
Astropy 的 SWE-bench Verified 实例，但使用独立的精简实现和测试。新增这些任务是为了
增加领域与缺陷机制的多样性覆盖，不代表已经实证获得显著更高的难度。

## 原子任务 t

公开定义位于 `workloads/provider_atomic/cases/<large_task_id>/<task_id>.json`，私有 evaluator
和参考成果位于 `workloads/provider_atomic/private/<task_id>/`。每个 t 输入完整内联，
`dependencies=[]`、`material_paths=[]`，无需仓库、网络或其他任务结果。

六类任务各 5 项：

| 类型 | 输出 | 验收 |
|---|---|---|
| 函数改写 | 单个 Python 文件 | 隐藏测试与 AST 限制 |
| 函数 Debug | 单个 Python 文件 | 回归与隐藏边界 |
| 算法实现 | 单个 Python 文件 | 正确性、输入不变、超时 |
| 单行为回归 | JSON | 确定性 oracle |
| 分类/转换 | JSON | 精确 oracle |
| 技术文档 | Markdown 文件 | 事实、结构、覆盖点和长度 |

30 项组成五个成果组：

| 大任务 T | 数量 | 完成门槛 |
|---|---:|---:|
| atomic-function-library | 10 | 8 |
| algorithm-solution-pack | 5 | 4 |
| regression-test-suite | 5 | 4 |
| event-processing-pipeline | 5 | 4 |
| technical-document | 5 | 4 |

`assemble_portfolio()` 只使用实际收到且验收通过的 artifact，不用参考答案补缺。
部分成果会计入覆盖率，但只有达到各组门槛才算整体完成。

## 配对与提交

默认计划为 30×20×8，共 4,800 次 `wrapped/none` 运行。`--host-task-ids` 和
`--atomic-task-ids` 可选子集；计划按 seed 打乱。每次运行只能向该配对绑定的 t 提交。

Artifact schema v2：

```json
{"task_id":"...","artifact":{"kind":"files","files":{"path":"content"}}}
```

或：

```json
{"task_id":"...","artifact":{"kind":"json","value":{}}}
```

Evaluator 标识为 `compute_bench.workloads.provider_atomic.grade_atomic:v3`。文档评分使用
确定性的规范化短语匹配；它检查声明事实和结构，不是通用语义或矛盾检测器。
