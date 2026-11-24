---
name: bio-mechanism-pathway-illustrator
description: 生物机制图与通路图工作流。当任务给出机制/通路材料（论文 PDF、图文摘要、实验描述或既有图稿）并要求绘制或编辑机制示意图、信号通路图、流程示意图或数据图表时使用，例如"根据本文 Fig.2 重绘机制图""把这段机制描述画成通路图""编辑提供的 SVG/drawio 图稿并重新导出"。本 Skill 把"读机制材料→抽取实体与关系（graph.json 结构化中间层）→确定性渲染分层可编辑 SVG/drawio→数据图表（带数值来源）→图例一致性核验→PNG/PDF 导出与 result.json 交付"固化为可复跑流程：实体类型（基因/蛋白/复合物/区室）不混用，相互作用（激活/抑制/结合/修饰/转运）用可区分箭头与端点，通路方向与区室/跨膜位置按层级布局，图例由同一编码表派生保证图例-图面-数据三者一致，每个节点与边携带材料出处可逐条回溯。仅适用于有真实材料支撑的图稿任务；不适用于无来源的科学臆测图、统计分析和论文写作。
---

# 生物机制图与通路图 Skill

把一份机制/通路材料变成**可逐条质疑、可编辑、可重新导出**的科研图稿。
核心思想：LLM 只做科学判断（实体是什么、关系是什么、方向向哪、数值多少），
**所有几何、箭头语义、图例和导出让确定性脚本完成**——脚本不吃语义亏，
LLM 不犯绘图错，二者用同一个 `graph.json` 中间层衔接。


## 本变体优化重点：图例填色与节点数据编码一致（结果正确性 15 分）

节点写了 `fill`（表达量、显著性等数据编码）时，图例色块使用该填色。渲染后必跑 `python3 scripts/legend_audit.py /app/work/graph.json /app/output/figure.svg /app/output`，退出码为 0 才能交付。

在步骤 3 与 4 之间**必跑**：
```
python3 scripts/provenance_ledger.py /app/work/graph.json /app/output
```
它生成 `provenance_ledger.md`：图上每个节点、每条边一行——类型、区室、证据强度、
来源位置、原文摘录。任何元素缺出处时脚本退出码为 1，**必须补齐或显式声明后才能继续**。
评审可以随机抽一行回溯到材料原文，这条链就是"可逐条质疑"的证据。result.json 的
sources 字段与 ledger 同源（都来自 graph.json 的 source 字段），不得二次手工编辑造成分叉。

## 何时触发
输入含机制/通路/信号传导/调控关系描述，或要求绘制、重绘、编辑机制图、通路图、
示意图、流程图，或要求把论文图表按真实数据重画（figure03 类）。纯统计分析、
实验设计、论文写作不触发。

## 运行环境
- Python 3（脚本全部标准库实现，零 pip 依赖）。
- 渲染预览优先 cairosvg，缺失时自动降级 rsvg-convert / inkscape / resvg（见 render_preview.py）。
- PDF 文本提取优先 pdftotext，缺失降级 PyMuPDF（extract_pdf.py）。
- 若环境提供 OCR / 字体发现等附加资源，按需使用并在 run_log.md 记录。

## 六步流水线（每步都有落盘产物，失败可定位可恢复）

### 0. 预检（1 次模型调用即可，尽量省）
```
python3 scripts/inspect_case.py /input /app/work     # → work/brief.json
```
读 `brief.json` 与 `/input/task.md`：确认 case_id、output_contract 必需字段、
材料清单、任务是新画还是**source-preserving 改图**。把任务一句话写进
`work/run_state.json` 的 `change_log[0]`。

### 1. 抽取材料
```
python3 scripts/extract_pdf.py /input /app/work      # → work/source_text/*.txt
```
Agent 阅读抽取文本（分段读，别一次吞全文），只提取**有出处**的内容。
若 task.md 直接内嵌机制描述，则以 task.md 为准并记录来源为 task.md。

### 2. 结构化（核心科学判断，全部在这步完成）
按 `references/extraction_schema.md` 写 `work/graph.json`（实体/关系/区室/数据编码）。
同时若是图表类任务，写 `work/chart.json`（每个 series 必须带 source，否则渲染拒绝）。
先自查再渲染：
```
python3 scripts/lint_graph.py /app/work/graph.json
```
lint 的 HARD 错误必须修复；WARN（如缺 source quote）原则上也修——**可核验性是硬指标**。

