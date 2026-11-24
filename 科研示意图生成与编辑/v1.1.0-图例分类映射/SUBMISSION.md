# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 103608 |
| 挑战赛 | `challenge-98e5a474` — 科研示意图生成与编辑 |
| 提交时间 | 2026-11-24T07:04:50+00:00（北京时间 2026-11-24 15:04） |
| 状态 | 待出分（`state: queued`，`scoreIsFinal: false`） |
| 得分 | 待出分 |
| 查询命令 | `playground status --attempt-id 103608` |

## 方向

图例分类映射。父版本 `v1.0.1`（attempt 73746，终分 72.6667）。

## 评分点

实际效果 / 结果正确性（15 分）：图例项、颜色与数据表的分类数目一致。

## 父版本

`v1.0.1`。本次只补它尚未通过的这一条本地检查。

## 本地检查前后

合成示例，非正式案例，不进提交包。数据表三行：`Sample-A,#1B4F72`、`Sample-B,#B9770E`、`Sample-C,#196F3D`。规格里三个节点带对应 `category`，但填色是 `#111111`、`#222222`、`#333333`，图例只有前两类。

检查命令：

```
python3 scripts/diagram.py render --spec spec.json --data categories.csv --out out.svg
python3 check_legend_map.py --svg out.svg --data categories.csv --spec spec.json
```

`check_legend_map.py` 要求图例文字和颜色与数据表逐行相同，且每个节点填色等于其分类在表中的颜色。

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.0.1 | `render --data` 不识别该参数 | 2 |
| v1.0.1 | 不带 `--data` 渲染出的 SVG，检查失败（图例 2 项，填色与表不一致） | 1 |
| v1.1.0 | `render --data` 成功，同一检查通过 | 0 |
