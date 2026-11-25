#!/usr/bin/env python3
"""Fail when an arrow contradicts a directional quote naming both endpoint labels.

Exit 0 when every such arrow ends nearer the quote's destination. Exit 1 on a
contradiction. Exit 2 when inputs cannot be read. Edges without one clear
directional quote are skipped.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

MARKS = ("进入", "流入", "送入", "送至", "流向", "到", "通向", "→", "->")


def local(tag):
    return tag.split("}")[-1] if tag else ""


def directed(quote, src, dst):
    i, j = quote.find(src), quote.find(dst)
    if i < 0 or j <= i:
        return False
    return any(mark in quote[i + len(src):j] for mark in MARKS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--svg", required=True)
    ap.add_argument("--meta", required=True)
    a = ap.parse_args()
    try:
        ir = json.load(open(a.ir, encoding="utf-8"))
        meta = json.load(open(a.meta, encoding="utf-8"))
        root = ET.parse(a.svg).getroot()
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    labels = {e["id"]: e.get("label") or "" for e in ir.get("entities") or [] if e.get("id")}
    centers = {n["id"]: (n["x"], n["y"]) for n in meta.get("nodes") or [] if n.get("id")}
    paths = {}
    for el in root.iter():
        if local(el.tag) == "path" and el.get("id") and el.get("d"):
            nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", el.get("d"))]
            if len(nums) >= 4:
                paths[el.get("id")] = ((nums[0], nums[1]), (nums[-2], nums[-1]))
    bad = []
    checked = 0
    for c in ir.get("connections") or []:
        quote = ((c.get("source") or {}).get("quote") or "")
        la, lb = labels.get(c.get("from"), ""), labels.get(c.get("to"), "")
        if not quote or not la or not lb or la == lb or la in lb or lb in la:
            continue
        ab, ba = directed(quote, la, lb), directed(quote, lb, la)
        if ab == ba:
            continue
        src_id, dst_id = (c["from"], c["to"]) if ab else (c["to"], c["from"])
        checked += 1
        path = paths.get(c.get("id"))
        if path is None or src_id not in centers or dst_id not in centers:
            bad.append(c.get("id", "?") + ":missing")
            continue
        end = path[1]
        def dist(nid):
            x, y = centers[nid]
            return (end[0] - x) ** 2 + (end[1] - y) ** 2
        if dist(dst_id) >= dist(src_id):
            bad.append(c.get("id", "?"))
    if bad:
        print("FAIL quote direction " + ",".join(bad))
        return 1
    print(f"OK quote_edges={checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