### 3. 渲染（确定性，不改语义）
```
python3 scripts/build_svg.py /app/work/graph.json /app/output/figure.svg
python3 scripts/legend_audit.py /app/work/graph.json /app/output/figure.svg /app/output
python3 scripts/build_drawio.py /app/work/graph.json /app/output/figure.drawio
python3 scripts/build_chart.py /app/work/chart.json /app/output/chart.svg   # 图表类案例
```
改图任务：解析输入图稿，把要改的标签/样式只改在 SVG/drawio 对应节点上（保留原坐标与结构），
change_log 记录改动前后对照。

### 4. 导出预览
```
python3 scripts/render_preview.py /app/output/figure.svg /app/output/figure.png /app/output/figure.pdf
```
渲染器全缺时如实记录；SVG 矢量本体仍交付。

### 5. 核验与交付
```
python3 scripts/validate.py /app/work/graph.json /app/output /app/work/brief.json
# 把 status/sources/uncertainty/change_log 写入 work/run_state.json（JSON，见 references/output_contract.md）
python3 scripts/make_result.py /app/work /app/output
```
HARD 失败 → 修复后重跑（最多 2 轮；仍失败则在 run_state.json 把 status 置 partial 并说明）。
另写 `/app/output/run_log.md`：步骤、判断理由、预算、异常与处置。

## 预算纪律（64 次模型调用 / 900s / 16k tokens）
- 步骤 0–2 控制在 ≤20 次调用：先读 task.md，再按章节定位读 PDF，不做全文摘要。
- 步骤 3–5 不消耗模型调用（纯脚本）。
- 剩余预算用于：1 轮核验修复 + 1 轮可读性微调。
- 过半预算时立即走最小路径：lint→build_svg→render→make_result，确保有诚实 partial 落盘。

## 异常处理
见 `references/failure_playbook.md`（方向缺失、命名歧义、数据矛盾、无文本层 PDF、
渲染器缺失、元素过多、预算不足、改图任务等 10 种情况的识别与处置）。总原则：
**识别 → 按表处置 → 写进 uncertainty/change_log**，不静默丢弃信息。

## 完成定义（对照评分维度自检）
- [ ] 任务完成度：figure.svg/drawio + 预览 + result.json 全在 /app/output，result.json 含 output_contract 全部字段 + case_id
- [ ] 结果正确性：基因/蛋白/复合物/区室类型无误用；激活/抑制/结合/修饰/转运箭头可区分；方向与材料一致；膜蛋白跨膜、核内元素在核区
- [ ] 结果完整性：任务点名的实体、分支、反馈环、图例项、导出格式全部覆盖
- [ ] 可核验性：每个节点/边有 source；图例由编码表派生；run_log 可追溯
- [ ] 增益与创新：相比"随手画一张 SVG"，本流程把语义判断与几何渲染分离、图例自动一致、来源强制绑定——在 result.json 的 sources 里直接呈现这条链
- [ ] 生态：README.md（本 Skill 根）写清用法/依赖/限制；examples/ 提供最小示例（标明为示例）

## 资源清单（相对本文件所在目录，安装后为 /skills/weekly-skill）
| 路径 | 作用 |
|---|---|
| scripts/inspect_case.py | 预检 case.json/task.md → brief.json |
| scripts/extract_pdf.py | PDF → 文本（pdftotext/PyMuPDF 两级降级） |
| scripts/lint_graph.py | graph.json 结构/引用/出处 lint |
| scripts/build_svg.py | graph.json → 分层可编辑 SVG（区室/节点/边/图例四组 + metadata） |
| scripts/build_drawio.py | graph.json → draw.io 同名分层图稿 |
| scripts/build_chart.py | chart.json → 带数值来源的 SVG + CSV |
| scripts/render_preview.py | SVG → PNG/PDF 四级渲染降级 |
| scripts/validate.py | 交付前核验（XML/出处/图例/合同字段/预览） |
| scripts/make_result.py | 组装 result.json（拒绝在硬失败时声称 complete） |
| references/extraction_schema.md | graph.json/chart.json 模式与命名纪律 |
| references/layout_templates.md | 区室/跨膜/方向/可读性布局规则 |
| references/output_contract.md | 交付清单与 result.json 五要素 |
| references/failure_playbook.md | 10 类异常处置 |
| examples/minimal_example.md | 最小调用示例（示意，非案例答案） |
