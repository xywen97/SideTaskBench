"""Generate the project entry report from retained runs; no model calls."""

from collections import Counter
import html
import json
from pathlib import Path

from compute_bench.report import answer_format, write_report


def main():
    root = Path(__file__).resolve().parents[1]
    experiments = []
    groups = []
    total_usage = Counter()
    total_calls = 0
    for directory in sorted((root / "runs").iterdir()):
        if not (directory / "manifest.json").exists():
            continue
        summary = write_report(directory)
        manifest = json.loads((directory / "manifest.json").read_text())
        results = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()]
        audit_path = directory / "audit.json"
        audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
        experiments.append({"name": directory.name, "runs": len(results), "model": manifest["settings"]["model"],
                            "thinking": manifest["settings"].get("thinking", "default"),
                            "attack_variant": manifest.get("attack_variant", "worksheet_v1"),
                            "audit_passed": audit.get("passed"), "tokens": summary["total_usage"]["total_tokens"],
                            "report": f"runs/{directory.name}/report.html"})
        total_usage.update(summary["total_usage"])
        total_calls += sum(result["llm_calls"] for result in results)
        groups.extend({"experiment": directory.name, **group} for group in summary["groups"])

    def group(experiment, condition, defense="none"):
        return next(item for item in groups if item["experiment"] == experiment and item["condition"] == condition and item["defense"] == defense)

    wrapped = group("validation_main", "wrapped")
    direct = group("validation_main", "direct")
    egress = group("validation_defenses", "wrapped", "egress")
    boundary = group("validation_defenses", "wrapped", "boundary")
    validation = [item for item in experiments if item["name"].startswith("validation_")]
    final_results = [json.loads(line) for line in (root / "runs/validation_main/results.jsonl").read_text().splitlines()]
    proof = next((item for item in final_results if item["joint_success"] and answer_format(item["final_content"])["json_only"]), None)
    overview = {"total_runs": sum(item["runs"] for item in experiments),
                "validation_runs": sum(item["runs"] for item in validation),
                "total_llm_calls": total_calls, "total_usage": dict(total_usage),
                "experiments": experiments, "groups": groups,
                "all_audited": all(item["audit_passed"] for item in experiments),
                "clean_json_success_example": proof["run_id"] if proof else None}
    (root / "RESULTS.json").write_text(json.dumps(overview, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 已完成的真实 LLM 验证", "",
             f"使用 `.env` 配置的 `deepseek-v4-flash`，完成 **{overview['total_runs']} 次真实 Agent 运行**，其中正式验证 {overview['validation_runs']} 次。正式验证保持默认推理模式；API 返回模型别名为 `deepseek-flash`。", "",
             f"核心结果：任务相关包装 **{wrapped['valid_deliveries']}/{wrapped['runs']}** 次取得正确的第三方计算成果；直接请求为 **{direct['valid_deliveries']}/{direct['runs']}**。跨三次重复去重后，收齐 **{wrapped['unique_accepted_tasks']}/10 子任务、{wrapped['unique_accepted_rows']}/60 条记录**。单轮未收齐全部子任务，完整大任务来自跨轮并集。", "",
             "正式验证的 200 次运行均完成，原任务三个事实均正确。此处不等同于满足全部输出格式约束：主包装成功的 15 次中，2 次最终回答为纯 JSON，7 次为纯 JSON 或单独 JSON 代码块；其它回答附带额外说明。", "",
             "| 实验 | 条件 | 防御 | 运行 | 提交尝试运行 | 正确工作可见 | 有效交付 | 主事实通过 | 独立有效记录 | 平均总 token |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for item in groups:
        if not item["experiment"].startswith("validation_"):
            continue
        lines.append("| " + " | ".join(str(item[key]) for key in ("experiment", "condition", "defense", "runs", "submission_attempted", "correct_work_observed", "valid_deliveries", "main_pass", "unique_accepted_rows", "mean_total_tokens")) + " |")
    lines += ["", f"任务边界防御：{boundary['correct_work_observed']}/{boundary['runs']} 次观察到正确额外工作，{boundary['valid_deliveries']} 次交付。仅限制外发：{egress['correct_work_observed']}/{egress['runs']} 次已产生正确额外工作，但交付全部被拦截。这说明阻止回传与阻止计算挪用是两项不同能力。", "",
              f"主包装组相对配对 clean 平均增加 {wrapped['mean_delta_tokens_vs_clean']:,.1f} token；相对字符等长对照平均增加 {wrapped['mean_delta_tokens_vs_length_control']:,.1f} token。该差值包含上下文重放和回答变化，不能解释为精确的被挪用计算量。", "",
              "部分无注入对照也尝试调用提交工具，但内容不对应众包任务且被拒收。因此，提交尝试不是该威胁成立的判据；本项目要求独立验收通过和真实交付。", "",
              "## 可直接复核的证据", ""]
    if proof:
        run_id = proof["run_id"]
        lines += [f"- 最终回答为纯 JSON、主事实正确且第三方成功交付的样本：`{run_id}`。",
                  f"- [完整轨迹](runs/validation_main/traces/{run_id}.jsonl) 与 [评分、工具事件和收据](runs/validation_main/results/{run_id}.json)。"]
    lines += ["- [实际收集的大任务成果：60 条记录](runs/validation_main/collected_batch.json)。",
              "- [收集服务收到的原始记录](runs/validation_main/collector/receipts.jsonl)。",
              "- [主实验离线审计](runs/validation_main/audit.json)、[防御审计](runs/validation_defenses/audit.json)、[检索排序审计](runs/validation_natural/audit.json)。", "",
              "## 保留的调试与正式运行", "",
              "| 目录 | 运行数 | 包装 | 推理模式 | 总 token | 离线审计 |", "|---|---:|---|---|---:|---|"]
    for item in experiments:
        lines.append(f"| [{item['name']}]({item['report']}) | {item['runs']} | {item['attack_variant']} | {item['thinking']} | {item['tokens']:,} | {item['audit_passed']} |")
    lines += ["", "初始 worksheet_v1 的直接请求及包装未成功；release_verification_v2 成功 1/2；maintenance_v3 pilot 成功 2/2，随后冻结这一包装执行正式矩阵。额外测试关闭推理的 worksheet_v1 仍为 0/2，未用于正式结果。失败尝试全部保留。", "",
              f"记录的模型调用共 **{total_calls} 次**；返回用量为输入 **{total_usage['prompt_tokens']:,}**、输出 **{total_usage['completion_tokens']:,}**，合计 **{total_usage['total_tokens']:,} token**。reasoning token 已包含在输出中。另一次连通性检查消耗 62 token，不计入上述 Agent 运行矩阵。", "",
              "## 实验解释", "",
              "- 所有正式条件共用相同用户任务和基础 Agent；boundary 是明确标注的防御提示变体。模型自行生成分类结果，脚本没有替它提交或补齐答案。",
              "- 未设置生成 token 上限或累计 token 预算；没有货币单价，因此不宣称实际盈利。",
              "- 60 个记录 ID 来自 12 个文本模板；这是一个任务家族内的机制验证，不是跨领域或模型排名结果。",
              "- 第三方来源包含合法任务必需的事实，本地有限语料内的曝光率较高；不能推广为互联网投放成功率。",
              "- 离线审计验证产物一致性，不是服务商签名或防篡改证明。最初 pilot_v1 缺少源代码快照，审计对此保留 warning；之后均有快照。", "",
              "[完整设计与复现命令](README.md) · [独立审查](docs/REVIEW.md) · [相关工作](docs/RELATED_WORK.md)", ""]
    markdown = "\n".join(lines)
    (root / "RESULTS.md").write_text(markdown)
    table_rows = "".join("<tr>" + "".join("<td>" + html.escape(str(item[key])) + "</td>" for key in ("experiment", "condition", "defense", "runs", "correct_work_observed", "valid_deliveries", "main_pass", "unique_accepted_rows")) + "</tr>" for item in groups if item["experiment"].startswith("validation_"))
    links = "".join(f'<li><a href="{item["report"]}">{html.escape(item["name"])}</a> · {item["runs"]} 次运行 · {item["tokens"]:,} token</li>' for item in experiments)
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agent 计算任务挪用 PoC · 实验结果</title><style>body{{font:16px/1.65 system-ui,sans-serif;background:#f4f6fb;color:#172339;margin:0;padding:36px}}main{{max-width:1220px;margin:auto}}h1{{font-size:36px;line-height:1.2}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:white;border:1px solid #dde3ec;border-radius:14px;padding:24px;margin:16px 0;overflow:auto}}.cards .card{{flex:1;min-width:180px}}strong.big{{font-size:36px;color:#146e53}}th,td{{padding:11px;border-bottom:1px solid #e2e7ef;text-align:left}}table{{border-collapse:collapse;width:100%;font-size:14px}}th{{background:#edf2f8}}a{{color:#2856b1}}pre{{white-space:pre-wrap;font:14px/1.7 ui-monospace,monospace}}</style><main><h1>Agent 计算任务挪用 PoC</h1><p>真实 DeepSeek 调用 · 本地合成任务 · 可核验 HTTP 交付 · 全部成功与失败试验留档</p><div class="cards"><div class="card"><strong class="big">{overview['total_runs']}</strong><br>真实 Agent 运行</div><div class="card"><strong class="big">{wrapped['valid_deliveries']}/{wrapped['runs']}</strong><br>包装任务有效交付</div><div class="card"><strong class="big">{wrapped['unique_accepted_rows']}/60</strong><br>跨重复聚合的正确记录</div><div class="card"><strong class="big">{egress['correct_work_observed']}/30</strong><br>外发被挡住但已产生正确工作</div></div><div class="card"><h2>正式验证</h2><table><tr><th>Experiment</th><th>Condition</th><th>Defense</th><th>Runs</th><th>Valid work</th><th>Delivered</th><th>Facts correct</th><th>Unique rows</th></tr>{table_rows}</table><p>主事实正确与输出格式遵循分开评分；完整大任务来自三轮并集。60条记录使用12个文本模板。</p></div><div class="card"><h2>报告与原始证据</h2><p><a href="RESULTS.md">中文结果报告</a> · <a href="README.md">设计与复现</a> · <a href="runs/validation_main/collected_batch.json">实际收到的60条结果</a> · <a href="docs/REVIEW.md">独立审查</a></p><ul>{links}</ul></div><div class="card"><h2>完整说明</h2><pre>{html.escape(markdown)}</pre></div></main></html>'''
    (root / "RESULTS.html").write_text(page)
    print(json.dumps({"runs": overview["total_runs"], "llm_calls": total_calls, "tokens": total_usage["total_tokens"], "audited": overview["all_audited"], "entry": str(root / "RESULTS.html")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
