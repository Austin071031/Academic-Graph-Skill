# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 未提交 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 未提交 |
| 状态 | 未提交 |
| 得分 | 未提交 |
| 查询命令 | 未提交 |

## 方向

零基线。父版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。

## 评分点

实际效果 / 结果正确性（15 分）：柱状图纵轴保留 0。在途名额未占用。同一评分点已有 v1.3.0 在途时不提交这一份。

## 父版本

`v1.2.0-图例系列绑定`。本次只补它尚未通过的这一条本地检查。

## 本地检查前后

合成示例，非正式案例，不进提交包。柱高是 4 和 7，规格把纵轴限制写成 `[2, 10]`。

检查命令：

```
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_bar_baseline.py --checks out/export_checks.json
```

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.2.0 | 渲染成功，检查仍报 bar_baseline_truncated | 1 |
| v1.7.0 | 同一检查通过，纵轴包含 0 | 0 |
