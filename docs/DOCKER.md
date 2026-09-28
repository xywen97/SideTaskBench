# Docker 运行

Docker Desktop 可让 macOS 用户在 Linux VM 中运行 SideTaskBench。当前沙箱需要嵌套创建
namespace、mount 和 chroot，因此 Compose 服务使用 `privileged`。只运行可信的本仓库镜像。

## 初始化

```bash
cp .env.example .env
# 编辑 .env，填写模型 API 配置
mkdir -p coding_runs metric_outputs
docker compose build
docker compose run --rm sidetaskbench check
```

`check` 不调用模型。若这里报告 Landlock 或 namespace 不可用，请先升级 Docker Desktop。

## 运行

检查计划：

```bash
docker compose run --rm sidetaskbench run --dry-run
```

最小真实实验：

```bash
docker compose run --rm sidetaskbench run \
  --output coding_runs/smoke \
  --host-task-ids coding-01 \
  --atomic-task-ids rewrite-user-record \
  --repeats 1 --workers 1
```

结果保存在宿主机的 `coding_runs/`。容器中的外层 benchmark 可以访问模型 API；模型生成的
命令仍在无公网访问的内层沙箱执行。

## 常用命令

```bash
docker compose run --rm sidetaskbench report coding_runs/smoke
docker compose run --rm sidetaskbench audit coding_runs/smoke --regrade
docker compose run --rm sidetaskbench resume coding_runs/smoke
```

镜像中的源码在构建时固定。拉取或修改源码后重新执行 `docker compose build`。
