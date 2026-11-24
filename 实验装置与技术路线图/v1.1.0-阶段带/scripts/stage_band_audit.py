#!/usr/bin/env python3
"""Check that each tech-route stage band contains its actor centers.

Exit 0 when every actor center lies inside its own stage rectangle.
Exit 1 when a band is missing or an actor center is outside it.
Exit 2 when the inputs cannot be read.
Diagrams with no staged steps pass.
"""
import argparse, json, sys, xml.etree.ElementTree as ET

NS = {"svg": "http://www.w3.org/2000/svg"}


def local(tag):
    return tag.split("}")[-1] if tag else ""


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def stage_actors(ir):
    order, actors = [], {}
    for step in ir.get("steps") or []:
        name, actor = step.get("stage"), step.get("actor")
        if not name or not actor:
            continue
        if name not in actors:
            order.append(name)
            actors[name] = []
        if actor not in actors[name]:
            actors[name].append(actor)
    return order, actors


def stage_rects(svg_path):
    root = ET.parse(svg_path).getroot()
    layer = None
    for el in root.iter():
        if local(el.tag) == "g" and el.get("id") == "layer-stages":
            layer = el
            break
    rects = []
    if layer is None:
        return rects
    for el in layer:
        if local(el.tag) != "rect":
            continue
        rects.append({
            "name": el.get("data-stage"),
            "x": float(el.get("x")),
            "y": float(el.get("y")),
            "w": float(el.get("width")),
            "h": float(el.get("height")),
        })
    return rects


def inside(rect, x, y):
    return rect["x"] <= x <= rect["x"] + rect["w"] and rect["y"] <= y <= rect["y"] + rect["h"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--svg", required=True)
    ap.add_argument("--meta", required=True)
    a = ap.parse_args()
    try:
        ir = load(a.ir)
        meta = load(a.meta)
        rects = stage_rects(a.svg)
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    order, actors = stage_actors(ir)
    if not order:
        print("OK no staged steps")
        return 0
    if len(rects) != len(order):
        print(f"FAIL stage rects={len(rects)} stages={len(order)}")
        return 1
    named = all(r["name"] for r in rects)
    if named:
        by_name = {r["name"]: r for r in rects}
        if set(by_name) != set(order):
            print(f"FAIL stage names rect={sorted(by_name)} ir={order}")
            return 1
    else:
        by_name = {name: rect for name, rect in zip(order, rects)}
    centers = {n["id"]: (n["x"], n["y"]) for n in meta.get("nodes") or [] if n.get("id")}
    missing = []
    for name in order:
        rect = by_name[name]
        for actor in actors[name]:
            if actor not in centers or not inside(rect, *centers[actor]):
                missing.append(f"{name}:{actor}")
    if missing:
        print("FAIL actors outside their stage band: " + ",".join(missing))
        return 1
    print(f"OK stages={len(order)} actors_inside={sum(len(v) for v in actors.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
