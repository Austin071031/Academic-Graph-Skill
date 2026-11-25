# bio-mechanism-pathway-illustrator · v2.0.3 双源语义

父版：v1.0.0（attempt 85718，73/100）。本版唯一机制增量：draw.io 的原生完整导出，
使两个可编辑源在类型、方向、区室、图例与来源上一致，不改图表或输出合同。

## 调用与依赖
Python ≥3.8，标准库。
```bash
python3 scripts/build_svg.py /app/work/graph.json /app/output/figure.svg
python3 scripts/build_drawio.py /app/work/graph.json /app/output/figure.drawio
```
产物含真实 mxfile/mxGraphModel/mxCell/object，非 HTML 位图或图片包装。

## 语义约定
inhibition/repression 使用原生 `bar` 端点；activation 为实线箭头；
binding/association 为无箭头实线；dissociation 为无箭头虚线；磷酸化、泛素化、
甲基化、切割、转运等保留各自颜色、线型、标注。节点与边含 source_loc/quote，
标题、图例和可见 native-citations 均从同一 graph 派生。`figure_semantics.json`
保存关系样式、来源和实际输出数量；悬空引用返回失败。

## 限制
不在本地声称已用在线 draw.io 审核视觉呈现，只验收原生 XML、容器、相对坐标及
语义映射。其它输入输出约定与 `examples/minimal_example.md` 一致，不内置案例答案。
