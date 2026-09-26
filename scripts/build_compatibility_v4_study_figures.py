"""Render the SVG figures used by docs/paper/compatibility_v4_study.md."""

from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/figures"
OUTPUT.mkdir(parents=True, exist_ok=True)

BLUE = "#377eb8"
ORANGE = "#e68632"
GREEN = "#4daf4a"
RED = "#d95f5f"
GRAY = "#6b7280"
LIGHT = "#eef2f7"
INK = "#172033"


def svg(width, height, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">\n'
            '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172033}'
            '.title{font-size:20px;font-weight:700}.label{font-size:14px}'
            '.small{font-size:12px;fill:#4b5563}.value{font-size:14px;font-weight:700}'
            '.axis{stroke:#9ca3af;stroke-width:1}.grid{stroke:#e5e7eb;stroke-width:1}</style>\n'
            + body + "\n</svg>\n")


def text(x, y, value, cls="label", anchor="start", fill=None):
    color = f' fill="{fill}"' if fill else ""
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{color}>{escape(str(value))}</text>'


def funnel():
    stages = [
        ("All runs", 1920, BLUE),
        ("Primary reference read", 1428, "#5b8fc0"),
        ("Embedded block seen", 1240, ORANGE),
        ("Submission attempted", 726, "#d79a3e"),
        ("Valid delivery", 722, GREEN),
        ("Joint success", 693, "#3f9650"),
    ]
    width, height = 900, 390
    out = [text(450, 32, "Execution Funnel (N = 1,920)", "title", "middle")]
    max_width = 690
    for i, (label, count, color) in enumerate(stages):
        y = 58 + i * 51
        bar = max_width * count / 1920
        out.append(f'<rect x="180" y="{y}" width="{bar:.1f}" height="32" rx="5" fill="{color}"/>')
        out.append(text(165, y + 21, label, "label", "end"))
        out.append(text(190 + bar, y + 21, f"{count:,}  ({count / 1920:.1%})", "value"))
    out.append(text(450, 375, "Only runs that actually saw the embedded block attempted delivery.", "small", "middle"))
    (OUTPUT / "execution_funnel.svg").write_text(svg(width, height, "\n".join(out)))


def grouped_bars():
    metrics = ["Block seen", "Valid delivery", "Valid | seen"]
    related = [60.8, 50.8, 83.6]
    control = [64.2, 37.5, 58.4]
    width, height = 860, 450
    left, top, plot_h = 90, 65, 300
    out = [text(430, 30, "Effect of Domain Relevance", "title", "middle")]
    for value in range(0, 101, 20):
        y = top + plot_h - value / 100 * plot_h
        out += [f'<line x1="{left}" y1="{y}" x2="820" y2="{y}" class="grid"/>',
                text(left - 12, y + 5, value, "small", "end")]
    centers = [220, 455, 690]
    for i, center in enumerate(centers):
        for offset, value, color in [(-38, related[i], BLUE), (38, control[i], ORANGE)]:
            h = value / 100 * plot_h
            x = center + offset - 29
            y = top + plot_h - h
            out.append(f'<rect x="{x}" y="{y:.1f}" width="58" height="{h:.1f}" rx="3" fill="{color}"/>')
            out.append(text(center + offset, y - 7, f"{value:.1f}%", "value", "middle"))
        out.append(text(center, 392, metrics[i], "label", "middle"))
    out += [f'<rect x="275" y="420" width="16" height="12" fill="{BLUE}"/>',
            text(298, 431, "Domain-related pairs", "small"),
            f'<rect x="505" y="420" width="16" height="12" fill="{ORANGE}"/>',
            text(528, 431, "Same atomic tasks on other hosts", "small")]
    (OUTPUT / "relevance_effect.svg").write_text(svg(width, height, "\n".join(out)))


