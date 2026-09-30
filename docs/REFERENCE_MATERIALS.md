# 参考材料

20 个主任务都使用启动前固定的本地技术文档，不在运行时联网。

- `coding-01`–`coding-08`：每题 3 份文档。
- `coding-09`–`coding-16`：每题 6 份文档。
- `coding-17`–`coding-20`：每题 6 份固定版本的 CPython 官方文档。
- 第一份文档写入 `docs/reference.md`，其余写入 `docs/references/`。
- `docs/reference-index.md` 记录标题、来源、版本和许可证。

前 16 题材料于 2026-09-25 从固定上游 commit 导入。Python 文档对应 3.11.14；分页题还使用固定版本的
Google AIP 和 Boto3 文档。正文保留上游原始字节。每题 `task.json` 是来源元数据的权威记录，
包含 URL、commit、SHA-256、大小、行数、词数和许可证路径。

`search_reference` 按查询词最多返回 3 份文档，优先返回本次运行尚未召回的相关项。
工具返回路径不等于模型已经读取正文；事件中的 `reference_paths` 记录实际访问的辅助文档。

实验条件只处理主文档 `docs/reference.md`：

- `clean` 保留原文；
- `length_control` 添加与任务载荷等字符数的中性填充；
- `direct` 或 `wrapped` 加入原子任务契约与本地提交协议。

后四题与旧任务使用相同的官方资料集合机制；辅助文档在所有条件下不变。
`exposed` 只表示处理过的主文档进入工具输出，不表示模型理解或执行。

重新导入固定材料可运行：

```bash
python scripts/import_reference_materials.py
```

修改任何材料后应使用新的运行目录；已有运行依赖自己的冻结快照和材料哈希。
