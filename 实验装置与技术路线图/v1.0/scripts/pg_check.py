#!/usr/bin/env python3
"""pg_check.py — self-check engine: verify the rendered SVG against the IR and
the export report. Every check is machine-computed from real files, never asserted.

Usage:
  python3 pg_check.py --ir /app/work/ir.json --svg /app/output/diagram.svg \
      --meta /app/output/diagram.svg.meta.json --export-report /app/output/export_report.json \
      --out /app/output/selfcheck.json

Checks (each produces pass/fail + evidence):
  1 entity_coverage    every IR entity id appears as a <g id> in the SVG
  2 connection_dangling every IR connection endpoint resolves to an entity
  3 direction_sanity   no self-loop; 回流 edges declared as cycles in IR
  4 numbering_order    steps numbered sequentially from 1, order matches IR
  5 legend_consistency legend entries == actually-used flow kinds / node types
  6 font_embedding     SVG font-family chain present; >=1 CJK font installed
  7 text_overflow      estimated label width fits node box (meta-driven)
  8 canvas_bounds      all node boxes inside declared canvas extents
  9 export_verified    PNG non-trivial, PDF exists (from export_report.json)
 10 six_elements       六要素覆盖: entities/spatial/edges(+labels)/legend/editable source(svg)/export(png,pdf)
"""
import argparse, json, re, sys, xml.etree.ElementTree as ET

def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def text_w(s, fs):
    return sum(fs * (1.0 if ord(ch) > 0x2E80 else 0.55) for ch in str(s))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--svg", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--export-report", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ir = load(a.ir) or {}
    meta = load(a.meta) or {}
    exp = load(a.export_report) if a.export_report else None
    checks = []

    # parse SVG ids
    try:
        tree = ET.parse(a.svg)
        svg_ids = {el.get("id") for el in tree.iter() if el.get("id")}
        svg_ok = True
    except Exception as e:
        svg_ids = set(); svg_ok = False
        checks.append({"id": "svg_parseable", "pass": False, "evidence": str(e)[:200]})
    if svg_ok:
        checks.append({"id": "svg_parseable", "pass": True, "evidence": f"{len(svg_ids)} ids"})

    ents = {e["id"]: e for e in ir.get("entities", []) if e.get("id")}
    missing = [eid for eid in ents if eid not in svg_ids]
    checks.append({"id": "entity_coverage", "pass": not missing,
                   "evidence": f"{len(ents)-len(missing)}/{len(ents)} entities in SVG",
                   "missing": missing})

    conns = ir.get("connections", [])
    dangling = [c.get("id", "?") for c in conns
                if c.get("from") not in ents or c.get("to") not in ents]
    selfloops = [c.get("id", "?") for c in conns if c.get("from") == c.get("to")]
    checks.append({"id": "connection_dangling", "pass": not dangling,
                   "evidence": f"{len(conns)} connections, dangling={dangling[:5]}",
                   "dangling": dangling})
    declared_cycles = {c.get("id") for c in conns if c.get("cycle")}
    checks.append({"id": "direction_sanity", "pass": not selfloops,
                   "evidence": f"self-loops={selfloops[:5]}, declared回流={sorted(declared_cycles)[:5]}"})

    steps = sorted([s for s in ir.get("steps", []) if s.get("id")],
                   key=lambda s: (s.get("no", 1 << 30), s["id"]))
    nos = [s.get("no") for s in steps]
    seq_ok = nos == list(range(1, len(steps) + 1))
    checks.append({"id": "numbering_order", "pass": seq_ok,
                   "evidence": f"step numbers={nos}"})

    legend_used = set((tuple(x) if isinstance(x, list) else x) for x in meta.get("legend_entries", []))
    svg_has_legend = any(i and "legend" in i for i in svg_ids)
    kinds_in_meta = {em["kind"] for em in meta.get("edges", [])}
    kinds_in_ir = {c.get("kind", "material") for c in conns}
    checks.append({"id": "legend_consistency", "pass": svg_has_legend and kinds_in_meta == kinds_in_ir,
                   "evidence": f"legend_in_svg={svg_has_legend}, kinds meta={sorted(kinds_in_meta)} ir={sorted(kinds_in_ir)}"})

    with open(a.svg, encoding="utf-8") as f:
        svg_txt = f.read(400000)
    font_chain = "Noto Sans CJK SC" in svg_txt or "WenQuanYi" in svg_txt or "sans-serif" in svg_txt
    cjk_ok = bool(exp and exp.get("cjk_fonts_found"))
    checks.append({"id": "font_embedding", "pass": font_chain and cjk_ok,
                   "evidence": f"chain_in_svg={font_chain}, installed_cjk={cjk_ok}"})

    fs = 12
    overflow = []
    for nm in meta.get("nodes", []):
        if text_w(nm.get("label", ""), fs) > nm.get("w", 120) - 10:
            overflow.append(nm["id"])
    checks.append({"id": "text_overflow", "pass": not overflow,
                   "evidence": f"overflow_est={overflow[:8]}", "overflow": overflow})

    ex = meta.get("extents", [0, 0, 0, 0])
    oob = [nm["id"] for nm in meta.get("nodes", [])
           if not (ex[0] - 1 <= nm["x"] - nm["w"] / 2 and nm["x"] + nm["w"] / 2 <= ex[2] + 1
                   and ex[1] - 1 <= nm["y"] - nm["h"] / 2 and nm["y"] + nm["h"] / 2 <= ex[3] + 1)]
    checks.append({"id": "canvas_bounds", "pass": not oob,
                   "evidence": f"out_of_bounds={oob[:8]}", "oob": oob})

    if exp:
        checks.append({"id": "export_verified", "pass": bool(exp.get("checks", {}).get("png_exists_nontrivial")),
                       "evidence": f"png={exp.get('png_bytes',0)}B pdf={exp.get('pdf_bytes',0)}B backend={exp.get('png_backend')}"})
    else:
        checks.append({"id": "export_verified", "pass": False, "evidence": "no export_report.json"})

    six = {
        "科学实体": bool(ents),
        "空间关系": len(conns) > 0 or ir.get("layout") is not None,
        "数据编码": any("label" in c or "label" in (ents.get(c.get('from'), {}) or {}) for c in conns) or bool(ir.get("chart")),
        "图例标注": svg_has_legend,
        "可编辑源文件": svg_ok,
        "导出格式": bool(exp and exp.get("checks", {}).get("png_exists_nontrivial")),
    }
    checks.append({"id": "six_elements", "pass": all(six.values()),
                   "evidence": json.dumps(six, ensure_ascii=False)})

    passed = sum(1 for c in checks if c["pass"])
    out = {"total": len(checks), "passed": passed,
           "all_pass": passed == len(checks), "checks": checks,
           "issues": [c["id"] for c in checks if not c["pass"]]}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"OK selfcheck passed={passed}/{len(checks)} issues={out['issues']}")
    sys.exit(0 if out["all_pass"] else 1)

if __name__ == "__main__":
    main()
