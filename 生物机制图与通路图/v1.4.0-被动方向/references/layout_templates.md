# 布局模板与区室/跨膜规则

build_svg.py 自动布局：区室按 order 自上而下分层（胞外→膜→胞质→核），同区室节点按
sqrt 网格均匀排布。以下规则保证"布局本身传达正确机制"：

## 区室位置约束（硬规则）
1. 配体（ligand）→ extracellular；其受体 → membrane（画成跨膜条带，头部在胞外侧）。
2. 受体下游的胞内信号蛋白 → cytoplasm；转录因子及其基因靶点 → nucleus。
3. translocation 边的 to 端必须在目标区室；若源材料只说 "X translocates into the nucleus"
   而未画核内节点，必须补一个 X 的核内节点（或把 X 的 compartment 改为 nucleus 并在
   change_log 记录），不允许出现"边穿区室而端点区室不符"。
4. 分泌/释放的分子：膜内合成 → translocation/secretion → extracellular 节点。

## 方向与拓扑
- 主流向自上而下（胞外→膜→胞质→核）；反馈环（如负反馈）允许自下而上，但用虚线或
  evidence=weak/inferred 并加 label（如 "negative feedback"）。
- 并行分支共享同一上游节点；合并（convergence）多个上游指向同一下游。
- 线粒体/ER/Golgi 等附加区室 order 取 2.1–2.4，排在胞质与核之间。

## 可读性
- 节点超过 ~14 个时：优先按分支拆成两栏布局（保持区室带跨栏），或在 title-block 注明
  "simplified to N nodes (full ledger in graph.json)"，宁可简化也不允许元素重叠不可读。
- 长标签 wrap 到 ≤3 行；基因/蛋白符号优先，全名放 <title> 提示里。

## 检查点（渲染前自问）
- [ ] 每个膜蛋白真的跨在膜带中央？
- [ ] 核内节点都在 nucleus 椭圆内？
- [ ] 任意两条边是否大面积重叠？（有则调整节点 size 或 compartment 微调坐标 x/y，build_svg 支持节点级 x/y 覆盖自动布局）
