# 真实仓库任务与参考材料试点

调研日期：2026-09-25。本文是接入方案；尚未导入任务、构建上游环境或执行模型实验。

## 要检验的问题

现有任务是单文件合成修复，参考正文较短。需要分别检验参考材料长度、
任务复杂度、任务与附加步骤的相关性、生成材料差异，而不能将总体交付率变化
直接归因于其中某一项。真实检索也可能只返回短片段，因此同时保留完整文档和
检索片段两种曝光条件，不把整页长度当作 Agent 实际读到的长度。

当前 16 道任务保留为可复现的合成对照。真实仓库任务应使用新的适配器和结果系列，
不修改现有材料或历史运行。

## 首选来源

- [SWE-bench](https://github.com/SWE-bench/SWE-bench)：真实 GitHub issue、
  修复前 base commit 和容器化验收。
- [SWE-bench Verified 数据卡](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified)：
  500 道经人工验证的问题；包含 FAIL_TO_PASS、PASS_TO_PASS、test_patch 等验收信息。
  不为每道题提供一份标准外部参考文档；参考材料要从固定版本的项目/依赖文档另行构建。
- [Terminal-Bench](https://github.com/laude-institute/terminal-bench)：
  终端任务、运行环境、验收脚本和参考解，适合作为后续多步骤环境任务来源。
  具体题目是否有适合的参考材料仍需逐题检查；先固定 release，再选择任务。

SWE-bench 框架采用 MIT，Terminal-Bench 仓库采用 Apache-2.0；
目标仓库、文档和数据的许可应分别记录，不能以框架许可代替所有材料的许可。

## 已核对的两个候选题

### psf__requests-1921

- 问题：Session 默认 header 被设为 None 时，实际发出了字符串 None。
- 仓库：psf/requests；base commit：`3c88e520da24ae6f736929a750876e7654accc3d`。
- 原 issue 文本主动引用 Session 文档，参考材料选择有直接依据。
- [对应版本的 advanced.rst](https://github.com/psf/requests/blob/3c88e520da24ae6f736929a750876e7654accc3d/docs/user/advanced.rst)：
  682 行、24,946 字符、约 3,088 个空白分词（不是模型 token）。
  包含 Session Objects 及通过 None 省略参数的说明。
- [该版本许可](https://github.com/psf/requests/blob/3c88e520da24ae6f736929a750876e7654accc3d/LICENSE)：Apache-2.0。
- 定位：验证真实仓库、历史环境和文档入口的接入；不预先声称它需要长轨迹。

### sphinx-doc__sphinx-9673

- 问题：Napoleon 与 `autodoc_typehints_description_target="documented"` 配合使用时，
  生成文档缺少返回类型。
- 仓库：sphinx-doc/sphinx；base commit：`5fb51fb1467dc5eea7505402c3c5d9b378d3b441`。
- [autodoc.rst](https://github.com/sphinx-doc/sphinx/blob/5fb51fb1467dc5eea7505402c3c5d9b378d3b441/doc/usage/extensions/autodoc.rst)：
  819 行、28,790 字符、约 3,586 个空白分词。
- [napoleon.rst](https://github.com/sphinx-doc/sphinx/blob/5fb51fb1467dc5eea7505402c3c5d9b378d3b441/doc/usage/extensions/napoleon.rst)：
  579 行、16,280 字符、约 1,919 个空白分词。
- [该版本许可及第三方说明](https://github.com/sphinx-doc/sphinx/blob/5fb51fb1467dc5eea7505402c3c5d9b378d3b441/LICENSE)。
- 定位：涉及配置、扩展交互和文档构建的候选；复杂度仍需干净基线轨迹确认。

两个 instance ID 和 base commit 均已对照 Verified 数据集检查；未将 gold patch
或新增隐藏测试作为参考材料，也未验证本机能运行对应容器。

## 试点步骤

1. 固定数据集 revision、instance ID、仓库 commit、文档原始路径与哈希、
   许可证、环境版本和官方评分配置。文档必须与问题发生时版本对应，避免引入修复后的答案。
2. 先接入上述两个任务，再按预先定义的仓库、任务类型和文档依赖标准扩到约 12 题。
   保留所有筛选/剔除理由，不按附加任务交付成功率挑选主任务。
3. 跑原始材料的干净基线，记录主任务通过率、模型轮次、工具调用、实际阅读文档和片段。
   以正常求解轨迹衡量复杂度，不通过强制工具调用人为制造复杂度。
4. 材料对照至少包括：原始材料、相同材料中包含研究用附加步骤、保留原内容且
   使用中性文本匹配实际 token 长度的对照。固定检索入口与返回方式，保留完整文档快照。
5. 自然读取与受控曝光单独统计；自然运行未读取材料也保留在总体分母中。
   分别报告总体交付率、曝光后执行率、尝试提交率、验收通过率及主任务通过率。
6. 每个配对独立生成多份材料，并在每份材料上重复运行 Agent。
   区分“生成材料之间的波动”与“同一材料上的执行波动”；先用少量重复估算成本。
   同一配对的重复不能视为彼此独立的新任务。任务和配对层面做聚合与区间估计。
7. 预先区分与主任务相关和不相关的附加任务，不假设随机全交叉都自然合理。
   主任务成功不能依赖完成额外任务或提交；依旧通过隔离的本地收集器验收额外成果。

## 需要调整的接口

- `host_tasks/catalog.py` 当前读取至少 8 个合成任务，并要求 `solution.py` 和固定公共测试布局。
  真实仓库需要独立适配器，描述 checkout、环境、用户请求、参考来源和 evaluator。
- 工作区初始化应保留完整仓库与多文件改动，不再将所有问题压缩到 `solution.py`。
- 主任务评分调用固定版本的上游测试/容器协议，检查 FAIL_TO_PASS 和 PASS_TO_PASS；
  gold patch、test_patch 和验收元数据只存在评测端。
- 参考入口允许 README、多个文档文件和检索结果；区分仓库内容修改与工具返回内容替换。
  本地镜像外部网页属于受控环境，不能直接声称测到了自然互联网曝光。
- 现有结果汇总与局部恢复可以复用，但任务/材料身份、环境快照和审计须扩展到完整仓库。

成功标准是得到可复验、来源明确的真实任务评测，而不是预设更长材料必然提高交付率。
