#!/usr/bin/env python3
"""lint_graph.py — structural lint of work/graph.json before rendering.

Checks schema shape, referential integrity (edges -> nodes, nodes -> compartments),
mandatory provenance (every node/edge needs source.quote or source.loc),
and naming hygiene (gene vs protein hints). Exits 1 on hard errors so the
agent MUST fix the graph instead of rendering garbage.
Usage: lint_graph.py work/graph.json
"""
import json, sys, re

NODE_TYPES = {"gene", "mrna", "protein", "receptor", "complex", "small_molecule",
              "ion", "cell", "cell_type", "compartment", "pathway", "phenotype"}
EDGE_TYPES = {"activation", "induction", "expression", "inhibition", "repression",
              "binding", "association", "dissociation", "phosphorylation",
              "dephosphorylation", "ubiquitination", "methylation", "cleavage",
              "translocation", "transport", "secretion", "input", "unknown"}
EVIDENCE = {"strong", "moderate", "weak", "inferred", "predicted"}

def lint(path):
    errors, warns = [], []
    try:
        g = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return ["graph.json unreadable: %s" % e], []
    if not isinstance(g, dict):
        return ["graph.json must be a JSON object"], []
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    comps = g.get("compartments", [])
    if not nodes:
        errors.append("nodes[] is empty — extract entities from the source first")
    ids = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict) or not n.get("id"):
            errors.append("nodes[%d] missing id" % i); continue
        if n["id"] in ids:
            errors.append("duplicate node id: %s" % n["id"])
        ids.add(n["id"])
        if not n.get("label"):
            errors.append("node %s missing label" % n["id"])
        t = n.get("type", "protein")
        if t not in NODE_TYPES:
            warns.append("node %s has non-standard type '%s'" % (n["id"], t))
        if not (n.get("source") or {}).get("quote") and not (n.get("source") or {}).get("loc"):
            warns.append("node %s lacks source quote/loc (traceability gap)" % n["id"])
        lab = n.get("label", "")
        if t in ("gene", "mrna") and re.search(r"\b(kinase|receptor|protein|enzyme)\b", lab, re.I):
            warns.append("node %s typed '%s' but label '%s' reads like a protein — check naming convention" % (n["id"], t, lab))
    comp_ids = {c.get("id") for c in comps if isinstance(c, dict)}
    for n in nodes:
        c = n.get("compartment")
        if c and comp_ids and c not in comp_ids and c != "membrane":
            warns.append("node %s references unknown compartment '%s'" % (n["id"], c))
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            errors.append("edges[%d] not an object" % i); continue
        for k in ("from", "to"):
            if e.get(k) not in ids:
                errors.append("edge %s references missing node '%s'" % (e.get("id", i), e.get(k)))
        t = e.get("type", "unknown")
        if t not in EDGE_TYPES:
            warns.append("edge %s has non-standard type '%s'" % (e.get("id", i), t))
        if not (e.get("source") or {}).get("quote") and not (e.get("source") or {}).get("loc"):
            warns.append("edge %s lacks source quote/loc (traceability gap)" % e.get("id", i))
        if e.get("evidence") and e["evidence"] not in EVIDENCE:
            warns.append("edge %s odd evidence '%s'" % (e.get("id", i), e["evidence"]))
    if not edges:
        warns.append("edges[] is empty — a mechanism figure needs at least one relation")
    return errors, warns

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/app/work/graph.json"
    errors, warns = lint(path)
    report = {"file": path, "errors": errors, "warnings": warns,
              "ok": not errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if not errors else 1)

if __name__ == "__main__":
    main()
