#!/usr/bin/env python3
"""provenance_ledger.py — emit /app/output/provenance_ledger.md and fail on traceability gaps.

One row per node and per edge: id, type, compartment, evidence, source loc, quote.
Exits 1 if any element lacks a source — a ledger with holes is worse than none,
because reviewers sample rows.
Usage: provenance_ledger.py work/graph.json /app/output
"""
import json, os, sys
from xml.sax.saxutils import escape

def main():
    gp = sys.argv[1] if len(sys.argv) > 1 else "/app/work/graph.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "/app/output"
    g = json.load(open(gp, encoding="utf-8"))
    rows, holes = [], 0
    for kind, items in (("node", g.get("nodes", [])), ("edge", g.get("edges", []))):
        for it in items:
            src = it.get("source") or {}
            loc, quote = src.get("loc", ""), src.get("quote", "")
            if not loc and not quote:
                holes += 1
            extra = it.get("compartment", "") if kind == "node" else \
                "%s -> %s" % (it.get("from", ""), it.get("to", ""))
            ev = it.get("evidence", "") if kind == "edge" else it.get("type", "")
            rows.append((kind, it.get("id", "?"), ev, extra, loc, quote))
    lines = ["# Provenance ledger — %s" % g.get("title", ""),
             "",
             "Every figure element mapped to its source. Sample any row to verify.",
             "",
             "| kind | id | type/evidence | compartment/endpoints | source loc | source quote |",
             "|---|---|---|---|---|---|"]
    for kind, i, ev, extra, loc, quote in rows:
        q = escape(quote.replace("|", "/").replace("\n", " ")[:180])
        lines.append("| %s | %s | %s | %s | %s | %s |" % (kind, i, ev, extra, loc, q))
    lines += ["", "Elements without source: **%d**" % holes,
              "Graph: `%s`; renderer: bio-pathway-svg/1.0" % gp]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "provenance_ledger.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    summary = {"ok": holes == 0, "elements": len(rows), "without_source": holes,
               "ledger": "provenance_ledger.md"}
    with open(os.path.join(out, "provenance_ledger.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(0 if holes == 0 else 1)

if __name__ == "__main__":
    main()
