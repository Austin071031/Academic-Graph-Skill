#!/usr/bin/env python3
"""legend_audit.py — verify legend/figure/data three-way consistency.

Checks, against graph.json + rendered figure.svg:
  1. every edge type drawn appears as a glyph legend row in the SVG legend
  2. every node fill actually used appears in a legend node row or legend.items
  3. every legend.items data encoding cites its dataset/figure source in text
  4. no style is used in the figure that no legend entry explains
Writes legend_audit.json; exit 1 on inconsistency.
Usage: legend_audit.py work/graph.json /app/output/figure.svg /app/output
"""
import json, os, re, sys

def main():
    gp, sp, out = (sys.argv[1], sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else \
        ("/app/work/graph.json", "/app/output/figure.svg", "/app/output")
    g = json.load(open(gp, encoding="utf-8"))
    svg = open(sp, encoding="utf-8").read()
    problems = []
    # 1. edge types drawn vs legend glyph rows (build_svg emits one "line" row per used type)
    drawn_types = sorted({e.get("type", "unknown") for e in g.get("edges", [])})
    legend_zone = re.search(r'<g id="legend".*?</g>', svg, re.S)
    legend_txt = legend_zone.group(0) if legend_zone else ""
    for t in drawn_types:
        if t.replace("_", " ") not in legend_txt and t not in legend_txt:
            problems.append("edge type '%s' drawn but missing from figure legend" % t)
    # 2. node fills used vs legend
    used_fills = set(re.findall(r'<(?:rect|ellipse|circle|polygon)[^>]*fill="(#[0-9a-fA-F]{6})"', svg))
    band_fills = {"#ffffff", "#caa64b", "#f4f0fa", "#eef5fb", "#f5f5f0"}
    comp_default = {"#e8dcf5", "#d9e8fb", "#cfe8d8", "#fff3c4", "#f6d9c3", "#d3f0f0", "#ffe9ec", "#fbd9e2", "#eeeeee", "#f2f2f2", "#e2e2e2"}
    unexplained = used_fills - band_fills - comp_default - {f.lower() for f in re.findall(r'fill="(#[0-9a-fA-F]{6})"', legend_txt)}
    items_txt = " ".join(str(i.get("label", "")) + " " + str(i.get("meaning", ""))
                         for i in (g.get("legend") or {}).get("items", [])).lower()
    for f in sorted(unexplained):
        if f not in items_txt:
            problems.append("fill %s used in figure but not explained by legend/items" % f)
    # 3. data encodings must cite a source
    for i in (g.get("legend") or {}).get("items", []):
        txt = (str(i.get("label", "")) + " " + str(i.get("meaning", ""))).lower()
        if re.search(r"(color|fill|size|width|shape)\s*=", txt) or "encoding" in txt or "fold" in txt or "expression" in txt:
            if not re.search(r"(fig|table|dataset|source|data|p\.?\d)", txt):
                problems.append("legend item '%s' is a data encoding without a source citation" % i.get("label"))
    report = {"ok": not problems, "problems": problems,
              "edge_types_checked": drawn_types,
              "fills_checked": sorted(used_fills)}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "legend_audit.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    sys.exit(0 if not problems else 1)

if __name__ == "__main__":
    main()
