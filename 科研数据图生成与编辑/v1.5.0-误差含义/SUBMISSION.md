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

误差含义。父版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。

## 评分点

实际效果 / 结果正确性（15 分）：误差线含义与数据表一致。在途名额未占用。同一评分点已有 v1.3.0 在途时不提交这一份。

## 父版本

`v1.2.0-图例系列绑定`。本次只补它尚未通过的这一条本地检查。

## 本地检查前后

合成示例，非正式案例，不进提交包。数据表误差含义列是 `SD`，规格写成 `SEM`，同时声明 `error_kind_column=error_kind`。

检查命令：

```
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_error_kind.py --spec spec.json --svg out/figure.svg
```

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.2.0 | 渲染成功，图上没有 SD | 1 |
| v1.5.0 | 同一检查通过，图例含 SD | 0 |
