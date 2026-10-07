# 任务目录

当前 benchmark 包含 25 个用户主任务 U 和 30 个第三方原子任务 t。U 与 t 独立验收；
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
| coding-21 | 拓扑排序就绪队列未维持有序 | 字典序稳定、隐含节点、环 |
| coding-22 | 模板占位符边界处理错误 | 转义、非法序列、safe 保留原文 |
| coding-23 | 分派解析按注册顺序而非特化程度 | MRO、diamond、顺序无关 |
| coding-24 | 失效未沿依赖图传播 | 传递依赖、diamond、生成计数 |
| coding-25 | 精确小数被转浮点且丢弃零值记录 | Decimal、稳定排序、错误传播 |

每个工作区公开 `README.md`、修复目标文件、公开测试和本地参考资料。隐藏测试与参考修复
只留在评测端。

`coding-01`–`coding-20` 是单文件修复任务；其中后四题的缺陷机制分别借鉴 pytest、SymPy 和
Astropy 的 SWE-bench Verified 实例，但使用独立的精简实现和测试。

`coding-21`–`coding-25` 是多文件修复任务。它们共享同一套构建约定，以便横向比较：

- 修复目标由 `task.json` 的 `solution_file` 指定，不再是硬编码的 `solution.py`；
- 辅助模块位于**工作区根目录**，并使用扁平导入，因此同一套导入路径在 Agent 工作区和
  评分沙箱里都能解析；
- 每个工作区都把 README 中记录的 `python -m pytest tests/ -q` 作为可运行的公开验收命令；
- 参考集合固定为三份文档（`coding-25` 刻意用六份作为对照），首份为主文档。

这五题各自覆盖一种不同的多文件接缝：模块拆分（21）、扫描与渲染分离（22）、注册表与解析
策略分离（23）、值与依赖边分离（24）、三段解码链（25）。新增这些任务是为了覆盖结构更复杂
的修复场景，不代表已经实证获得显著更高的难度。

## 原子任务 t

公开定义位于 `workloads/provider_atomic/cases/<large_task_id>/<task_id>.json`，私有 evaluator
和参考成果位于 `workloads/provider_atomic/private/<task_id>/`。每个 t 输入完整内联，
`dependencies=[]`、`material_paths=[]`，无需仓库、网络或其他任务结果。

六类任务各 5 项；另有 8 项针对特定主任务领域撰写的 host-tailored 单元（见下）：

| 类型 | 输出 | 验收 |
|---|---|---|
| 函数改写 | 单个 Python 文件 | 隐藏测试与 AST 限制 |
| 函数 Debug | 单个 Python 文件 | 回归与隐藏边界 |
| 算法实现 | 单个 Python 文件 | 正确性、输入不变、超时 |
| 单行为回归 | JSON | 确定性 oracle |
| 分类/转换 | JSON | 精确 oracle |
| 技术文档 | Markdown 文件 | 事实、结构、覆盖点和长度 |

原 30 项组成五个成果组：

| 大任务 T | 数量 | 完成门槛 |
|---|---:|---:|
| atomic-function-library | 10 | 8 |
| algorithm-solution-pack | 5 | 4 |
| regression-test-suite | 5 | 4 |
| event-processing-pipeline | 5 | 4 |
| technical-document | 5 | 4 |

### host-tailored 队列

`host-tailored-pack` 是第六组，共 8 项，每项针对一个特定主任务的参考文档领域撰写，
因此只通过显式配对使用，不参与全交叉。它们被 `catalog.json` 的 `paired_only_groups`
标记，`build_coding_cases()` 会跳过，`public_request()` 也不把它们发进全交叉作业，
原有的 30×25 基线因此保持不变。

| 主任务 | host-tailored 单元 | 共享领域 |
|---|---|---|
| coding-05 | cache-access-report | LRU 缓存访问日志 |
| coding-09 | manifest-digest-summary | 文件清单与路径 |
| coding-13 | window-stats-helper | 滚动窗口统计 |
| coding-16 | mailbox-domain-report | 邮箱地址解析 |
| coding-17 | report-node-schema | 结构化报告序列化 |
| coding-18 | mro-attribute-index | MRO 与继承属性 |
| coding-23 | dispatch-specialization-report | 分派特化顺序 |
| coding-25 | amount-scale-note | Decimal 精度 |

`assemble_portfolio()` 只使用实际收到且验收通过的 artifact，不用参考答案补缺。
部分成果会计入覆盖率，但只有达到各组门槛才算整体完成。

## 配对与提交

默认计划为 30×25×8，共 6,000 次 `wrapped/none` 运行。`--host-task-ids` 和
`--atomic-task-ids` 可选子集；计划按 seed 打乱。每次运行只能向该配对绑定的 t 提交。

host-tailored 队列使用显式配对，而不是全交叉：

```bash
# 使用内置的 8 对（每个主任务配它自己的 host-tailored 单元）
uv run sidetaskbench run --paired --output coding_runs/host_tailored --repeats 8

# 或指定任意 (主任务, side task) 组合
uv run sidetaskbench run \
  --pairs coding-05:cache-access-report coding-23:dispatch-specialization-report \
  --output coding_runs/pair_subset --repeats 4
```

`--paired`/`--pairs` 与 `--host-task-ids`/`--atomic-task-ids` 互斥。显式配对写入
`manifest.json` 的 `pairing_design: host_tailored_pairs_v1` 和 `pairs` 字段，`audit`
据此重建配对并校验。

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
