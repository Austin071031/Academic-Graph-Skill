# bio-mechanism-pathway-illustrator · v2.0.1 数值图表

父版：v1.0.0（attempt 85718，73/100）。本版唯一机制增量：真实数据到图元、图例、
来源与导出数组的一致性，不改输出合同、机制布局或 draw.io 编辑器。

## 调用与依赖
Python ≥3.8。SVG/CSV 必需路径只用标准库；PNG 使用已提供 matplotlib/numpy，
并在 `chart_render_report.json` 记录实际后端；没有 PNG 后端不得用机制父图替代。
```bash
python3 scripts/build_chart.py /app/work/chart.json /app/output/chart.svg
```
最小 graph 与完整流水线见 `examples/minimal_example.md`；材料/数字均须来自输入。

## 输入与输出
沿用 `chart.json`：kind/categories/series/x_label/y_label/source。另支持 points、
x_values/categories 分别横轴。输出 chart.svg、chart.png（后端可用）、chart_data.csv、
chart_render_report.json。数值 x 线性且升序，类别 x 保序，null/NA 省略且折线分段；
散点不连线，图例按系列 ID 绑定，来源显示为 SVG 文本。

## 限制
不把示意数值当正式案例；不补造横轴或数值。缺失输入与无出处序列返回失败，
没有 matplotlib 时仍交付真实 SVG/CSV 并标注 PNG 缺口。
