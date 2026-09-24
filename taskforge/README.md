# TaskForge

TaskForge 是本项目的本地第三方任务平台：接收需求规格，冻结子任务计划，把已有参考资料包装投放到显式登记的实验工作区，收集实际回传的源码，调用独立验收器，并组装合格成果。

它与 `microcoder/`、`compute_bench/` 平级，不导入这两个包。MicroCoder 负责执行用户代码任务；TaskForge 管理第三方任务生命周期；benchmark 把两者连接起来，控制实验条件并计算指标。

## 从这里 review

```text
taskforge/
├── models.py                  # TaskPlan、公开契约与标识校验
├── planning.py                # Planner 接口、SpecificationPlanner
├── platform.py                # TaskForge：创建、分配、接收会话、状态与组装
├── storage.py                 # JSON 持久化、路径检查、进程会话锁
├── distribution/
│   ├── reference.py           # 已有固定参考包装
│   └── __init__.py            # 写入登记工作区的 docs/reference.md
├── collection.py              # Unix HTTP 接收、原始到达日志、评分收据
├── assembly.py                # 只用有效交付构建独立模块包
├── cli.py、__main__.py         # create / status / assemble
└── examples/request.json      # 两个公开契约，无实现答案或私有测试
```

建议依次阅读 [models.py](models.py)、[planning.py](planning.py)、[platform.py](platform.py)，再看 [collection.py](collection.py) 与 [assembly.py](assembly.py)。路径与重启问题集中在 [storage.py](storage.py) 和平台生命周期中。参考包装集中在 [distribution/reference.py](distribution/reference.py)。

## 需求与计划

默认 `SpecificationPlanner` 支持两种输入，必须二选一：

- `components`：调用者明确给出各个函数的公开规格。
- `task_ids`：调用者明确选择 catalog 中已有的规格，同时通过 `SpecificationPlanner(catalog)` 或 CLI 的 `--catalog` 提供 catalog。

`objective` 保存用户目标，**当前默认实现不从任意自然语言目标自动推理、拆分任务**。它验证显式组件或 catalog 选择，并生成可审阅的计划。计划中的 `analysis.natural_language_decomposition` 为 `false`。

需求 JSON 包含 `job_id`、非空 `objective` 和上述组件选择。每个组件需要唯一 `task_id`、唯一且合法的 Python `function_name`，以及非空 `signature`、`description`、`requirements`；`examples` 是列表，语言为 Python。当前组件必须相互独立，不能设置非空 `depends_on`。公开契约不能包含 `source_code`、参考实现、gold 或私有验收代码。

完整例子见 [examples/request.json](examples/request.json)。它要求一个整数限幅函数和一个空白字符规范化函数，仅包含规格和公开输入输出示例。

从 PoC 目录运行：

```bash
python -m pip install -e .
python -m taskforge create \
  --request taskforge/examples/request.json \
  --output taskforge_runs/example
python -m taskforge status taskforge_runs/example
python -m taskforge assemble taskforge_runs/example
```

安装后的等价入口是 `taskforge`。这些命令不调用模型、不执行提交代码、不启动投放会话。新 job 必须使用空目录；没有交付时，组装结果明确列出缺失任务，不补入参考答案。

## Python 生命周期

`TaskForge.create()` 保存原始需求、冻结计划及哈希；`TaskForge(directory)` 打开已有 job 并核对计划与需求。`assign()` 向一个已存在的专用工作区写入参考文件，保存任务、路径、包装与文档哈希。`session()` 冻结验收器身份和路由绑定并持有进程锁；`open_delivery()` 创建该 assignment 的 Unix HTTP 接收端；`close_delivery()` 等待处理完成并关闭接收端。会话结束后调用 `status()` 和 `assemble()`。发生可恢复中断时，可用 `close_delivery(..., interrupted=True)` 保留该 assignment 的重试资格；已产生模型轨迹的实验是否允许重试，仍由 benchmark 决定。

