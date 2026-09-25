# 主 Agent 的任务材料

每个用户任务 U 独立放置在 `cases/<case_id>/`：

```text
task.json                  # 标识、标题、文件映射、参考元数据
instructions.md            # 原始用户请求
materials/
  README.md                # 初始仓库说明
  solution.py              # 有缺陷的初始实现
  tests/test_solution.py   # 原始公开测试
reference/reference.md     # 正常技术参考正文
private/
  solution.py              # 参考修复
  test_hidden.py           # 隐藏验收
```

`cases/catalog.json` 固定任务顺序。`catalog.py` 只读取文件，不执行材料中的 Python。
编辑 Markdown、Python 材料或 task.json 即可修改该题，无需编辑运行器。
加载器验证文件映射，拒绝越界和符号链接，禁止将 private 文件映射为公开仓库材料。

实验通过 `load_host_tasks()` 读取字节对应的文本；coding 只执行配对、渲染和运行。
每次运行根据 repo_files 清单创建工作区副本，再独立生成 docs/reference.md；
private、task.json 和其他题目的文件不会复制进去。运行时编辑不回写原始材料。

主任务材料与相邻的 provider_atomic 原子任务目录独立。通用 Agent 提示词、
参考渲染模板和评分逻辑仍归运行组件，不属于具体某题的材料。
