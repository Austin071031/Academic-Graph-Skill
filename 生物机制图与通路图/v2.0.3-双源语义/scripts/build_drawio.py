#!/usr/bin/env python3
"""build_drawio.py — complete native mxGraph export from graph.json.

Every entity/relation is an editable object+mxCell, never HTML or a bitmap.
SVG and draw.io share the same relation vocabulary, source fields and stable IDs.
Usage: build_drawio.py /app/work/graph.json /app/output/figure.drawio
"""
import json
import math
import os
import re
import sys
from xml.sax.saxutils import escape

GEN = "bio-pathway-drawio/2.0"
WIDTH = 1240
RAIL = 320
ORDER = {"extracellular": 0, "membrane": 1, "cytoplasm": 2, "cytosol": 2,
         "golgi": 2.2, "er": 2.3, "mitochondrion": 2.4, "nucleus": 3,
         "periplasm": 1.5}
BAND_H = {"extracellular": 150, "membrane": 72, "cytoplasm": 300, "nucleus": 250}
FILLS = {"gene": ("#fff3c4", "#8a6d00"), "mrna": ("#ffe9ec", "#a3123a"),
         "protein": ("#d9e8fb", "#1d4e89"), "receptor": ("#cfe8d8", "#1e6b45"),
         "complex": ("#e8dcf5", "#5b2d8e"), "small_molecule": ("#f6d9c3", "#9a4b12"),
         "ion": ("#d3f0f0", "#0f6b6b"), "cell": ("#eeeeee", "#555555"),
         "cell_type": ("#eeeeee", "#555555"), "phenotype": ("#fbd9e2", "#8e2050"),
         "pathway": ("#e2e2e2", "#333333"), "compartment": ("#f2f2f2", "#666666")}
EDGE_STYLE = {
    "activation": "endArrow=block;endFill=0;strokeColor=#1a6b1a;",
    "induction": "endArrow=block;endFill=0;strokeColor=#1a6b1a;",
    "expression": "endArrow=block;endFill=0;strokeColor=#1a6b1a;",
    "inhibition": "endArrow=bar;endSize=12;endFill=0;strokeColor=#b01818;",
    "repression": "endArrow=bar;endSize=12;endFill=0;strokeColor=#b01818;",
    "binding": "endArrow=none;strokeColor=#333366;",
    "association": "endArrow=none;strokeColor=#333366;",
    "dissociation": "endArrow=none;dashed=1;dashPattern=4 3;strokeColor=#333366;",
    "phosphorylation": "endArrow=block;endFill=0;strokeColor=#7a3db0;",
    "dephosphorylation": "endArrow=block;endFill=0;dashed=1;dashPattern=5 3;strokeColor=#7a3db0;",
    "ubiquitination": "endArrow=block;endFill=0;strokeColor=#b06a1a;",
    "methylation": "endArrow=block;endFill=0;strokeColor=#b06a1a;",
    "cleavage": "endArrow=block;endFill=0;dashed=1;dashPattern=6 3;strokeColor=#555555;",
    "translocation": "endArrow=block;endFill=0;dashed=1;dashPattern=6 4;strokeColor=#0f6b6b;",
    "transport": "endArrow=block;endFill=0;dashed=1;dashPattern=6 4;strokeColor=#0f6b6b;",
    "secretion": "endArrow=block;endFill=0;dashed=1;dashPattern=6 4;strokeColor=#0f6b6b;",
    "input": "endArrow=block;endFill=0;dashed=1;dashPattern=2 3;strokeColor=#888888;",
    "unknown": "endArrow=open;endFill=0;dashed=1;dashPattern=2 3;strokeColor=#888888;",
}
TAG = {"phosphorylation": "P", "dephosphorylation": "P (-)",
       "ubiquitination": "Ub", "methylation": "Me"}


def esc(value):
    return escape(str(value if value is not None else ""), {"\"": "&quot;", "'": "&apos;"})


