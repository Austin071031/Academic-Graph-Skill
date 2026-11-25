# 变更

相对 v1.0.0：仅强化结构归一、几何与原生出处。
- 缺省 cytoplasm、受体 membrane、稳定 ID、显式坐标和悬空边记录。
- 按成员数动态扩容，图例专轨，冲突时正交绕行，保留原语义。
- 原生 `<text>` 显示每个 source.loc（或 quote-only 来源）。
- 新增 routing_aabb.json，测节点/图例/出处相交及路径自交。
- 预览复核后将 context-stroke 换成显式颜色的小 marker，避免黑色大箭头。
