# 最小调用示例（示意输出，非正式案例结果）

输入（示意）：
```json
// /input/case.json
{"case_id": "demo-01",
 "output_contract": {"editable_source": "file", "preview": "file", "summary": "str"}}
```
```markdown
// /input/task.md
Draw the mechanism: ligand L binds receptor R on the cell membrane; R activates
kinase K in the cytoplasm; K phosphorylates transcription factor T, which
translocates into the nucleus and induces gene G expression. (illustrative text)
```

调用：
```bash
python3 scripts/inspect_case.py /input /app/work
python3 scripts/extract_pdf.py /input /app/work        # 无 PDF 时跳过
# agent 据材料写 /app/work/graph.json（内容见下），然后：
python3 scripts/lint_graph.py /app/work/graph.json
python3 scripts/build_svg.py /app/work/graph.json /app/output/figure.svg
python3 scripts/build_drawio.py /app/work/graph.json /app/output/figure.drawio
python3 scripts/render_preview.py /app/output/figure.svg /app/output/figure.png /app/output/figure.pdf
python3 scripts/validate.py /app/work/graph.json /app/output /app/work/brief.json
python3 scripts/make_result.py /app/work /app/output
```

graph.json（节选，示意）：
```json
{
  "title": "L-R-K-T-G signaling (illustrative)",
  "source_caption": "demo material only — not a real case result",
  "compartments": [
    {"id": "extracellular", "label": "Extracellular"},
    {"id": "membrane", "label": "Cell membrane"},
    {"id": "cytoplasm", "label": "Cytoplasm"},
    {"id": "nucleus", "label": "Nucleus"}
  ],
  "nodes": [
    {"id": "L", "label": "L", "type": "small_molecule", "compartment": "extracellular",
     "source": {"loc": "task.md", "quote": "ligand L"}},
    {"id": "R", "label": "R", "type": "receptor", "compartment": "membrane",
     "source": {"loc": "task.md", "quote": "receptor R on the cell membrane"}},
    {"id": "K", "label": "K", "type": "protein", "compartment": "cytoplasm",
     "source": {"loc": "task.md", "quote": "kinase K in the cytoplasm"}},
    {"id": "T", "label": "T (p)", "type": "protein", "compartment": "nucleus",
     "synonyms": "T", "source": {"loc": "task.md", "quote": "translocates into the nucleus"}},
    {"id": "G", "label": "G", "type": "gene", "compartment": "nucleus",
     "source": {"loc": "task.md", "quote": "induces gene G expression"}}
  ],
  "edges": [
    {"id": "e1", "from": "L", "to": "R", "type": "binding", "evidence": "strong",
     "source": {"loc": "task.md", "quote": "binds receptor R"}},
    {"id": "e2", "from": "R", "to": "K", "type": "activation", "evidence": "strong",
     "source": {"loc": "task.md", "quote": "R activates kinase K"}},
    {"id": "e3", "from": "K", "to": "T", "type": "phosphorylation", "evidence": "strong",
     "label": "phospho.", "source": {"loc": "task.md", "quote": "K phosphorylates T"}},
    {"id": "e4", "from": "T", "to": "T", "type": "translocation", "evidence": "strong",
     "label": "to nucleus", "source": {"loc": "task.md", "quote": "translocates into the nucleus"}}
  ],
  "legend": {"items": [{"label": "arrowhead", "meaning": "activation"},
                        {"label": "T-bar", "meaning": "inhibition"},
                        {"label": "no head", "meaning": "binding"}]}
}
```

示意输出：`/app/output/figure.svg`（分层、含图例与 metadata）、`figure.drawio`、
`figure.png`、`figure.pdf`、`result.json`（status=complete，sources 逐条指向 task.md）。
真实案例必须替换为材料实体的出处（PDF 页/图 + 引文）。
