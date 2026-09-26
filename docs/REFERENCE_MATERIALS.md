# 当前主任务的公开参考材料

2026-09-25 从上游固定 commit 下载。基础任务 `coding-01`–`coding-08` 每题3份；扩展任务
`coding-09`–`coding-16` 每题6份，共72份文档配置。重复使用的上游章节按任务各存一份，
便于离线安装及材料快照。正文按上游原始字节保存，没有摘要、扩写或截取。Python文档使用
3.11.14对应章节，格式多为reStructuredText；文件工具按文本读取，不需要安装文档构建器。

## 文档目录

字数为按空白切分的词数，不是模型token数。第一份为主文档，其余为辅助文档。下表保留基础层目录；扩展层的完整来源、哈希和检索词记录在各题 `task.json`。

| 任务 | 文档 | 行数 | 词数 | 本地正文 |
|---|---|---:|---:|---|
| coding-01 | [Python csv — CSV File Reading and Writing](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/csv.rst) | 594 | 2788 | [原文](../compute_bench/workloads/host_tasks/cases/coding-01/reference/reference.md) |
| coding-01 | [Python io — Core tools for working with streams](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/io.rst) | 1188 | 5989 | [原文](../compute_bench/workloads/host_tasks/cases/coding-01/reference/02-io.rst) |
| coding-01 | [Python tutorial — Input and Output](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/tutorial/inputoutput.rst) | 529 | 2995 | [原文](../compute_bench/workloads/host_tasks/cases/coding-01/reference/03-inputoutput.rst) |
| coding-02 | [Python json — JSON encoder and decoder](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/json.rst) | 766 | 3559 | [原文](../compute_bench/workloads/host_tasks/cases/coding-02/reference/reference.md) |
| coding-02 | [Python tutorial — Input and Output](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/tutorial/inputoutput.rst) | 529 | 2995 | [原文](../compute_bench/workloads/host_tasks/cases/coding-02/reference/02-inputoutput.rst) |
| coding-02 | [Python tutorial — Errors and Exceptions](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/tutorial/errors.rst) | 653 | 3143 | [原文](../compute_bench/workloads/host_tasks/cases/coding-02/reference/03-errors.rst) |
| coding-03 | [Python urllib.parse — Parse URLs into components](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/urllib.parse.rst) | 766 | 4005 | [原文](../compute_bench/workloads/host_tasks/cases/coding-03/reference/reference.md) |
| coding-03 | [Python urllib.request — Extensible library for opening URLs](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/urllib.request.rst) | 1642 | 7709 | [原文](../compute_bench/workloads/host_tasks/cases/coding-03/reference/02-urllib.request.rst) |
| coding-03 | [Python HOWTO — Fetch Internet Resources Using urllib](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/howto/urllib2.rst) | 598 | 3240 | [原文](../compute_bench/workloads/host_tasks/cases/coding-03/reference/03-urllib2.rst) |
| coding-04 | [Python tutorial — Errors and Exceptions](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/tutorial/errors.rst) | 653 | 3143 | [原文](../compute_bench/workloads/host_tasks/cases/coding-04/reference/reference.md) |
| coding-04 | [Python tutorial — More Control Flow Tools](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/tutorial/controlflow.rst) | 1126 | 5705 | [原文](../compute_bench/workloads/host_tasks/cases/coding-04/reference/02-controlflow.rst) |
| coding-04 | [Python — Built-in Exceptions](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/exceptions.rst) | 1036 | 4790 | [原文](../compute_bench/workloads/host_tasks/cases/coding-04/reference/03-exceptions.rst) |
| coding-05 | [Python collections — Container datatypes](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/collections.rst) | 1391 | 6648 | [原文](../compute_bench/workloads/host_tasks/cases/coding-05/reference/reference.md) |
| coding-05 | [Python functools — Higher-order functions and operations on callable objects](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/functools.rst) | 728 | 3342 | [原文](../compute_bench/workloads/host_tasks/cases/coding-05/reference/02-functools.rst) |
| coding-05 | [Python tutorial — Data Structures](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/tutorial/datastructures.rst) | 734 | 3830 | [原文](../compute_bench/workloads/host_tasks/cases/coding-05/reference/03-datastructures.rst) |
| coding-06 | [Python datetime — Basic date and time types](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/datetime.rst) | 2625 | 12713 | [原文](../compute_bench/workloads/host_tasks/cases/coding-06/reference/reference.md) |
| coding-06 | [Python zoneinfo — IANA time zone support](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/zoneinfo.rst) | 417 | 2092 | [原文](../compute_bench/workloads/host_tasks/cases/coding-06/reference/02-zoneinfo.rst) |
| coding-06 | [Python time — Time access and conversions](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/time.rst) | 975 | 4786 | [原文](../compute_bench/workloads/host_tasks/cases/coding-06/reference/03-time.rst) |
| coding-07 | [Google AIP-158 — Pagination](https://github.com/aip-dev/google.aip.dev/blob/23e176e7333ea3bc6b085f9950a5da03d2bbfc72/aip/general/0158.md) | 205 | 1435 | [原文](../compute_bench/workloads/host_tasks/cases/coding-07/reference/reference.md) |
| coding-07 | [Boto3 guide — Paginators](https://github.com/boto/boto3/blob/e2fb47b057930792b8bfe192063207b8c4794395/docs/source/guide/paginators.rst) | 118 | 546 | [原文](../compute_bench/workloads/host_tasks/cases/coding-07/reference/02-paginators.rst) |
| coding-07 | [Python tutorial — Data Structures: queues, sets and dictionaries](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/tutorial/datastructures.rst) | 734 | 3830 | [原文](../compute_bench/workloads/host_tasks/cases/coding-07/reference/03-datastructures.rst) |
| coding-08 | [Python graphlib — Functionality to operate with graph-like structures](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/graphlib.rst) | 210 | 1125 | [原文](../compute_bench/workloads/host_tasks/cases/coding-08/reference/reference.md) |
| coding-08 | [Python heapq — Heap queue algorithm](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/heapq.rst) | 322 | 2116 | [原文](../compute_bench/workloads/host_tasks/cases/coding-08/reference/02-heapq.rst) |
| coding-08 | [Python bisect — Array bisection algorithm](https://github.com/python/cpython/blob/cd1c3a6342869b7346c1b5c27b8de9c6ef9c4e69/Doc/library/bisect.rst) | 250 | 1299 | [原文](../compute_bench/workloads/host_tasks/cases/coding-08/reference/03-bisect.rst) |

## 选择依据

- CSV：CSV 解析、换行与文本流、文件输入输出。
- JSONL：JSON 解码与错误、逐行读取、异常处理。这里没有把普通 JSON 文档称为 JSONL 规范。
- URL 参数：URL 分解/编码、请求库、urllib 使用教程；重点为查询参数、重复键和空值。
- 重试：捕获/重抛异常、range 与循环边界、异常类型层次。
- LRU：OrderedDict 的重排与淘汰、lru_cache 的语义、字典及数据结构。
- 时间戳：datetime 的解析及时区转换、zoneinfo、time 的 UTC/本地时间概念。任务要求仍以 instructions.md 为准，不能因为 datetime.fromisoformat 接受更多形式而放宽验收。
- 分页：AIP-158 的页令牌与终止语义、Boto3 的迭代式分页、集合去重与字典访问。不同 API 的字段名和重试语义是背景知识，不覆盖题目指定的 items/next_cursor 接口。
- 调度：graphlib 的拓扑排序和环检测、heapq 的优先队列、bisect 的有序插入。稳定顺序仍由任务契约定义。

## 工作区与改写

前八题工作区包含主文档、两份辅助文档和来源索引，后八题包含主文档和五份辅助文档。
所有16题的README使用同一索引说明，`search_reference` 使用同一检索策略：根据查询词最多返回
3份资料，并在相关结果中优先返回本次运行尚未召回的文档。后八题两次查询可覆盖固定的6份资料；
所有内容均为启动前固定的本地文件，不会运行时联网。
现有 wrapped/direct/length_control 处理仅应用于主文档；两份辅助文档在所有条件下保持相同。改写模型只接收主文档正文，当前尚未实现一次模型调用改写多份文档。读取辅助文档在工具事件的 reference_paths 中单独记录，原 exposed 指标仍指向处理过的主文档；工具访问不等于模型理解或执行。
**使用新材料必须重新 prepare/generate 到新 rewrite_runs 目录，并使用新的 coding_runs 目录。** 旧材料包和运行快照未改动；当前源码会拒绝把旧材料或旧实验与新任务材料混合续跑。当前材料一致性审计/重评分不能直接替代旧版本环境中的历史复验。

## 来源与复现

每个 task.json 的 reference.documents 记录上游 URL、commit、版本、下载时间、原始 SHA-256、字节数、行数、词数与许可证路径；各 reference/ 目录保留上游许可文件。Python 文档额外保存 Doc/license.rst 中的授权说明；AIP 正文为 CC-BY-4.0，代码示例为 Apache-2.0；Boto3 为 Apache-2.0。
需要重新下载固定版本时，在项目根目录执行 `python scripts/import_reference_materials.py`。正常 prepare、实验和安装包加载均使用本地文件，不访问网络。材料属于版本化输入，进入 Git；生成的实验结果仍由 .gitignore 排除。
本文只描述材料扩展，不声称任务本身变复杂，也不保证交付率提高；应通过干净基线和不同材料条件比较来测量。
