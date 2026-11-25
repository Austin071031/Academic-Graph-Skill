#!/usr/bin/env python3
"""Fail when the legend rectangle intersects a node box or covers entity text.

Exit 0 when every node box is clear of the legend and entity text baselines
sit above the legend top. Exit 1 on an overlap. Exit 2 when inputs cannot be read.
A figure with no legend passes.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET


def local(tag):
    return tag.split("}")[-1] if tag else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", required=True)
    ap.add_argument("--meta", required=True)
    a = ap.parse_args()
    try:
        meta = json.load(open(a.meta, encoding="utf-8"))
        root = ET.parse(a.svg).getroot()
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    legend = None
    for el in root.iter():
        if local(el.tag) == "g" and el.get("id") == "layer-legend":
            for child in el:
                if local(child.tag) == "rect":
                    legend = (float(child.get("x")), float(child.get("y")),
                              float(child.get("width")), float(child.get("height")))
                    break
            break
    if legend is None:
        print("OK no legend")
        return 0
    lx, ly, lw, lh = legend
    hits = []
    for n in meta.get("nodes") or []:
        nx, ny = n["x"] - n["w"] / 2, n["y"] - n["h"] / 2
        if not (nx + n["w"] <= lx or lx + lw <= nx or ny + n["h"] <= ly or ly + lh <= ny):
            hits.append(n["id"] + ":box")
    for el in root.iter():
        if local(el.tag) != "g" or not el.get("id") or el.get("id").startswith("layer-"):
            continue
        for child in el.iter():
            if local(child.tag) == "text" and child.get("y"):
                if float(child.get("y")) >= ly:
                    hits.append(el.get("id") + ":text")
                    break
    if hits:
        print("FAIL legend covers " + ",".join(hits))
        return 1
    print(f"OK legend_clears nodes={len(meta.get('nodes') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
