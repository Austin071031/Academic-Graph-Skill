# 相互作用语义判定表（正确性核心）

把材料措辞映射到边类型的判定流程。**拿不准时先查此表，再写 graph.json；表内没有
的措辞用 type=unknown + evidence=weak，并在 uncertainty 声明。**

## 判定顺序（自上而下，先匹配先用）

1. **物理结合**：binds / interacts with / forms a complex with / associates with
   → `binding`（无端点箭头，深蓝）。解离/解组装 dissociates / disassembles → `dissociation`（虚线无端点）。
2. **共价修饰**（动词以 -ates 结尾、有修饰位点时优先于激活/抑制）：
   phosphorylates → `phosphorylation`（紫，端点 P 标记，label 写位点如 pTyr705）；
   dephosphorylates → `dephosphorylation`（紫虚线 P(-)）；ubiquitinates → `ubiquitination`（橙 Ub）；
   methylates → `methylation`（橙 Me）；cleaves/proteolyzes → `cleavage`（灰剪刀）。
3. **方向性调控**（改变活性/表达，无共价修饰）：
   activates / promotes / enhances / upregulates / drives → `activation`（绿实心箭头）；
   inhibits / suppresses / blocks / attenuates / abolishes / knockdown of → `inhibition`（红 T 棒）。
   转录层面的 induces expression of → `expression`（绿箭头，目标为 gene 节点）；
   represses transcription of → `repression`（红 T 棒）。
4. **位置变化**：translocates to / imported into / shuttles into → `translocation`（青虚线箭头，
   目标节点必须在目标区室）；secretes / releases → `secretion`；transports/carries → `transport`。
5. **输入/刺激**：材料中的处理条件（药物、刺激、敲除）作为上下文节点 → `input`（灰虚线箭头）。

## 方向铁律
- from = 作用方，to = 被作用方。"X is activated by Y" ⇒ from=Y to=X。逐句核对主被动。
- 材料只说相关（correlates with / associated in patients）→ 不是调控边：
  `association` + evidence=weak + uncertainty 声明"关联≠因果"。

## 实体类型铁律
- 激酶/受体/转录因子/抗体 = protein 或 receptor；其基因符号（讨论表达、突变、启动子时）= gene。
- 复合物 = complex，label 写成分（"mTORC1 (mTOR+Raptor)"）；家族成员不能合并成一个节点，
  除非材料明确以家族整体作用（此时 label 写 "JUN/FOS family"）。
- 配体、代谢物、药物 = small_molecule；离子 = ion；细胞/细胞类型 = cell/cell_type（画在最外层语境带）。
- 同一分子跨区室移动：源区室与目标区室各一个节点（如 "TF (cytosol)"、"TF (nucleus)"），
  用 translocation 边连接——这是区室正确性的常见失分点。

## 证据强度
- strong：材料直接陈述（"X phosphorylates Y"）或有图注佐证；
- moderate：直接陈述但来自单一实验；weak：间接/推测（may, might, suggested）；
- inferred/predicted：由本图其他边推断，必须在 label 或 uncertainty 说明推断依据。
