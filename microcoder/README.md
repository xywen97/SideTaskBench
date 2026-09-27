# MicroCoder

MicroCoder 是一个轻量 Coding Agent。它负责模型循环、工具调用、轨迹和 Linux 沙箱，
不包含 benchmark 的任务、实验条件、评分或回执逻辑。

## 模块

```text
core/agent.py       模型—工具循环和运行结果
core/trace.py       JSONL 公开轨迹
config.py           模型配置
llm.py              Chat Completions 客户端
prompts/coding.py   默认提示词和授权边界提示
tools/              文件、shell、参考检索和工具注册
sandbox/linux.py    namespace、chroot、Landlock、seccomp
cli.py              独立 run / check 命令
```

核心只依赖两个接口：模型客户端的 `complete()`，以及工具环境的 `tools`、`events` 和
`execute()`。因此 benchmark 可扩展工具事件，而不用修改 Agent 循环。

## 独立使用

检查沙箱：

```bash
python -m microcoder check
```

在专用仓库中运行任务：

```bash
microcoder run \
  --workspace /tmp/example-repo \
  --task '修复 README 描述的问题并运行测试' \
  --env .env
```

工作区必须已存在。模型配置和轨迹必须位于工作区之外，已有轨迹不会被覆盖。
`--boundary` 增加第三方资料授权边界提示；`--block-egress` 阻断工作区 Unix socket。

Python 调用：

```python
from pathlib import Path
from microcoder import CodingAgent
from microcoder.config import Settings
from microcoder.llm import ChatClient
from microcoder.tools import CodingTools

client = ChatClient(Settings.load(Path(".env")))
tools = CodingTools(Path("/tmp/example-repo"))
try:
    result = CodingAgent(client, tools).run(
        "修复问题并运行测试", Path("microcoder_runs/example/trace.jsonl")
    )
finally:
    client.close()
    tools.close()
```

## 执行边界

每条 shell 命令在独立 namespace 和最小 chroot 中执行；工作区可写，运行环境只读，
模型密钥不会传入命令。沙箱不可用时运行失败，不会退化为宿主 shell。

文件工具限制路径留在工作区。默认允许隔离环境中的 Unix socket，以便 benchmark
连接本地收集器；`--block-egress` 会关闭该能力。默认最多 70 次模型调用，不设置生成
token 上限。

Benchmark 适配位于 `compute_bench/coding/environment.py` 和 `runner.py`。