def clean_comparison():
    labels = ["Host pass", "Reference read", "Tokens", "Tool calls", "LLM calls", "Latency"]
    clean = [100, 100, 100, 100, 100, 100]
    wrapped = [100.6, 99.9, 138.6, 113.1, 114.2, 124.5]
    width, height = 940, 450
    left, top, plot_h = 80, 65, 290
    out = [text(470, 30, "Clean vs Embedded Condition (Clean = 100)", "title", "middle")]
    for value in range(0, 151, 25):
        y = top + plot_h - value / 150 * plot_h
        out += [f'<line x1="{left}" y1="{y}" x2="910" y2="{y}" class="grid"/>',
                text(left - 10, y + 5, value, "small", "end")]
    for i, label in enumerate(labels):
        center = 145 + i * 135
        for offset, value, color in [(-25, clean[i], GRAY), (25, wrapped[i], BLUE)]:
            h = value / 150 * plot_h
            x = center + offset - 19
            y = top + plot_h - h
            out.append(f'<rect x="{x}" y="{y:.1f}" width="38" height="{h:.1f}" rx="3" fill="{color}"/>')
        out.append(text(center, 382, label, "small", "middle"))
    out += [f'<rect x="330" y="416" width="16" height="12" fill="{GRAY}"/>',
            text(353, 427, "Clean", "small"),
            f'<rect x="470" y="416" width="16" height="12" fill="{BLUE}"/>',
            text(493, 427, "Embedded", "small")]
    (OUTPUT / "clean_comparison.svg").write_text(svg(width, height, "\n".join(out)))


def position_ablation():
    labels = ["Middle", "Near end", "End A", "End B", "End C", "End pooled"]
    values = [25.0, 20.3, 45.3, 35.2, 39.8, 40.1]
    colors = [GRAY, GRAY, BLUE, BLUE, BLUE, GREEN]
    width, height = 900, 430
    left, top, plot_h = 80, 60, 280
    out = [text(450, 30, "Placement Ablation: Valid Delivery Rate", "title", "middle")]
    for value in range(0, 51, 10):
        y = top + plot_h - value / 50 * plot_h
        out += [f'<line x1="{left}" y1="{y}" x2="870" y2="{y}" class="grid"/>',
                text(left - 10, y + 5, f"{value}%", "small", "end")]
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        x = 105 + i * 125
        h = value / 50 * plot_h
        y = top + plot_h - h
        out.append(f'<rect x="{x}" y="{y:.1f}" width="75" height="{h:.1f}" rx="4" fill="{color}"/>')
        out.append(text(x + 37.5, y - 8, f"{value:.1f}%", "value", "middle"))
        out.append(text(x + 37.5, 370, label, "label", "middle"))
    out.append(text(450, 410, "End C is the comparable 4 × 4 subset of the full-matrix run.", "small", "middle"))
    (OUTPUT / "placement_ablation.svg").write_text(svg(width, height, "\n".join(out)))


def case_study():
    width, height = 980, 350
    out = [text(490, 30, "Case Study: Cursor Pagination Repair", "title", "middle")]
    lanes = [
        ("Clean reference", 92, BLUE,
         [("Inspect", 150), ("Read docs", 275), ("Patch", 400), ("Test", 525), ("Finish", 650)]),
        ("Embedded task", 225, ORANGE,
         [("Inspect", 150), ("Read block", 275), ("Patch", 400), ("Test", 525),
          ("Build artifact", 650), ("Submit", 790), ("Verify", 900)]),
    ]
    for label, y, color, nodes in lanes:
        out.append(text(110, y + 5, label, "label", "end"))
        out.append(f'<line x1="140" y1="{y}" x2="920" y2="{y}" stroke="{color}" stroke-width="4"/>')
        for node, x in nodes:
            out.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{color}"/>')
            out.append(text(x, y - 18 if y < 150 else y + 30, node, "small", "middle"))
    out += [text(490, 310, "Both runs completed the host repair; only the embedded condition created and delivered the atomic artifact.", "small", "middle"),
            text(490, 332, "Comparable pair: coding-07 × regression-empty-page, repeat 2", "small", "middle")]
    (OUTPUT / "case_study_timeline.svg").write_text(svg(width, height, "\n".join(out)))


if __name__ == "__main__":
    funnel()
    clean_comparison()
    grouped_bars()
    position_ablation()
    case_study()
    print(f"Wrote figures to {OUTPUT}")
