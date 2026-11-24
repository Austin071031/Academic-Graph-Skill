# graph.json 抽取模式（work/graph.json）

机制图的唯一结构化中间表示。先抽取、过 lint、再渲染——不要在 SVG 里手工改内容。

## 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| title | str | 图题，来自任务或论文图注 |
| species | str | 物种（如 "Homo sapiens"），用于命名前缀判断 |
| source_caption | str | 来源一句话（论文图注/材料位置），进图面标题区 |
| compartments | [{id,label,order?}] | 区室；order 越小越靠上。常用：extracellular(0) membrane(1) cytoplasm(2) nucleus(3) |
| nodes | [node] | 实体 |
| edges | [edge] | 相互作用 |
| legend.items | [{label,meaning}] | 数据编码图例（颜色=表达量、线宽=置信度等），由 build_svg 自动合并进图例 |

## node

```json
{
  "id": "stat3",
  "label": "STAT3",
  "type": "protein | gene | mrna | receptor | complex | small_molecule | ion | cell | phenotype",
  "compartment": "cytoplasm | membrane | nucleus | extracellular | <compartment id>",
  "synonyms": "STAT-3; signal transducer and activator of transcription 3",
  "species_prefix": "Hs",
  "size": 1.0,
  "fill": "#hex (可选，覆盖默认配色)",
  "source": {"loc": "paper p.4 Fig2A", "quote": "STAT3 is phosphorylated at Tyr705 ..."}
}
```

命名纪律（评分点：实体正确性）：
- 基因用斜体（图形上以 gene 类型表达，label 为基因符号）；蛋白/激酶/受体不用斜体含义、用 protein/receptor 类型。
- 复合物用 complex 类型并在 label 里写成分（如 "AP-1 (JUN+FOS)"）。
- 同名歧义（如 STAT3 基因 vs STAT3 蛋白）必须拆成两个节点，用 type 区分，并在 synonyms 里互相标注。

## edge

```json
{
  "id": "e1",
  "from": "jak2", "to": "stat3",
  "type": "activation | inhibition | binding | phosphorylation | dephosphorylation | ubiquitination | methylation | cleavage | translocation | transport | secretion | expression | induction | repression | association | dissociation | input | unknown",
  "label": "可选，如 pTyr705",
  "evidence": "strong | moderate | weak | inferred | predicted",
  "source": {"loc": "...", "quote": "..."}
}
```

关系语义映射（评分点：相互作用正确性）：
- "促进/增强/upregulates/activates" → activation；"抑制/downregulates/blocks/abolishes" → inhibition。
- "phosphorylates" → phosphorylation（端点带 P 标记）；"deubiquitinates" → 视方向用 ubiquitination/inhibition。
- "binds/interacts/forms a complex with" → binding（无端点箭头）。
- "translocates to the nucleus / imported into" → translocation，目标节点应在 nucleus 区室。
- 方向即因果方向：from = 作用方（上游），to = 被作用方（下游）。方向不确定时保留 direction 判断为弱证据 + 在 uncertainty 里声明。

## 数据编码（图例一致性）

若材料给出表达量/显著性/时间点：
- 在 node.fill 使用同一色板的深浅（如上调 #d73027、不变 #fee090、下调 #4575b4），并在 legend.items 写明 "color = log2 fold-change (dataset X, Fig n)"。
- 用 edge 的 evidence 字段表达证据强度（实线粗 = strong；虚线 = weak/inferred）。
- 任何编码必须能在 legend.items 与 result.json.sources 中找到出处；禁止图上出现图例无法解释的样式。
