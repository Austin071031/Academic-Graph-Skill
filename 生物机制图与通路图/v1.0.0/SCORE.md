# 生物机制图与通路图 v1.0.0 平台得分

| 项目 | 官方记录 |
|---|---|
| 题目 | 生物机制图与通路图（科研绘图：生成图稿，也保留可编辑来源） |
| Challenge ID | `challenge-83d4f050` |
| Attempt | **85718** |
| Skill 版本 | **1.0.0**（内部优化变体代号 `v2-verifiability`，可核验性强化版） |
| 提交时间 | 2026-11-18 01:36:53（Asia/Shanghai） |
| 查分日期 | 2026-11-20（Asia/Shanghai） |
| 最终得分 | **73 / 100** |
| 状态 | `scored`；`scoreIsFinal: true` |
| Harbor reward | `0.73`（`harbor_errors: 0`） |
| Trace factor | `1` |

题目链接：https://play.bohrium.com/challenge/challenge-83d4f050

官方反馈原文：

> Received and graded in full. Solid — refine for a more complete and rigorous solution.

平台未提供分维度扣分明细；本目录不推断各项得分。73 分是该提交的官方成绩，不保证其他运行复现相同分数。

## 本轮提交背景

2026-11-17 同一批次提交 6 个优化变体（同一基座 + 各自强化一个评分维度），全部出分：

| Attempt | 内部变体 | 强化维度 | 官方得分 |
|---|---|---|---|
| **85718** | **v2-verifiability** | **逐元素出处台账（可核验性）** | **73.0** |
| 85717 | v1-correctness | 相互作用语义判定表（正确性） | 72.6667 |
| 85722 | v5-robust | 预算触发线与检查点（可靠体验） | 71.6667 |
| 85721 | v4-editable-export | 改标签重导出实证（可编辑性） | 70.0 |
| 85720 | v3-legend-data | 图例-图面-数据三方对账 | 68.3333 |
| 85723 | v6-efficiency | 拓扑预分类压缩模型调用 | 66.6667 |

本目录归档其中最高分版本 85718。该分数同时刷新了本人在此题目上的此前最高分（attempt 73816，70.6667）。同轮其余 5 个变体未归档；如需追溯，可在平台按 Attempt 号查询。

得分观察（供下轮迭代参考，非平台结论）：可核验性强化相对基线 +2.3 分，是六个方向中唯一稳定正增益的尖峰；正确性与稳健性变体增益接近噪声，说明剩余失分更多来自隐藏案例上的实际执行表现，而非 Skill 文本表述。

## 归档对应关系

本目录的 `SKILL.md`、`README.md`、`CHANGELOG.md`、`references/`（6 篇）、`scripts/`（13 个）、`examples/`（1 篇）共 23 个文件，取自 85718 提交时传给 `playground submit --outputs` 的目录，与打包上传内容逐字节一致（归档时用 `diff -rq` 核验无差异）。各文件 SHA256 见 `PROVENANCE.json`。

本目录归档 Skill 本体及成绩记录，不包含整份 ARM 提交包、作者执行轨迹、诊断案例、预制答案或凭据；不是重新提交记录。后续版本应另建目录，保留本版本不变。
