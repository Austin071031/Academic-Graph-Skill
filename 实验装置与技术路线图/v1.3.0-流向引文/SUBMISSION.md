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

流向引文。父版本 `v1.0`（attempt 85706，终分 72.3333）。

## 评分点

实际效果 / 结果正确性（15 分）：箭头方向与来源引文中的上下游一致。

## 父版本

`v1.0`。本次只补它尚未通过的这一条本地检查。与 `v1.2.0-图例避让` 不是同一评分点。

## 本地检查前后

合成示例，非正式案例，不进提交包。示例 C1 被改成 from=E2、to=E1，引文为「原料A进入预处理单元」。

检查命令：

```
python3 scripts/pg_render.py --ir quote_ir.json --out diagram.svg --meta diagram.svg.meta.json
python3 scripts/flow_quote_audit.py --ir quote_ir.json --svg diagram.svg --meta diagram.svg.meta.json
```

父版本没有这个脚本，两次检查都用本目录的 `flow_quote_audit.py`。

| 版本 | 结果 | 退出码 |
|-|-|-|
| v1.0 | C1 的箭头终点更靠近原料A，与引文相反 | 1 |
| v1.3.0 | C1 的箭头终点更靠近预处理单元 | 0 |
