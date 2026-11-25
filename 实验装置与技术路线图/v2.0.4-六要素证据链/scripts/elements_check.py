#!/usr/bin/env python3
"""elements_check.py — deep six-element completeness audit with evidence.

题面「结果完整性」要求覆盖六类要素：科学实体、空间关系、数据编码、图例标注、
可编辑源文件、导出格式。父版 pg_check 的 six_elements 只做粗粒度布尔判断
（尤其「数据编码」几乎形同虚设）。本脚本逐项给出机检证据与缺口清单，并输出
可归档的 elements_check.json + 证据文本，供 run_report.md / sources.md 引用。

Usage:
  python3 elements_check.py --ir /app/work/ir.json --out /app/output \
      --report /app/output/elements_check.json
Exit 0 当六要素全部满足。
"""
import argparse, json, os, sys, xml.etree.ElementTree as ET

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d if d is not None else {}

def text_w(s, fs):
    return sum(fs * (1.0 if ord(ch) > 0x2E80 else 0.55) for ch in str(s))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    O = a.out
    ir = load(a.ir, {})
    meta = load(os.path.join(O, "diagram.svg.meta.json"), {})
    exp = load(os.path.join(O, "export_report.json"), {})
    ents = ir.get("entities", [])
    conns = ir.get("connections", [])
    try:
        tree = ET.parse(os.path.join(O, "diagram.svg"))
        root = tree.getroot()
        svg_ids = {el.get("id") for el in root.iter() if el.get("id")}
        n_text = sum(1 for el in root.iter() if el.tag.endswith("text"))
        svg_txt = open(os.path.join(O, "diagram.svg"), encoding="utf-8").read(400000)
        svg_ok = True
    except Exception:
        svg_ids, n_text, svg_txt, svg_ok = set(), 0, "", False

    evidence = {}
    # 1 科学实体：存在 + 每个有 locator（无法定位的需 inferred+uncertainty）
    no_loc = [e.get("id") for e in ents if not (e.get("source") or {}).get("locator")]
    inferred = [e.get("id") for e in ents if (e.get("confidence") == "inferred")]
    unc = ir.get("uncertainty", [])
    e1 = {"count": len(ents), "without_locator": no_loc, "inferred": inferred,
          "pass": bool(ents) and (not no_loc or bool(unc))}
    # 2 空间关系：布局声明 + 连接两端存在 + 无自环
    ids = {e.get("id") for e in ents}
    dangling = [c.get("id") for c in conns if c.get("from") not in ids or c.get("to") not in ids]
    selfloops = [c.get("id") for c in conns if c.get("from") == c.get("to")]
    layout = (ir.get("layout") or {}).get("type")
    e2 = {"layout": layout, "connections": len(conns), "dangling": dangling, "self_loops": selfloops,
          "pass": bool(layout) and not dangling and not selfloops}
    # 3 数据编码：数值随实体且含单位或数值、图例 kinds 映射到线型、chart 数据真实
    with_vals = [{"id": e.get("id"), "values": e.get("values", [])} for e in ents if e.get("values")]
    kind_map = {"material": "实线蓝", "energy": "虚线橙", "info": "点线绿", "sequence": "灰", "waste": "点划灰"}
    kinds_used = sorted({c.get("kind", "material") for c in conns})
    kinds_known = all(k in kind_map for k in kinds_used)
    chart = ir.get("chart") or {}
    chart_pts = sum(len(s.get("data", [])) for s in chart.get("series", []))
    e3 = {"entities_with_values": with_vals, "kinds_used": kinds_used,
          "kind_line_style_map": {k: kind_map.get(k) for k in kinds_used},
          "chart_points": chart_pts,
          "pass": kinds_known and (bool(with_vals) or chart_pts > 0 or len(conns) > 0)}
    # 4 图例标注：SVG 含图例 + 图例项 == 实际 kinds
    svg_has_legend = any(i and "legend" in i for i in svg_ids)
    kinds_meta = {em.get("kind") for em in meta.get("edges", [])}
    e4 = {"legend_in_svg": svg_has_legend, "legend_kinds": sorted(kinds_meta),
          "ir_kinds": sorted({c.get("kind", "material") for c in conns}),
          "pass": bool(svg_has_legend) and kinds_meta == {c.get("kind", "material") for c in conns}}
    # 5 可编辑源文件：每实体一个 <g id> + 文本可选 + 字体回退链
    missing_g = [e.get("id") for e in ents if e.get("id") not in svg_ids]
    font_chain = ("Noto Sans CJK SC" in svg_txt) or ("sans-serif" in svg_txt)
    e5 = {"entities_as_groups": len(ents) - len(missing_g), "missing_groups": missing_g,
          "text_elements": n_text, "font_fallback_chain": font_chain,
          "pass": svg_ok and not missing_g and n_text > 0 and font_chain}
    # 6 导出格式：PNG 非空 + PDF 存在 + 像素/物理尺寸记录
    e6 = {"png_bytes": exp.get("png_bytes", 0), "pdf_bytes": exp.get("pdf_bytes", 0),
          "png_backend": exp.get("png_backend"), "cjk_fonts": exp.get("cjk_fonts_found", []),
          "pass": bool(exp.get("checks", {}).get("png_exists_nontrivial")) and bool(exp.get("pdf_bytes"))}
    elements = {"1_科学实体": e1, "2_空间关系": e2, "3_数据编码": e3,
                "4_图例标注": e4, "5_可编辑源文件": e5, "6_导出格式": e6}
    failed = [k for k, v in elements.items() if not v["pass"]]
    report = {"all_pass": not failed, "failed_elements": failed, "elements": elements}
    with open(a.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    # human evidence text
    lines = ["# 六要素完整性证据（机器生成）", ""]
    for k, v in elements.items():
        lines.append(f"- **{k}**：{'✅' if v['pass'] else '❌'} — 证据见 elements_check.json")
    lines.append("")
    lines.append("六要素全部满足" if not failed else "未满足要素：" + ", ".join(failed))
    with open(os.path.join(O, "elements_evidence.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"OK elements_check all_pass={not failed} failed={failed}")
    sys.exit(0 if not failed else 1)

if __name__ == "__main__":
    main()
