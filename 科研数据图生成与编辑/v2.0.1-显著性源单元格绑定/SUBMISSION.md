# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | **107311** |
| 版本 | v2.0.1-显著性源单元格绑定 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 2026-11-25T06:46:33+00:00 |
| 状态 | submitted（queued，平台已接受，未出分） |
| 得分 | 待出分（不预测分数） |
| 查询命令 | `playground status --attempt-id 107311` |

## 父版与唯一改动

父版为当前最高已出分版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。本版只补“显著性文字来自源表指定单元格”与独立核验，不改变数值映射、图例或其他标注流程。对应题面“显著性标记”的正确性与“每个关键元素来源定位”的可核验性，不推定官方具体扣分项。

## 合成回归（非官方案例）

源表第 2 行 `p_label=p=0.03`，规格 `text=***`。父版显示 `***` 且标注映射没有源单元格；新版在标注自己的稳定 ID 显示 `p=0.03`，并能从该文件、SHA256、行和列独立回读。

执行并通过：

```bash
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_significance.py --map out/source_map.json --svg out/figure.svg --out out/significance_checks.json
python3 scripts/check_legend_series.py --spec spec.json --svg out/figure.svg
python3 scripts/verify_sources.py --map out/source_map.json --out out/source_checks.json
```

不计算 p 值或星号，不从柱高推断显著性；缺失或空白证据保持失败。2026-11-25 的完整五版测试共执行 22 项命令，全部通过。

## 实际提交证据

2026-11-25T06:46:33+00:00 通过 playground CLI 0.1.58 正式提交，平台返回 Attempt **107311**、状态 `submitted`、评分 `queued`。`bundle_sha256=8b3c3f6c2a161b60b5cb1e1ad5aee628b152c207c584d758190412243b6edf2d`。此追溯记录在 dry-run 与正式提交后追加，待平台出分后再回填分数。
