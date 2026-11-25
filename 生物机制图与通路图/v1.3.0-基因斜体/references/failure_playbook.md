# 异常处理手册（识别 → 处置 → 记录）

每条处置都要写进 result.json 的 uncertainty 或 change_log。

| 情况 | 识别 | 处置 |
|---|---|---|
| 材料缺方向信息 | 句子无主从关系（"X and Y are involved in"） | edge.type=unknown + evidence=weak，label 标 "direction unclear"，uncertainty 声明 |
| 同名基因/蛋白歧义 | 一句中 "X expression" 与 "X kinase activity" 并存 | 拆两节点（gene + protein），synonyms 互注 |
| 输入数据与图示矛盾 | 数值表与图注不一致 | 以数据表为准重算编码；图注矛盾写入 uncertainty，不静默取舍 |
| 实体旧名/同义名 | 材料用旧名 | label 用材料原文，synonyms 列现行名，ledger 注明 |
| PDF 无文本层 | extract_pdf.py method=null | 用 OCR 资源；OCR 不可用时只交付基于 task.md 的骨架并在 status=partial 说明 |
| 渲染器全缺 | render_preview.py 报 errors | 记录 render_report.json；SVG 本身仍是交付物（矢量，可直接打开），status 如实 |
| 图面元素过多 | 节点 >14 或边 >20 | 按主干简化 + graph.json 保留全量；或拆 panel A/B |
| 输出合同字段不明 | case.json 无 output_contract | 以 task.md 为准；result.json 仍含 case_id/status/sources/uncertainty/change_log 五要素 |
| 超时/预算紧 | 已用 >40 次模型调用或 >600s | 立即走最小路径：lint→build_svg→render→make_result，跳过 chart/drawio/第二遍润色 |
| 案例要求改图而非新画 | task.md 提到 "edit/update/redraw provided figure" | 先解析输入图（SVG/drawio/PNG），保留原结构做 source-preserving edit：只改标签/样式，不重排坐标；改后重新导出预览并写 change_log（改前/改后对照） |
