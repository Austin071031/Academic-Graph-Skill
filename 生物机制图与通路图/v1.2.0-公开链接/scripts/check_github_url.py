#!/usr/bin/env python3
"""Exit 0 when GITHUB_URL.txt line 1 is a public GitHub URL."""
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
path = root / "GITHUB_URL.txt"
if not path.is_file():
    print("missing GITHUB_URL.txt")
    sys.exit(1)
line = path.read_text(encoding="utf-8").splitlines()[0].strip()
if line.startswith("https://github.com/") and len(line) > len("https://github.com/"):
    print("ok")
    sys.exit(0)
print("url is not a GitHub link")
sys.exit(1)
