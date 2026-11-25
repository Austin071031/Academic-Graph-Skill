# bio-mechanism-pathway-illustrator · v2.0.2 原生引用布局

父版：v1.0.0（attempt 85718，73/100）。本版唯一机制增量：真实结构归一化、
非重叠布局、冲突绕行和原生可见出处，不合并数据图表/合同修改。

## 调用与依赖
Python ≥3.8，核心路径标准库。Shapely 若可达仅用于额外 `is_simple` 复核；
预览沿用 render_preview.py 内置渲染器，缺渲染器如实报告。使用：
```bash
python3 scripts/build_svg.py /app/work/graph.json /app/output/figure.svg
# 核查同目录 routing_aabb.json 的 ok/geometry/self_intersections
```
图元类型、字段与完整流水线见 `examples/minimal_example.md`。

## 行为
支持缺省 cytoplasm、受体 membrane、真实 ID/悬空边日志、显式 `_x/_y`；
区室按 order 和实际成员数扩容，右侧图例专轨不参与节点排布。每个节点/边的
source.loc/quote 派生可见引用文本。只有在通道被其他节点 AABB 阻挡时绕行边，
不修改原始标签/相互作用语义。`routing_aabb.json` 记录节点/图例/出处矩形与路径自交。

## 限制
不承诺任意人工坐标都自动可读；显式重叠会报告失败而非自证完成。原始路径与
科学证据仍以输入材料为准，不联网补造型号、数值或实体定位。
