#!/usr/bin/env python3
"""topology.py — detect pathway topology and emit layout hints (efficiency path).

Classifies the graph as linear / branching / feedback-loop / multi-compartment and
writes work/layout_hints.json. With --apply it also writes node x/y overrides back
into a copy of graph.json for the renderer (cleaner auto-layout, fewer model calls
spent on manual coordinates).
Usage: topology.py work/graph.json [--apply]
"""
import json, sys

ORDER = {"extracellular": 0, "membrane": 1, "cytoplasm": 2, "cytosol": 2, "nucleus": 3}

def layer_of(n, default=2):
    return ORDER.get((n.get("compartment") or "").lower(), default)

def main():
    gp = sys.argv[1] if len(sys.argv) > 1 else "/app/work/graph.json"
    apply_hints = "--apply" in sys.argv
    g = json.load(open(gp, encoding="utf-8"))
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    edges = g.get("edges", [])
    layers = {nid: layer_of(n) for nid, n in nodes.items()}
    feedback = [e for e in edges
                if e.get("from") in layers and e.get("to") in layers
                and layers[e["to"]] < layers[e["from"]]]
    indeg, outdeg = {}, {}
    for e in edges:
        outdeg[e.get("from")] = outdeg.get(e.get("from"), 0) + 1
        indeg[e.get("to")] = indeg.get(e.get("to"), 0) + 1
    branch_nodes = [k for k, v in outdeg.items() if v >= 2]
    merge_nodes = [k for k, v in indeg.items() if v >= 2]
    comps = {n.get("compartment") for n in nodes.values()}
    kinds = []
    if feedback:
        kinds.append("feedback-loop")
    if branch_nodes:
        kinds.append("branching")
    if len(comps - {None}) >= 3:
        kinds.append("multi-compartment")
    if not kinds and edges:
        kinds.append("linear")
    hints = {"topology": kinds or ["single-node"],
             "feedback_edges": [e.get("id") for e in feedback],
             "branch_nodes": branch_nodes, "merge_nodes": merge_nodes,
             "compartments": sorted(c for c in comps if c),
             "advice": []}
    if feedback:
        hints["advice"].append("feedback edges (%s): keep evidence weak/inferred + label 'feedback'" %
                               ", ".join(hints["feedback_edges"]))
    if branch_nodes:
        hints["advice"].append("branch at %s: place branch children side-by-side downstream" % ", ".join(branch_nodes))
    if len(nodes) > 14:
        hints["advice"].append(">14 nodes: simplify to the task's named entities; keep full set in graph.json")
    if apply_hints and edges:
        # spread same-layer nodes evenly by chain order to reduce overlap
        by_layer = {}
        for nid, l in layers.items():
            by_layer.setdefault(l, []).append(nid)
        for l, nids in by_layer.items():
            for i, nid in enumerate(sorted(nids)):
                nodes[nid]["_x"] = i
        g["_layout_order"] = {nid: n.get("_x", 0) for nid, n in nodes.items()}
        with open(gp, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, indent=2)
    out = gp.rsplit("/", 1)[0] + "/layout_hints.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(hints, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "hints": out, "topology": hints["topology"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
