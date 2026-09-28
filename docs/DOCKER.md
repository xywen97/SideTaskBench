# Docker 运行

Docker Desktop 可让 macOS 用户在 Linux VM 中运行 SideTaskBench。当前沙箱需要嵌套创建
namespace、mount 和 chroot，因此 Compose 服务使用 `privileged`。只运行可信的本仓库镜像。

## 安装 Docker Desktop

使用 Homebrew 安装并启动：

```bash
brew install --cask docker
open -a Docker
```

首次启动需要在界面中接受条款并等待 Docker Engine 就绪。然后打开新终端验证：

```bash
docker version
docker compose version
```

也可以从 [Docker Desktop 官网](https://www.docker.com/products/docker-desktop/) 安装。
仅安装 Homebrew 的 `docker` CLI 不够，还需要 Docker Desktop 提供 Linux Engine。

## 初始化项目

```bash
cp .env.example .env
# 编辑 .env，填写模型 API 配置
mkdir -p metric_outputs
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

结果保存在 Docker 的 `sidetaskbench-coding-runs` named volume。不能把运行工作区直接映射到
macOS 目录：Docker Desktop 的文件共享层不支持内层沙箱再次 bind mount 后的完整 Git 写入语义。
容器中的外层 benchmark 可以访问模型 API；模型生成的命令仍在无公网访问的内层沙箱执行。

## 常用命令

```bash
docker compose run --rm sidetaskbench report coding_runs/smoke
docker compose run --rm sidetaskbench audit coding_runs/smoke --regrade
docker compose run --rm sidetaskbench resume coding_runs/smoke
```

查看和导出 named volume：

```bash
docker volume inspect sidetaskbench-coding-runs
mkdir -p docker_exports/coding_runs
docker run --rm \
  -v sidetaskbench-coding-runs:/source:ro \
  -v "$PWD/docker_exports/coding_runs:/target" \
  ubuntu:24.04 bash -c 'cp -a /source/. /target/'
```

导出的报告位于 `docker_exports/coding_runs/<运行名>/report.html`。删除 Compose 容器不会删除
named volume；确认不再需要任何实验后，才可执行
`docker volume rm sidetaskbench-coding-runs`。

镜像中的源码在构建时固定。拉取或修改源码后重新执行 `docker compose build`。