def plain(value):
    # Newlines must remain native text encoded as XML entities, not literal markup.
    return esc(str(value if value is not None else "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "&#10;"))


def style_for_edge(edge):
    kind = edge.get("type", "unknown")
    style = EDGE_STYLE.get(kind, EDGE_STYLE["unknown"])
    evidence = edge.get("evidence", "strong")
    if evidence in ("weak", "inferred", "predicted") and "dashed=" not in style:
        style += "dashed=1;dashPattern=5 4;"
    if edge.get("dash"):
        style += "dashed=1;dashPattern=%s;" % esc(edge["dash"])
    if edge.get("color"):
        style = re.sub(r"strokeColor=[^;]*;", "strokeColor=%s;" % esc(edge["color"]), style)
    width = {"strong": 2.4, "moderate": 1.9, "weak": 1.8, "inferred": 1.6, "predicted": 1.5}.get(evidence, 1.8)
    return style + "strokeWidth=%s;html=1;rounded=0;" % width


def normalize(g):
    nodes = [n for n in g.get("nodes", []) if isinstance(n, dict) and n.get("id")]
    node_ids = {n["id"] for n in nodes}
    missing = []
    edges = []
    for edge in g.get("edges", []):
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            missing.append(edge.get("id"))
        else:
            edges.append(edge)
    compartments = {c.get("id"): dict(c) for c in g.get("compartments", []) if isinstance(c, dict) and c.get("id")}
    used = []
    for node in nodes:
        node["compartment"] = node.get("compartment") or "cytoplasm"
        if node["compartment"] not in used:
            used.append(node["compartment"])
    ordered = sorted(used, key=lambda cid: compartments.get(cid, {}).get("order", ORDER.get(cid, 2.5)))
    comps = []
    for cid in ordered:
        c = compartments.get(cid, {})
        c["id"] = cid
        c["label"] = c.get("label", cid)
        c["order"] = c.get("order", ORDER.get(cid, 2.5))
        comps.append(c)
    if not any(n["compartment"] == "membrane" for n in nodes):
        pass
    elif "membrane" not in ordered:
        comps.append({"id": "membrane", "label": "Membrane", "order": 1})
        comps.sort(key=lambda c: c["order"])
    return nodes, edges, comps, missing


def geometry(nodes, comps):
    per = {}
    for n in nodes:
        per.setdefault(n["compartment"], []).append(n)
    positions, bands = {}, {}
    y = 90
    available = WIDTH - 60
    for c in comps:
        cid = c["id"]
        ns = per.get(cid, [])
        cols = max(1, min(len(ns), int(available // 192))) if ns else 1
        rows = math.ceil(len(ns) / cols) if ns else 1
        h = max(BAND_H.get(cid, 220), 44 + 90 * rows) if ns else BAND_H.get(cid, 220)
        if cid == "membrane" and ns:
            h = max(74, h)
        bands[cid] = [y, h]
        for i, n in enumerate(ns):
            kind = n.get("type", "protein")
            if kind in ("small_molecule", "ion"):
                w, hnode = 44, 44
            elif kind == "complex":
                w, hnode = 124, 48
            elif kind in ("gene", "mrna"):
                w, hnode = 108, 48
            elif kind in ("cell", "cell_type"):
                w, hnode = 150, 56
            else:
                w, hnode = 116, 44 if kind == "receptor" else 40
            if cid == "membrane":
                xstep = available / max(1, len(ns))
                x = 30 + xstep * (i + 0.5) - w / 2
                yy = y + h / 2 - hnode / 2
            else:
                r, col = divmod(i, cols)
                cw = available / cols
                x = 30 + cw * col + (cw - w) / 2
                yy = y + 32 + r * 90 + (90 - hnode) / 2
            positions[n["id"]] = (x, yy, w, hnode)
        y += h + 18
    return positions, bands, y - 18


def build(g):
    nodes, edges, comps, missing = normalize(g)
    positions, bands, body_bottom = geometry(nodes, comps)
    if not nodes:
        raise ValueError("no editable nodes after IR check")
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append('<mxCell id="title-block" value="%s" style="text;html=1;fontSize=20;fontStyle=1;align=left;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="30" y="26" width="1150" height="32" as="geometry"/></mxCell>' % plain(g.get("title", "Mechanism figure")))
    for c in comps:
        cid = c["id"]
        y, h = bands[cid]
        style = "rounded=1;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;fillColor=%s;strokeColor=%s;align=left;verticalAlign=top;fontStyle=2;fontSize=12;" % (
            "#e9d9a8" if cid == "membrane" else ("#f4f0fa" if cid == "nucleus" else "#eef5fb"),
            "#caa64b" if cid == "membrane" else ("#9a86b8" if cid == "nucleus" else "#b9c6d2"))
        cells.append('<mxCell id="compartment-%s" kind="compartment" value="%s" style="%s" vertex="1" parent="1"><mxGeometry x="24" y="%d" width="%d" height="%d" as="geometry"/></mxCell>' % (
            esc(cid), esc(c["label"]), style, y, WIDTH - 48, h))
    for n in nodes:
        x, y, w, h = positions[n["id"]]
        kind = n.get("type", "protein")
        fill, stroke = FILLS.get(kind, FILLS["protein"])
        if n.get("fill"):
            fill = n["fill"]
        if n.get("stroke"):
            stroke = n["stroke"]
        if kind in ("gene", "mrna", "small_molecule"):
            shape = "ellipse;"
        elif kind == "ion":
            shape = "rhombus;"
        elif kind == "phenotype":
            shape = "shape=hexagon;"
        else:
            shape = "rounded=1;"
        font = "fontStyle=2;" if kind == "gene" else ""
        if kind == "mrna":
            font += "dashed=1;"
        style = "%swhiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;strokeWidth=1.6;%s" % (shape, esc(fill), esc(stroke), font)
        source = n.get("source") or {}
        label = n.get("label", n["id"])
        cells.append('<object id="node-%s" label="%s" kind="%s" compartment="%s" source_loc="%s" source_quote="%s"><mxCell value="%s" style="%s" vertex="1" parent="compartment-%s"><mxGeometry x="%.2f" y="%.2f" width="%.2f" height="%.2f" as="geometry"/></mxCell></object>' % (
            esc(n["id"]), plain(label), esc(kind), esc(n["compartment"]), plain(source.get("loc")), plain(source.get("quote")),
            plain(label), style, esc(n["compartment"]), x - 24, y - bands[n["compartment"]][0], w, h))
    emitted = 0
    for i, e in enumerate(edges):
        eid = e.get("id", "e%d" % i)
        kind = e.get("type", "unknown")
        source = e.get("source") or {}
        label = e.get("label") or e.get("tag") or TAG.get(kind, kind)
        cells.append('<object id="edge-%s" label="%s" kind="%s" evidence="%s" source_loc="%s" source_quote="%s"><mxCell style="%s" edge="1" parent="1" source="node-%s" target="node-%s"><mxGeometry relative="1" as="geometry"/></mxCell></object>' % (
            esc(eid), plain(label), esc(kind), esc(e.get("evidence", "strong")),
            plain(source.get("loc")), plain(source.get("quote")), style_for_edge(e),
            esc(e["from"]), esc(e["to"])))
        emitted += 1
    # Derived native legend: actual relation-specific style, never an unrelated image.
    y = 90
    lx = WIDTH + 28
    cells.append('<mxCell id="legend-title" value="Legend" style="text;html=1;fontSize=14;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="272" height="28" as="geometry"/></mxCell>' % (lx, y - 28))
    used = []
    for e in edges:
        if e.get("type", "unknown") not in used:
            used.append(e.get("type", "unknown"))
    for nt in sorted({n.get("type", "protein") for n in nodes}):
        if nt not in used:
            used.append(nt)
    for item in (g.get("legend") or {}).get("items", []):
        used.append("encoding:" + str(item.get("label", "")) + " = " + str(item.get("meaning", "")))
    for i, kind in enumerate(used):
        yy = y + 34 * i
        if kind.startswith("encoding:"):
            cells.append('<mxCell id="legend-encoding-%d" value="%s" style="text;html=1;fontSize=11;whiteSpace=wrap;" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="272" height="30" as="geometry"/></mxCell>' % (i, plain(kind[9:]), lx, yy))
        elif kind in EDGE_STYLE:
            sample = {"type": kind, "evidence": "strong"}
            cells.append('<mxCell id="legend-edge-%s" value="%s" style="%s" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="%d" y="%d" as="sourcePoint"/><mxPoint x="%d" y="%d" as="targetPoint"/></mxGeometry></mxCell>' % (
                esc(kind), plain(kind + (" (" + TAG[kind] + ")" if kind in TAG else "")), style_for_edge(sample), lx, yy + 12, lx + 50, yy + 12))
    for i, kind in enumerate(sorted({n.get("type", "protein") for n in nodes})):
        yy = y + 34 * (len(used) + i)
        fill, stroke = FILLS.get(kind, FILLS["protein"])
        cells.append('<mxCell id="legend-node-%s" value="%s" style="rounded=1;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;fontSize=11;%s" vertex="1" parent="1"><mxGeometry x="%d" y="%d" width="190" height="24" as="geometry"/></mxCell>' % (
            esc(kind), esc(kind), esc(fill), esc(stroke), "fontStyle=2;" if kind == "gene" else "", lx + 50, yy))
    # Visible native provenance, also attached structurally to each object.
    sources = [g["source_caption"]] if g.get("source_caption") else []
    for n in nodes + edges:
        src = n.get("source") or {}
        value = src.get("loc") or ("Quote: " + str(src.get("quote")) if src.get("quote") else None)
        if value and value not in sources:
            sources.append(value)
    native = "Source: " + " | ".join(sources) if sources else "Source not supplied; see uncertainty"
    cy = max(body_bottom + 32, y + 34 * (len(used) + len({n.get("type", "protein") for n in nodes})) + 40)
    cells.append('<mxCell id="native-citations" value="%s" style="text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=11;fontColor=#333333;" vertex="1" parent="1"><mxGeometry x="30" y="%d" width="%d" height="120" as="geometry"/></mxCell>' % (plain(native), cy, WIDTH + RAIL - 60))
    H = cy + 150
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<mxfile host="app.diagrams.net" agent="%s" version="24.7.5" type="device">'
           '<diagram id="figure" name="mechanism">'
           '<mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0">'
           '<root>%s</root></mxGraphModel></diagram></mxfile>') % (
           GEN, WIDTH + RAIL, H, "".join(cells))
    report = {"nodes": len(nodes), "edges": emitted, "relations": EDGE_STYLE,
              "missing_edge_ids": missing, "native_citations": native,
              "sources": "source_loc/source_quote on every object + visible native-citations"}
    return xml, report


def main():
    gp = sys.argv[1] if len(sys.argv) > 1 else "/app/work/graph.json"
    op = sys.argv[2] if len(sys.argv) > 2 else "/app/output/figure.drawio"
    try:
        with open(gp, encoding="utf-8") as f:
            graph = json.load(f)
        xml, report = build(graph)
        if report["missing_edge_ids"]:
            raise ValueError("unresolved edge references: %s" % report["missing_edge_ids"])
        os.makedirs(os.path.dirname(op) or ".", exist_ok=True)
        with open(op, "w", encoding="utf-8") as f:
            f.write(xml)
        with open(os.path.splitext(op)[0] + "_semantics.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(json.dumps({"ok": True, **report}, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
