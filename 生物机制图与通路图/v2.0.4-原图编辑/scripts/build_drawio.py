#!/usr/bin/env python3
"""build_drawio.py — export graph.json to a layered, named draw.io (.drawio) diagram.

Same graph model as the SVG, so the two editable sources stay consistent.
Cells are named node-<id>/edge-<id> and compartments are background swimlanes,
so a human can open the file, change one label and re-export.
Usage: build_drawio.py work/graph.json /app/output/figure.drawio
"""
import json, math, sys
from xml.sax.saxutils import escape

DRAWIO_EDGE = {
    "activation": "endArrow=block;html=1;",
    "induction": "endArrow=block;html=1;",
    "expression": "endArrow=block;html=1;",
    "inhibition": "endArrow=open;endSize=12;html=1;",
    "repression": "endArrow=open;endSize=12;html=1;",
    "binding": "endArrow=none;html=1;",
    "association": "endArrow=none;html=1;",
    "phosphorylation": "endArrow=block;html=1;strokeColor=#7a3db0;",
    "dephosphorylation": "endArrow=block;html=1;strokeColor=#7a3db0;dashed=1;",
    "ubiquitination": "endArrow=block;html=1;strokeColor=#b06a1a;",
    "translocation": "endArrow=block;html=1;dashed=1;strokeColor=#0f6b6b;",
    "transport": "endArrow=block;html=1;dashed=1;strokeColor=#0f6b6b;",
}
FILL = {"gene": "#fff3c4", "protein": "#d9e8fb", "receptor": "#cfe8d8",
        "complex": "#e8dcf5", "small_molecule": "#f6d9c3", "ion": "#d3f0f0",
        "phenotype": "#fbd9e2", "mrna": "#ffe9ec"}

def main():
    gp, op = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("/app/work/graph.json", "/app/output/figure.drawio")
    g = json.load(open(gp, encoding="utf-8"))
    W = 1240
    comps = g.get("compartments", [])
    order = {"extracellular": 0, "membrane": 1, "cytoplasm": 2, "nucleus": 3}
    comps = sorted(comps, key=lambda c: c.get("order", order.get(c.get("id", ""), 2.5)))
    nodes, edges = g.get("nodes", []), g.get("edges", [])
    band_h = {"extracellular": 150, "membrane": 60, "cytoplasm": 320, "nucleus": 260}
    y = 60
    band = {}
    for c in comps:
        cid = c.get("id", "c%d" % y)
        h = band_h.get(cid, 220)
        band[cid] = (y, h)
        y += h + 20
    H = y + 40
    cells = []
    cells.append('<mxCell id="0"/><mxCell id="1" parent="0"/>')
    for c in comps:
        cid = c.get("id")
        top, h = band[cid]
        style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f8fb;strokeColor=#b9c6d2;align=left;verticalAlign=top;fontStyle=2;"
        if cid == "membrane":
            style = "rounded=0;whiteSpace=wrap;html=1;fillColor=#e9d9a8;strokeColor=#caa64b;align=left;verticalAlign=top;fontStyle=2;"
        cells.append('<mxCell id="compartment-%s" value="%s" style="%s" vertex="1" parent="1">'
                     '<mxGeometry x="20" y="%d" width="%d" height="%d" as="geometry"/></mxCell>' %
                     (escape(str(cid)), escape(c.get("label", cid)), style, top, W - 40, h))
    per = {}
    for n in nodes:
        cid = n.get("compartment") or "cytoplasm"
        if cid not in band:
            cid = "cytoplasm" if "cytoplasm" in band else comps[0]["id"]
        per.setdefault(cid, []).append(n)
    pos = {}
    for cid, ns in per.items():
        top, h = band[cid]
        if cid == "membrane":
            step = max(150, (W - 80) / max(1, len(ns)))
            for i, n in enumerate(ns):
                pos[n["id"]] = (40 + step * i, top + 10, 130, 40)
            continue
        cols = max(1, math.ceil(math.sqrt(len(ns))))
        rows = math.ceil(len(ns) / cols)
        cw, ch = (W - 80) / cols, h / max(rows, 1)
        for i, n in enumerate(ns):
            r, c = divmod(i, cols)
            pos[n["id"]] = (40 + cw * c + 20, top + 30 + ch * r, 120, 40)
    for n in nodes:
        if n["id"] not in pos:
            continue
        x, yy, w, h = pos[n["id"]]
        t = n.get("type", "protein")
        shape = "ellipse" if t in ("gene", "mrna") else ("rhombus" if t == "ion" else "rounded=1")
        style = "%s;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=#333333;" % (
            shape + ";" if not shape.endswith(";") else shape, FILL.get(t, "#d9e8fb"))
        label = n.get("label", n["id"])
        if n.get("synonyms"):
            label += "\\n(%s)" % str(n["synonyms"])[:36]
        cells.append('<mxCell id="node-%s" value="%s" style="%s" vertex="1" parent="1">'
                     '<mxGeometry x="%.0f" y="%.0f" width="%d" height="%d" as="geometry"/></mxCell>' %
                     (escape(str(n["id"])), escape(label), style, x, yy, w, h))
    for e in edges:
        if e.get("from") not in pos or e.get("to") not in pos:
            continue
        st = DRAWIO_EDGE.get(e.get("type", "unknown"), "endArrow=block;html=1;")
        if e.get("evidence") in ("weak", "inferred", "predicted"):
            st += "dashed=1;"
        val = e.get("label") or e.get("type", "")
        cells.append('<mxCell id="edge-%s" value="%s" style="%s" edge="1" parent="1" source="node-%s" target="node-%s">'
                     '<mxGeometry relative="1" as="geometry"/></mxCell>' %
                     (escape(str(e.get("id", "e"))), escape(str(val)), st,
                      escape(str(e["from"])), escape(str(e["to"]))))
    xml = ('<mxfile host="bio-pathway" agent="%s" version="24.7.5">'
           '<diagram id="figure" name="mechanism">'
           '<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" '
           'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0">'
           '<root>%s</root></mxGraphModel></diagram></mxfile>') % (
           "bio-pathway-drawio/1.0", W, H, "".join(cells))
    with open(op, "w", encoding="utf-8") as f:
        f.write(xml)
    print(json.dumps({"ok": True, "drawio": op, "nodes": len(pos), "edges": len(edges)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
