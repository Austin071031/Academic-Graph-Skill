# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 待提交 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 待提交 |
| 状态 | 待提交 |
| 得分 | 待提交 |
| 查询命令 | 待提交 |

## 方向

样本量。父版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。

## 评分点

实际效果 / 结果完整性（5 分）：每个分类的样本量标注来自数据表。

## 父版本

`v1.2.0-图例系列绑定`。本次只补它尚未通过的这一条本地检查。与另一份在途版本打在不同评分点。

## 本地检查前后

合成示例，非正式案例，不进提交包。数据表两行：`A,4,8`、`B,7,6`，第三列是 `n`。规格声明 `n_column=n`，图上原本没有样本量。

检查命令：

```
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_sample_size.py --spec spec.json --svg out/figure.svg
```

`check_sample_size.py` 要求 SVG 含每个分类的 `n=<值>`。

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.2.0 | 渲染成功，图上没有 n=8 和 n=6 | 1 |
| v1.4.0 | 同一检查通过，图上有 n=8 和 n=6 | 0 |
