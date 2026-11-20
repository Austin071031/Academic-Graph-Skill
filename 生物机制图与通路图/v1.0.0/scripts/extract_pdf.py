#!/usr/bin/env python3
"""extract_pdf.py — extract text from PDF materials into work/source_text/.

Cascade: pdftotext (poppler) -> PyMuPDF (fitz) -> honest failure note.
Usage: extract_pdf.py /input /app/work
Writes one .txt per PDF plus an index.json with page counts.
"""
import json, os, subprocess, sys

def extract_with_pdftotext(pdf, out):
    r = subprocess.run(["pdftotext", "-layout", pdf, out],
                       capture_output=True, timeout=120)
    return r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0

def extract_with_fitz(pdf, out):
    try:
        import fitz  # PyMuPDF
    except Exception:
        return False
    try:
        doc = fitz.open(pdf)
        parts = []
        for i, page in enumerate(doc):
            parts.append("\n===== [page %d] =====\n" % (i + 1) + page.get_text())
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))
        return True
    except Exception:
        return False

def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else "/input"
    work = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
    outdir = os.path.join(work, "source_text")
    os.makedirs(outdir, exist_ok=True)
    index = []
    for root, _dirs, files in os.walk(inp):
        for name in sorted(files):
            if not name.lower().endswith(".pdf"):
                continue
            pdf = os.path.join(root, name)
            stem = os.path.splitext(name)[0].replace(" ", "_")
            out = os.path.join(outdir, stem + ".txt")
            method = None
            if extract_with_pdftotext(pdf, out):
                method = "pdftotext"
            elif extract_with_fitz(pdf, out):
                method = "pymupdf"
            rec = {"pdf": pdf, "text": out if method else None, "method": method}
            if method:
                rec["chars"] = os.path.getsize(out)
            else:
                rec["error"] = "no working PDF text extractor; try OCR resources if available"
            index.append(rec)
    idx_path = os.path.join(outdir, "index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "extracted": sum(1 for r in index if r.get("method")),
                      "failed": sum(1 for r in index if not r.get("method")),
                      "index": idx_path}, ensure_ascii=False))

if __name__ == "__main__":
    main()