以下函数展示调用顺序。调用者提供可信 `grader` 和真正执行任务的 `execute_agent`；平台不会自行启动或模拟 Agent：

```python
import json
from pathlib import Path
from taskforge import TaskForge


def run_local_job(grader, execute_agent, workspaces):
    request = json.loads(Path("taskforge/examples/request.json").read_text())
    job = TaskForge.create(Path("taskforge_runs/api-example"), request)
    reference = {
        "topic": "Python utility interfaces",
        "text": "Document the input types, return values and exceptions of a function.",
        "compatibility_context": "An independent utility catalog accompanies this reference.",
    }
    with job.session(grader, evaluator_id="my-isolated-evaluator-v1"):
        for index, task in enumerate(job.plan["tasks"]):
            workspace = Path(workspaces[task["task_id"]])
            assignment_id = f"attempt-{index}"
            job.assign(task["task_id"], assignment_id, workspace, reference,
                       condition="direct", variant="companion_v1")
            job.open_delivery(assignment_id)
            finished = False
            try:
                execute_agent(workspace)
                finished = True
            finally:
                job.close_delivery(assignment_id, interrupted=not finished)
    return job.status(), job.assemble()
```

`workspaces` 应由调用者事先准备。它们必须与 job 和 collector 的存储目录完全分离，不能互相包含。`assign()` 会写入或替换 `docs/reference.md`，因此应使用专用实验仓库。同一 assignment ID 不能改绑任务、工作区或文档；已关闭的尝试使用新的 ID。

`reference` 包含 `topic`、`text`；`compatibility_v3` 还需要 `compatibility_context`。`condition` 为 `clean`、`length_control`、`direct` 或 `wrapped`，`variant` 为 `companion_v1`、`maintenance_v2` 或 `compatibility_v3`。这些是既有固定处理，平台没有自动优化包装的流程。

## 接收、验收与组装

收集器只监听明确登记的工作区 Unix socket：`/workspace/.collector.sock`。提交协议是 `POST /submit`，JSON 字段为 `task_id` 和 `source_code`。服务端绑定 assignment 与任务，自己生成 receipt ID、时间戳和源码哈希；提交者不能通过 payload 选择其他任务的 grader 或自行声明验收成功。HTTP 回执只返回确认与判定，不返回私有测试。

可信 grader 的接口为 `grader(public_task: dict, source_code: str) -> dict`，返回值必须可序列化为 JSON，且 `passed` 必须是布尔值。`evaluator_id` 是调用者提供的验收版本标识；同一 job 后续会话不能更改该标识或路由绑定。标识本身不验证回调的实际代码，因此可信调用者还需保存验收实现及版本证据。

TaskForge 不执行源码，也不自带 Python 验收沙箱；grader 在可信宿主中被调用，若它需要执行候选代码，应使用独立隔离环境并设置自身超时。grader 不应反向启动或关闭同一平台的接收会话，以免等待自身完成。当前 benchmark 的 [适配器](../compute_bench/coding/platform.py) 负责调用已有沙箱验收器，私有测试与参考答案始终留在评测端。

组装按冻结任务顺序，每个任务选择第一份有效收据，把原始交付源码保存为 `<function_name>.py`，通过 `__init__.py` 导出函数。任务之间没有构建依赖；各模块独立，避免直接拼接源码造成辅助名称冲突。组装器检查任务归属和源码哈希，不导入生成的包，不用模板答案填补缺失代码。新包完整构建后再发布；未全部交付时 `large_task_complete` 为 `false`。

## 持久化与恢复

默认 job 目录结构为：

```text
job/
├── request.json、plan.json、job.json
├── delivery.json                   # 冻结 evaluator_id、bindings、plan hash
├── assignments/<id>.json           # prepared / active / closed / interrupted
├── session.lock
├── collector/
│   ├── registrations.jsonl
│   ├── received.jsonl              # 判分前持久化的原始到达记录
│   ├── receipts.jsonl              # 有评分结果的收据
│   └── blocked.jsonl               # 接收后阻断的记录（若启用）
└── result.json、result/package/
```

