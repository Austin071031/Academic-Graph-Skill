#!/usr/bin/env python3
"""Passive 'A is activated by B' must be drawn from B to A."""
import re
import sys
import xml.etree.ElementTree as ET

PAT = re.compile(r"(\S+) is (?:activated|inhibited|phosphorylated|repressed) by (\S+)", re.I)
ZH = re.compile(r"(\S+)被(\S+?)(?:激活|抑制|磷酸化)")
EDGE = re.compile(r"^(\S+): (\S+) --\[(\w+)\]--> (\S+)")

def local(tag):
    return tag.split("}")[-1]

def main():
    root = ET.parse(sys.argv[1]).getroot()
    seen = 0
    for title in root.iter():
        if local(title.tag) != "title":
            continue
        text = "".join(title.itertext())
        edge = EDGE.match(text)
        if not edge:
            continue
        patient = agent = None
        m = PAT.search(text)
        if m:
            patient, agent = m.group(1), m.group(2).rstrip(".")
        else:
            m = ZH.search(text)
            if m:
                patient, agent = m.group(1), m.group(2)
        if not patient:
            continue
        seen += 1
        frm, to = edge.group(2), edge.group(4)
        if frm != agent or to != patient:
            print("direction %s -> %s, quote patient %s agent %s" % (frm, to, patient, agent))
            sys.exit(1)
    if seen < 1:
        print("no passive edge")
        sys.exit(1)
    print("ok")
    sys.exit(0)

if __name__ == "__main__":
    main()
