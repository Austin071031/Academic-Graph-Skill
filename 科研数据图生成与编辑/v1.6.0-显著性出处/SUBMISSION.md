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

显著性出处。父版本 `v1.2.0-图例系列绑定`（attempt 103638，终分 73.3333）。

## 评分点

实际效果 / 结果可核验性（5 分）：显著性文字来自源表单元格。在途名额未占用。

## 父版本

`v1.2.0-图例系列绑定`。本次只补它尚未通过的这一条本地检查。

## 本地检查前后

合成示例，非正式案例，不进提交包。源表第 2 行 `p_label` 是 `p=0.03`，规格标注写成 `***`，同时声明 `text_column` 和 `row`。

检查命令：

```
python3 scripts/charts.py render --spec spec.json --out out
python3 scripts/check_significance.py --spec spec.json --svg out/figure.svg
```

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.2.0 | 渲染成功，图上没有 p=0.03 | 1 |
| v1.6.0 | 同一检查通过，图上有 p=0.03 | 0 |
