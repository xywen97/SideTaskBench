# TaskForge

TaskForge 是本地任务投放与成果收集平台。它冻结公开任务计划，把参考资料写入已登记的
工作区，通过 Unix socket 接收成果，调用可信 evaluator，并组装验收通过的结果。
它不会启动 Agent，也不依赖 MicroCoder 或 `compute_bench`。

## 模块

```text
models.py              计划和标识契约
planning.py            公开任务规划器
platform.py            创建、分配、会话、状态和组装
storage.py             JSON 持久化和进程锁
distribution/          reference 渲染与写入
collection.py          Unix HTTP 收集器和回执
artifacts.py           files / JSON artifact 校验
assembly.py            v1 Python 模块组装
artifact_assembly.py   v2 artifact 组装
cli.py                 create / status / assemble
```

## 任务计划

请求必须显式提供 `components`，或提供 `task_ids` 并给规划器传入 catalog。
默认规划器不从自然语言目标自动拆分任务。公开任务不能包含答案、源码或私有测试，
当前任务必须彼此独立。

```bash
python -m taskforge create \
  --request taskforge/examples/request.json \
  --output taskforge_runs/example
python -m taskforge status taskforge_runs/example
python -m taskforge assemble taskforge_runs/example
```

这些 CLI 命令不调用模型，也不启动投放会话。

## 生命周期

Python 调用顺序为：

1. `TaskForge.create()` 保存请求、计划和哈希。
2. `assign()` 把固定 reference 写入一个专用工作区。
3. `session()` 冻结 evaluator 标识和任务路由。
4. `open_delivery()` 创建工作区内的 `.collector.sock`。
5. Agent 通过 `POST /submit` 提交成果。
6. `close_delivery()` 关闭接收端；`status()` 和 `assemble()` 汇总结果。

工作区不能包含平台或 collector 目录。assignment ID 不能改绑任务、工作区或 reference；
已关闭的尝试必须使用新 ID。

## Artifact 协议

Schema v2 支持两种成果：

```json
{"task_id":"task-a","artifact":{"kind":"files","files":{"src/a.py":"..."}}}
```

```json
{"task_id":"task-b","artifact":{"kind":"json","value":{"ok":true}}}
```

请求上限为 2 MiB，artifact 上限为 1 MiB。文件路径必须是安全的相对 POSIX 路径，
文件内容必须是 UTF-8 文本；JSON 只接受有限数值和标准 JSON 类型。

Evaluator 由可信调用者提供，接口为 `grader(public_task, artifact) -> {"passed": bool, ...}`。
平台会先持久化收到的原始成果，再调用 evaluator。`accepted: true` 只表示请求被接收；
只有回执中的 `valid: true` 才表示成果通过验收且未被阻断。

## 持久化与恢复

平台保存 request、plan、assignment、delivery 配置和 JSONL 回执。并发修改由进程锁保护。
若进程在评分期间崩溃，`received.jsonl` 可能有原始成果而没有评分回执；这种记录不能算成功。
重新打开会话会把遗留的 active assignment 标为 interrupted，并只恢复有匹配登记的失效 socket。

平台目录是可信状态，不提供对拥有宿主写权限者的防篡改保证。Benchmark 的 evaluator 绑定见
`compute_bench/coding/platform.py`。
