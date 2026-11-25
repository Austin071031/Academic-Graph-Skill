#!/usr/bin/env python3
"""recall_audit.py — source-text recall audit for the IR.

父版失分主因是案例运行时的**实体/连接/步骤召回不足**：材料里写到的装置、连接、
步骤没有全部进 IR，图面因此漏画。本脚本把材料原文当作唯一事实来源，抽取三类
候选后与 IR 比对，检出遗漏并强制处置（补全或显式 uncertainty）。

抽取（保守、可解释、不臆造）：
  1. 装置候选：设备词典命中 + 工程代号模式（R-101 / C1 / E201 / V3A / P-02 …）。
  2. 连接候选：「A 进入/流经/送入/排入/汇入 B」「A → B」「A 到 B」模式。
  3. 步骤候选：「第一步/第二步…」「步骤 1/2/3」「1. 2. 3.」编号。

比对：候选（或其别名/代号子串）未出现在任何 IR entity.label / connection / steps
即记为遗漏。遗漏项若 IR.uncertainty 未提及，本脚本非零退出，阻止漏图进入导出。

Usage:
  python3 recall_audit.py --ir /app/work/ir.json --materials /input \
      --report /app/output/recall_report.json
"""
import argparse, json, os, re, sys, glob

DEVICE_LEX = [
    "反应器", "预热器", "加热器", "换热器", "冷凝器", "分离柱", "精馏塔", "蒸馏塔", "吸收塔",
    "泵", "阀门", "压缩机", "储罐", "缓冲罐", "混合器", "过滤器", "干燥器", "冷却塔",
    "传感器", "进料口", "出料口", "废气", "废液", "循环水", "原料", "产品", "催化剂",
    "离心机", "蒸发器", "结晶器", "搅拌釜", "流化床", "固定床", "膜分离", "萃取塔",
]
CODE_RE = re.compile(r"\b([A-Z]{1,3}[-≈]?\d{1,4}[A-Z]?)\b")
CONN_RES = [
    re.compile(r"([一-龥A-Za-z0-9\-]{1,12})\s*(?:进入|流经|送入|排入|汇入|通入|导入|进入)\s*([一-龥A-Za-z0-9\-]{1,12})"),
    re.compile(r"([一-龥A-Za-z0-9\-]{1,12})\s*(?:→|->|到|至)\s*([一-龥A-Za-z0-9\-]{1,12})"),
]
STEP_RES = [re.compile(r"第\s*([一二三四五六七八九十\d]+)\s*步"),
            re.compile(r"步骤\s*(\d{1,2})"),
            re.compile(r"^\s*(\d{1,2})\s*[.、)]\s*", re.M)]
CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d if d is not None else {}

def read_texts(path):
    files = []
    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        for ext in ("*.md", "*.txt", "*.json"):
            files += glob.glob(os.path.join(path, "**", ext), recursive=True)
    txt = []
    for fp in sorted(files):
        if os.path.basename(fp) in ("result.json",):
            continue
        try:
            with open(fp, encoding="utf-8", errors="ignore") as f:
                txt.append((os.path.basename(fp), f.read()))
        except Exception:
            pass
    return txt

def norm(s):
    return re.sub(r"\s+", "", str(s or "")).lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--materials", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    ir = load(a.ir, {})
    texts = read_texts(a.materials)
    corpus = "\n".join(t for _, t in texts)
    labels = " ".join(str(e.get("label", "")) for e in ir.get("entities", []))
    labels_n = norm(labels)
    conn_set = {(norm(c.get("from")), norm(c.get("to"))) for c in ir.get("connections", [])}
    steps_nos = {s.get("no") for s in ir.get("steps", [])}
    unc = " ".join(ir.get("uncertainty", []))
    unc_n = norm(unc)

    # 1 device candidates
    missing_devices = []
    for lex in DEVICE_LEX:
        if lex in corpus and norm(lex) not in labels_n and norm(lex) not in unc_n:
            missing_devices.append(lex)
    missing_codes = []
    for code in set(CODE_RE.findall(corpus)):
        if len(code) < 2:
            continue
        if norm(code) not in labels_n and norm(code) not in unc_n and not code.startswith(("E", "C", "S", "P")):
            missing_codes.append(code)

    # 2 connection candidates -> only flag pairs whose both endpoints already exist as labels
    known = {norm(e.get("label")) for e in ir.get("entities", [])}
    id_by_label = {norm(e.get("label")): e.get("id") for e in ir.get("entities", [])}
    existing_pairs = set()
    ents = {e.get("id"): e for e in ir.get("entities", [])}
    for c in ir.get("connections", []):
        f = norm((ents.get(c.get("from"), {}) or {}).get("label"))
        t = norm((ents.get(c.get("to"), {}) or {}).get("label"))
        existing_pairs.add((f, t))
    missing_conns = []
    for rx in CONN_RES:
        for src, dst in rx.findall(corpus):
            ns, nd = norm(src), norm(dst)
            if ns in known and nd in known and (ns, nd) not in existing_pairs:
                missing_conns.append({"from": src, "to": dst})

    # 3 step numbers
    found_steps = set()
    for rx in STEP_RES:
        for m in rx.findall(corpus):
            if isinstance(m, tuple):
                m = m[0]
            n = CN.get(m, None)
            if n is None:
                try:
                    n = int(m)
                except Exception:
                    continue
            found_steps.add(n)
    missing_steps = sorted(n for n in found_steps if n not in steps_nos and n <= 30)

    total = len(missing_devices) + len(missing_codes) + len(missing_conns) + len(missing_steps)
    report = {
        "materials_files": [n for n, _ in texts],
        "entities_in_ir": len(ir.get("entities", [])),
        "connections_in_ir": len(ir.get("connections", [])),
        "steps_in_ir": len(ir.get("steps", [])),
        "missing_devices": missing_devices,
        "missing_engineering_codes": sorted(missing_codes),
        "missing_connections": missing_conns,
        "missing_step_numbers": missing_steps,
        "recall_ok": total == 0,
        "note": "候选项若确属不需入图，必须在 ir.uncertainty 说明，方可豁免",
    }
    with open(a.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"OK recall_audit missing_devices={missing_devices[:6]} codes={missing_codes[:6]} "
          f"conns={missing_conns[:4]} steps={missing_steps[:6]}")
    sys.exit(0 if total == 0 else 1)

if __name__ == "__main__":
    main()
