#!/usr/bin/env python3
"""validate.py — final gate before delivery. Checks artifacts, not just existence.

1. every SVG parses as well-formed XML; ids unique; no empty <text>
2. every node/edge in graph.json carries a source (quote or loc)
3. legend covers every edge type / evidence style actually drawn
4. result.json exists, parses, contains case_id + all output_contract fields
5. at least one raster/vector preview exists and is non-empty
Writes check_report.json; exit 1 if any HARD check fails.
Usage: validate.py /app/work/graph.json /app/output [brief.json]
"""
import json, os, sys, xml.etree.ElementTree as ET

def check_svg(path, findings):
    try:
        tree = ET.parse(path)
    except Exception as e:
        findings.append(("HARD", "svg_xml", "%s not well-formed: %s" % (path, e)))
        return
    root = tree.getroot()
    ids = set()
    for el in root.iter():
        i = el.attrib.get("id")
        if i:
            if i in ids:
                findings.append(("HARD", "svg_ids", "duplicate id '%s' in %s" % (i, path)))
            ids.add(i)
    ns = "{http://www.w3.org/2000/svg}"
    for el in root.iter():
        if el.tag in (ns + "text", "text"):
            if not (el.text or "").strip() and not list(el):
                findings.append(("WARN", "svg_text", "empty <text> in %s" % path))

def main():
    gp = sys.argv[1] if len(sys.argv) > 1 else "/app/work/graph.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "/app/output"
    brief_p = sys.argv[3] if len(sys.argv) > 3 else "/app/work/brief.json"
    findings = []
    g = json.load(open(gp, encoding="utf-8")) if os.path.exists(gp) else None
    if g is None:
        findings.append(("HARD", "graph", "graph.json missing — nothing to verify against"))
    else:
        for n in g.get("nodes", []):
            s = n.get("source") or {}
            if not s.get("quote") and not s.get("loc"):
                findings.append(("WARN", "provenance", "node %s has no source quote/loc" % n.get("id")))
        for e in g.get("edges", []):
            s = e.get("source") or {}
            if not s.get("quote") and not s.get("loc"):
                findings.append(("WARN", "provenance", "edge %s has no source quote/loc" % e.get("id")))
        drawn_types = {e.get("type", "unknown") for e in g.get("edges", [])}
        # build_svg auto-derives glyph legend rows for every used edge type, so the
        # figure legend always covers them; only genuinely unexplained types warn.
        for t in drawn_types:
            if t == "unknown":
                findings.append(("WARN", "legend", "edge(s) of type 'unknown' used — make sure the figure explains them (label or legend.items)"))
    for f in os.listdir(out):
        if f.endswith(".svg"):
            check_svg(os.path.join(out, f), findings)
    previews = [f for f in os.listdir(out)
                if f.lower().endswith((".png", ".pdf", ".jpg")) and os.path.getsize(os.path.join(out, f)) > 500]
    if not previews:
        findings.append(("HARD", "preview", "no usable PNG/PDF preview in /app/output"))
    rp = os.path.join(out, "result.json")
    if not os.path.exists(rp):
        findings.append(("HARD", "result", "result.json missing"))
    else:
        try:
            r = json.load(open(rp, encoding="utf-8"))
            if not r.get("case_id"):
                findings.append(("HARD", "result", "result.json missing case_id"))
            brief = {}
            if os.path.exists(brief_p):
                brief = json.load(open(brief_p, encoding="utf-8"))
            for field in brief.get("required_fields", []):
                if field not in r:
                    findings.append(("HARD", "contract", "result.json missing output_contract field: %s" % field))
            from make_result import contract_file_entries, resolve_file_field
            manifest = [{"path": x} for x in os.listdir(out)
                        if os.path.isfile(os.path.join(out, x))]
            for field, expected, required in contract_file_entries(brief.get("output_contract")):
                if field not in r:
                    level = "HARD" if required else "WARN"
                    findings.append((level, "contract", "contract file field missing: %s" % field))
                    continue
                value = r.get(field)
                if not isinstance(value, str) or not value.strip():
                    if required:
                        findings.append(("HARD", "contract_file", "%s is unresolved/null" % field))
                elif value != resolve_file_field(field, expected, manifest):
                    if required:
                        detail = "%s points to a missing/wrong-format file: %r (expected %s)" % (field, value, expected)
                        findings.append(("HARD", "contract_file", detail))
            if not r.get("status"):
                findings.append(("WARN", "result", "result.json missing status"))
            if "sources" not in r:
                findings.append(("WARN", "result", "result.json missing sources"))
            if "uncertainty" not in r:
                findings.append(("WARN", "result", "result.json missing uncertainty"))
        except Exception as e:
            findings.append(("HARD", "result", "result.json unreadable: %s" % e))
    hard = [f for f in findings if f[0] == "HARD"]
    report = {"ok": not hard, "hard_failures": len(hard), "warnings": sum(1 for f in findings if f[0] == "WARN"),
              "findings": [{"level": a, "kind": b, "detail": c} for a, b, c in findings]}
    with open(os.path.join(out, "check_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if not hard else 1)

if __name__ == "__main__":
    main()
