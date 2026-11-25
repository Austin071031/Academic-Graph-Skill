#!/usr/bin/env python3
"""Gene node text is italic. Protein node text is not."""
import sys
import xml.etree.ElementTree as ET

def local(tag):
    return tag.split("}")[-1]

def main():
    svg = sys.argv[1]
    root = ET.parse(svg).getroot()
    genes = proteins = 0
    for node in root.iter():
        if local(node.tag) != "g":
            continue
        kind = node.get("class") or ""
        if "node" not in kind:
            continue
        texts = [e for e in node if local(e.tag) == "text"]
        if "type-gene" in kind:
            genes += 1
            if not texts or any((e.get("font-style") or "") != "italic" for e in texts):
                print("gene text is not italic")
                sys.exit(1)
        if "type-protein" in kind:
            proteins += 1
            if any((e.get("font-style") or "") == "italic" for e in texts):
                print("protein text is italic")
                sys.exit(1)
    if genes < 1 or proteins < 1:
        print("need one gene and one protein")
        sys.exit(1)
    print("ok")
    sys.exit(0)

if __name__ == "__main__":
    main()