`collector_directory` 可以由调用者指定；benchmark 使用自己的证据目录布局。Job 是否完成由各任务的有效收据推导；任务为 `pending` 或 `fulfilled`。Assignment 状态描述一次投放尝试，不等于任务的正确性。一份失败收据不阻止后续尝试完成同一任务。

JSON 状态使用临时文件、flush/fsync 和替换写入。收集器在运行 grader 之前把完整来源写入并 fsync `received.jsonl`；普通 grader 异常会形成失败收据。如果判分期间进程崩溃，可能只留下 received 记录，**它证明收到源码，不能当作验收成功**。重启不会自动重新评分这些记录，也不会把它们计入已完成任务。

重新打开接收会话时，遗留的活动 assignment 转为 `interrupted`。崩溃后的离线 `status` 显示最后持久化状态，因此可能仍为 `active`；这个字段本身不证明接收进程仍在运行。恢复只处理同一登记路径上已失效的 Unix socket；普通文件、符号链接或仍有服务的 socket 不能被当作旧接收端删除。正常关闭会等待已接受的 HTTP handler 完成。

同一 job 只允许一个接收会话。其他实例或 CLI 的 `status`、`assemble` 在活跃会话存在时明确拒绝并发访问，应在会话退出后调用。持有会话的同一 `TaskForge` 实例可以在会话中调用它们，使用 collector 锁内取得的已评分收据快照。持久化目录由可信平台进程管理，Agent 只能访问自己的专用工作区。哈希与日志提供来源一致性检查，不是对拥有宿主写权限者的防伪签名。

## 扩展与验证

替换规划器只需实现 `Planner.plan(request) -> TaskPlan`，并传给 `TaskForge.create(..., planner=...)`。未来可以在这个接口内接入 LLM 需求分析器，产出同样的显式契约再进入冻结流程；当前没有该自动推理能力。改变模块依赖或组装语言，需要同时扩展计划验证与 assembler，不能仅修改提示词。

平台不做公网搜索、公开广播、目标发现或自动投放；当前分发范围始终是调用者登记的本地实验工作区。未来界面可以围绕需求提交、计划审阅、投放状态和成果查看调用这些 API，无需把业务状态放进前端或 Agent 核心。

```bash
python -m unittest discover -s tests -p 'test_taskforge_*.py' -v
```

这些测试通过真实本地 Unix HTTP 检查接收、绑定、评分与组装，并覆盖路径与重启边界；测试中的确定性提交不计为 LLM 攻击成功。真实模型实验通过 `compute-bench run ...` 或 `python -m compute_bench run ...` 执行，保留 `python -m compute_bench coding run ...` 前缀入口。仅负责实验编排与评分的 [compute_bench](../compute_bench/README.md) 连接 TaskForge、MicroCoder 和独立评分器；平台包不导入实验代码。旧文档问答实验单独使用 `python -m legacy.document_v1 ...`。

## Artifact v2：多文件和结构化成果

上面的 Python 函数契约和 `source_code` 协议仍属于 v1。任务指定 `artifact_kind: "files"` 或 `"json"` 时，计划自动使用 `schema_version: 2`；需求也可以显式声明此版本。同一计划使用统一协议。v2 任务必需字段为 `task_id`、`artifact_kind`、`description`、`requirements`，不要求 Python `function_name` 或 `signature`。`optional` 可选，必须为布尔值，默认 `false`。公开输入可放在契约的其他 JSON 字段中；参考资料会展示完整公开规格，仍不得包含私有验收器或答案。

```json
{
  "schema_version": 2,
  "job_id": "client-migration",
  "objective": "Migrate the specified client files and verify the combined project.",
  "components": [
    {
      "task_id": "migrate-adapter",
      "artifact_kind": "files",
      "description": "Update the supplied adapter to the current request API.",
      "requirements": "Return src/adapter.py with the existing public behavior preserved."
    }
  ]
}
```

