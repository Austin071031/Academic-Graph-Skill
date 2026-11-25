# 已知限制与失败清单（LIMITATIONS / failure log）

1. **不做科学判断**：不评估实验方案合理性、不换算单位以外的数值、不补全材料未给出的参数。
2. **布局目标**：自动布局（Sugiyama 最长路径 + 重心排序）面向结构清晰，非美术排版；>20 节点的稠密图建议改用 grid 布局人工指定行列。
3. **glyph 覆盖**：assets/glyphs/ 提供 11 种常用装置图元（泵、阀、釜、罐、塔、换热器、冷凝器、加热器、传感器、进出口）；材料中装置形态超出词表时退化为圆角矩形 + 原名标注，不臆造图形。
4. **chart 模式**：仅支持 line/bar 两种系列与线性坐标轴；对数轴、双轴、误差带尚未支持（需要时先在 IR uncertainty 中声明）。
5. **导出链**：真矢量 PDF 依赖 rsvg/inkscape/cairosvg；仅有 chromium 时 PDF 不可得，matplotlib 回退从 meta.json 重渲染（非 SVG 栅格），此情形 export_report.json 的 note 字段会显式说明。
6. **字体**：SVG 依赖查看器端字体回退；PNG/PDF 导出时 fc-list 探测中文字体，若环境无任何 CJK 字体，导出报告中 cjk_fonts_found 为空且自检 font_embedding 不通过——此时不伪造导出成功状态。
7. **历史失败与对策**（真实沉淀）：
   - 长中文标签溢出 ⇒ pg_check text_overflow 检出后缩短 label（保留原名于 sources.md）或增大节点宽。
   - 工艺描述歧义 ⇒ 最保守语义抽取 + confidence=inferred + changes.md 记录。
   - 材料只有图片无文本层 ⇒ 用平台 ocr-tool 后仍须人工核对数字，核对结论写入 uncertainty。
