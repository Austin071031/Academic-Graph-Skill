# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | **107312** |
| 版本 | v2.0.2-柱图零基线强制 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 2026-11-25T06:46:34+00:00 |
| 状态 | submitted（queued，平台已接受，未出分） |
| 得分 | 待出分（不预测分数） |
| 查询命令 | `playground status --attempt-id 107312` |

## 父版与唯一改动

父版为当前最高已出分版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。本版只修复线性柱图零基线可能被 `ylim` 截断的问题，并增加显式机器通过项，其他科学映射与导出参数不改。目标是题面“数据编码/坐标轴刻度”的正确性，不是视觉美化。

## 合成回归（非官方案例）

柱高为 4 与 7，规格 `ylim=[2,10]`。父版的 `export_checks.json` 记录 `bar_baseline_truncated` 但仍导出；新版最终纵轴含 0，源值与柱高保持 4、7，检查通过。

执行并通过：

```bash
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_bar_baseline.py --checks out/export_checks.json
python3 scripts/verify_sources.py --map out/source_map.json --out out/source_checks.json
```

对数柱图仍按父版明确拒绝，不静默用普通坐标替代。2026-11-25 的完整五版测试共执行 22 项命令，全部通过。

## 实际提交证据

2026-11-25T06:46:34+00:00 通过 playground CLI 0.1.58 正式提交，平台返回 Attempt **107312**、状态 `submitted`、评分 `queued`。`bundle_sha256=7299ca30f13ea7997e51da298a52325b2442750f80596929eccd227f8c606ef3`。此追溯记录在 dry-run 与正式提交后追加，待平台出分后再回填分数。