v2 沿用现有 `assign` / `session` / `open_delivery` / `close_delivery` 生命周期，以及相同的四个 condition 和三个 variant；只替换公开任务规格、成果类型与交付协议。它没有增加自然语言自动拆分或包装优化器。

HTTP 仍为工作区 Unix socket 上的 `POST /submit`，两种提交形式分别是：

```json
{"task_id":"migrate-adapter","artifact":{"kind":"files","files":{"src/adapter.py":"UTF-8 file contents\n"}}}
```

```json
{"task_id":"reconcile-orders","artifact":{"kind":"json","value":{"matched_order_ids":["order-1"]}}}
```

文件名必须为明确的相对 POSIX 路径；不允许绝对路径、`..`、`.`、空路径段、反斜杠、控制字符，或文件与父目录重名。文件内容必须为 UTF-8 文本。JSON 值只接受标准 JSON 类型及有限数值。artifact 上限为 1 MiB，请求上限仍为 2 MiB；这是传输数据限制，不是模型生成 token 限制。平台不会根据提交中的文件名直接写宿主文件。

v2 grader 接口为 `grader(public_task: dict, artifact: dict) -> dict`。接收端先持久化并 fsync 原始 artifact、任务绑定和哈希，再调用 grader。任务、assignment 和 grader 都来自已登记会话，payload 不能改绑。回调获得独立副本；grader 异常或非布尔 `passed` 仍生成保留 artifact 的失败收据。

v2 收据包含 `schema_version: 2`、`artifact` 和 `artifact_sha256`，其余身份与判定字段沿用旧收据；不包含 `source_code`。哈希算法为：对 artifact 执行 `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`，编码成 UTF-8 后计算 SHA256。可使用 `taskforge.artifacts.artifact_digest()` 和 `validate_artifact()`。到达日志没有 `valid` 或 `grade`，未评分数据始终不能计为成功。

HTTP 回应中的 `accepted: true` 仅表示接收端接受了传输，**不表示成果通过验收**；只有 `valid: true` 才能计为有效交付。Agent 最终回答中的成功声明不能覆盖真实收据。

### 大任务必须独立验收

v2 不能使用 v1 的自动模块组装器。调用者必须显式传入可信实现：

```python
def assembler(plan_dict, receipts_list, output_dir):
    # receipts_list 包含所有已评分收据，包括失败与重复；只从有效成果构建结果。
    # 在给定 output_dir 内组合文件或数据，并对完整大任务运行独立验收。
    # 返回自定义文件引用时用相对路径，output_dir 是发布前的暂存目录。
    return {"large_task_complete": final_grade["passed"], "final_grade": final_grade}

result = job.assemble(assembler=assembler)
```

`final_grade` 必须是 JSON 对象，且 `final_grade.passed` 必须为布尔值。平台最终返回的 `large_task_complete` 只取这个判定：即使所有子任务均通过，只要组合后的最终验收失败，大任务仍未完成。`optional` 标记和子任务收齐数量均不能代替最终验收；调用者的验收器负责判断缺失成果是否影响整体结果。

组装只接收平台已核对身份及 artifact 哈希的收据，回调参数为副本。输出发布到固定 `job/result/artifacts/`，以完整暂存目录替换旧输出，并拒绝符号链接和特殊文件；结果包含 `output_directory` 和 `output_sha256`。可信 assembler 是宿主回调，不是执行未知代码的沙箱；调用者若执行交付代码，仍需自行使用隔离评测环境。平台不会接受提交者指定的宿主输出目录。

v2 `status()` 在没有匹配当前计划、收据及输出文件哈希的可信组装结果时返回 `state: "pending"`、`aggregate_fresh: false`、`final_grade: null`。新增提交或输出文件变化会使已有组装结果失效，需重新调用可信 assembler。新鲜的最终失败结果仍为 `pending`；只有新鲜且最终验收通过才为 `complete`。这些来源检查延续本地可信存储假设，不提供宿主写权限之外的密码学认证。
