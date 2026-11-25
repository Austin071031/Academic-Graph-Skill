# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 待提交 |
| 挑战赛 | `challenge-9034312d` — 实验装置与技术路线图 |
| 提交时间 | 待提交 |
| 状态 | 未提交 |
| 得分 | 未出分 |
| 查询命令 | 待提交后填写 |

## 方向

图例避让。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

实际效果 / 结果完整性（5 分）：图例不遮挡科学实体及其数值、来源定位。

## 父版本

`v1.0`。本次只补它尚未通过的这一条本地检查。与已终分的 `v1.1.0-阶段带` 不是同一评分点。

## 本地检查前后

合成示例 `examples/example_ir.json`，非正式案例。父版本图例顶边压住 E2、E3、E4 的节点框，并盖住实体文字。

检查命令：

```
python3 scripts/pg_render.py --ir examples/example_ir.json --out diagram.svg --meta diagram.svg.meta.json
python3 scripts/legend_clearance.py --svg diagram.svg --meta diagram.svg.meta.json
```

父版本没有这个脚本，两次检查都用本目录的 `legend_clearance.py`。

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.0 | 图例压住 E2、E3、E4 的节点框，并盖住实体文字 | 1 |
| v1.2.0 | 图例在节点框和实体文字之下 | 0 |
