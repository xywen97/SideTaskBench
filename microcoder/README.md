# MicroCoder

MicroCoder 是本项目的轻量 Coding Agent。它通过模型 API 决定下一步动作，在专用仓库里读取文件、修改代码、执行测试，再根据工具结果继续工作。

Agent 的实现全部位于这个目录，Python 包名和命令名都是 `microcoder`。它不依赖 `compute_bench`，可单独运行；benchmark 通过适配器给它分配任务并记录实验指标。

## 从这里 review

```text
microcoder/
├── core/
│   ├── agent.py         # CodingAgent、模型/工具接口、执行循环
│   └── trace.py         # JSONL 轨迹，排除私有推理文本
├── tools/
│   ├── registry.py      # 工具 schema、注册、分发与事件记录
│   ├── files.py         # 文件读写与路径边界
│   ├── shell.py         # shell 工具，调用 Sandbox.run
│   └── reference.py     # 本地参考文件入口
├── sandbox/
│   └── linux.py         # namespace、chroot、降权、Landlock、seccomp
├── prompts/
│   └── coding.py        # 默认编码提示词与可选授权边界提示词
├── config.py            # 模型连接配置，凭据不进入公开元数据
├── llm.py               # Chat Completions HTTP 适配器
├── cli.py               # 独立 run / check 命令
└── __main__.py          # python -m microcoder
```

建议依次读 [core/agent.py](core/agent.py)、[tools/registry.py](tools/registry.py)、[sandbox/linux.py](sandbox/linux.py)，最后看 [benchmark 适配器](../compute_bench/coding/environment.py) 和 [实验 runner](../compute_bench/coding/runner.py)。各目录的 `__init__.py` 只定义公开导出。

## 执行路径

```text
用户任务 + prompts
        ↓
CodingAgent.run → llm.complete(messages, tools)
        ↑                   ↓ 工具调用
        └── 工具结果 ← CodingTools.execute
                           ├── files：受路径检查约束的文件操作
                           ├── reference：本地参考位置
                           └── shell → Sandbox.run → Bash
```

`core` 只需要两个小接口：模型的 `complete(messages, tools)`，以及工具环境的 `tools`、`events`、`execute(name, args)`。接口使用 `typing.Protocol` 表达，不要求继承特定基类。

`CodingAgent` 管理一次任务的消息历史。模型回复包含工具调用时，按顺序执行并回传结果；没有工具调用时结束。调用者负责模型连接与工具的创建、关闭。复用工具环境时，每次结果只统计本次任务的工具调用。

默认最多 45 轮模型调用；不设置生成 token 上限或累计 token 预算。API usage、response ID、公开回答、工具参数与结果会写入轨迹。私有推理内容仅按模型协议在内存会话中回放。

## 独立运行

从 PoC 目录安装并检查执行环境：

```bash
python -m pip install -e .
python -m microcoder check
```

向已经准备好的专用仓库分配一个任务：

```bash
microcoder run \
  --workspace /tmp/my-python-repo \
  --task '修复 README 描述的问题，运行测试并检查最终 diff。' \
  --env .env \
  --trace microcoder_runs/example/trace.jsonl
```

`--workspace` 必须显式给出，代码修改会直接保留在该目录。模型配置 `.env` 与输出轨迹放在工作区之外；沙箱拒绝包含 `.env` 或 `.env.*` 的工作区，CLI 拒绝向已有轨迹追加内容。仓库可提供 `docs/reference.md`；没有该文件时，本地参考检索返回空结果。

可选参数 `--boundary` 加入第三方资料授权边界提示词，`--block-egress` 同时阻断 Unix socket。两者分别控制模型指令和执行权限。独立命令不会自动创建第三方收集器、注入实验文档或运行 benchmark 隐藏验收。

Python 调用入口：

```python
from pathlib import Path
from microcoder import CodingAgent
from microcoder.config import Settings
from microcoder.llm import ChatClient
from microcoder.tools import CodingTools

client = ChatClient(Settings.load(Path(".env")))
tools = CodingTools(Path("/tmp/my-python-repo"))
try:
    result = CodingAgent(client, tools).run(
        "修复 README 描述的问题并运行测试。",
        Path("microcoder_runs/example/trace.jsonl"),
    )
finally:
    client.close()
    tools.close()
```

Python 调用者应为每个会话提供新的、工作区外的轨迹路径；CLI 会强制检查这两点。

## 扩展位置

| 想改什么 | 修改或替换哪里 |
|---|---|
| 默认编码行为 | `prompts/coding.py`，或传入 `CodingAgent(system_prompt=...)` |
| 接入另一个模型 | 实现 `ModelClient.complete`；现有 HTTP 适配器在 `llm.py` |
| 新增工具 | 调用 `CodingTools.register_tool(schema, handler)`；无需修改执行循环 |
| 修改文件操作规则 | `tools/files.py` |
| 修改命令超时 | `tools/shell.py` |
| 修改执行隔离 | `sandbox/linux.py`；同时运行真实边界测试 |
| 新增 benchmark 任务、注入条件、指标 | `compute_bench/coding/` |

一个最小工具扩展示例：

```python
tools.register_tool(
    {
        "type": "function",
        "function": {
            "name": "project_name",
            "description": "Return the repository name.",
            "parameters": {
                "type": "object", "properties": {},
                "required": [], "additionalProperties": False,
            },
        },
    },
    lambda args: {"name": tools.workspace.name},
)
```

注册的 handler 是可信宿主代码；只有 `shell` 默认通过 Linux 沙箱执行。扩展工具时应明确它的文件、网络和进程边界。

## 执行权限

每条 shell 命令创建独立的 mount/network/PID/IPC namespace，构造最小 chroot，降为普通用户，再应用 Landlock 与 seccomp。工作区可读写，系统运行环境只读；模型凭据、宿主目录和其他实验不可见。启动阶段需要 Linux、Landlock ABI≥3、libseccomp 和可用的 `sudo -n`；设施不可用时停止执行。

文件在命令之间保留，shell 的 `cd`、环境变量和后台进程不作为持久会话保留。默认 shell 超时 60 秒，每个 stdout/stderr 最多返回 128 KiB。没有公开互联网访问，默认仅允许隔离范围内的 Unix socket；`--block-egress` 连同本地 socket 一并阻断。

## 与 benchmark 的边界

MicroCoder 不持有 `case`、`condition`、正确答案、第三方任务、交付收据或评分规则。`compute_bench/coding/environment.py` 创建任务仓库，并在通用工具事件上附加参考资料接触指标；runner 组合 `CodingAgent`、该适配器、收集器与验收器。

调用方直接导入 MicroCoder。当前实验使用布局6快照，分别保存 `compute_bench`、`microcoder`、`taskforge` 三个包及独立的任务材料。

验证入口：

```bash
python -m unittest discover -s tests -q
python -m compute_bench check
```

历史实验已移出当前项目，恢复位置见 [精简记录](../docs/ARTIFACTS.md)。当前运行使用独立输出目录。
