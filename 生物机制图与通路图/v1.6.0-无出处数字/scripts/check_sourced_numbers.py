#!/usr/bin/env python3
"""Every number in node text appears in that node's source quote, and sourced numbers stay."""
import re
import sys
import xml.etree.ElementTree as ET

NUM = re.compile(r"\d+(?:\.\d+)?")

def local(tag):
    return tag.split("}")[-1]

def main():
    root = ET.parse(sys.argv[1]).getroot()
    checked = 0
    for node in root.iter():
        if local(node.tag) != "g" or "node" not in (node.get("class") or ""):
            continue
        title = ""
        visible = []
        for child in node:
            if local(child.tag) == "title":
                title = "".join(child.itertext())
            elif local(child.tag) == "text":
                visible.append("".join(child.itertext()))
        if "source:" not in title or " [" not in title:
            continue
        label = title.split(" [", 1)[0]
        quote = title.split("source:", 1)[1]
        shown = " ".join(visible)
        checked += 1
        for num in NUM.findall(shown):
            if num not in quote:
                print("unsourced number %s in %s" % (num, shown))
                sys.exit(1)
        for num in NUM.findall(label):
            if num in quote and num not in shown:
                print("sourced number %s missing from figure" % num)
                sys.exit(1)
    if checked < 1:
        print("no nodes")
        sys.exit(1)
    print("ok")
    sys.exit(0)

if __name__ == "__main__":
    main()
