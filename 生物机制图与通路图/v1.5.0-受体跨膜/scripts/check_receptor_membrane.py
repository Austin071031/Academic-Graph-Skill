#!/usr/bin/env python3
"""A receptor node is drawn on the membrane band."""
import sys
import xml.etree.ElementTree as ET

def local(tag):
    return tag.split("}")[-1]

def main():
    root = ET.parse(sys.argv[1]).getroot()
    bands = []
    for rect in root.iter():
        if local(rect.tag) == "rect" and (rect.get("fill") or "").lower() == "#caa64b":
            bands.append(float(rect.get("y")) + float(rect.get("height")) / 2)
    if not bands:
        print("no membrane band")
        sys.exit(1)
    membrane = sum(bands) / len(bands)
    found = 0
    for node in root.iter():
        if local(node.tag) != "g" or "type-receptor" not in (node.get("class") or ""):
            continue
        found += 1
        shape = next(e for e in node if local(e.tag) in ("rect", "ellipse"))
        if local(shape.tag) == "ellipse":
            center = float(shape.get("cy"))
        else:
            center = float(shape.get("y")) + float(shape.get("height")) / 2
        if abs(center - membrane) > 24:
            print("receptor center %.1f membrane %.1f" % (center, membrane))
            sys.exit(1)
    if found < 1:
        print("no receptor")
        sys.exit(1)
    print("ok")
    sys.exit(0)

if __name__ == "__main__":
    main()
