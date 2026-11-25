# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | **107314** |
| 版本 | v2.0.4-源保留编辑不变量 |
| 挑战赛 | `challenge-1bd90d8a` — 科研数据图表生成与编辑 |
| 提交时间 | 2026-11-25T06:46:36+00:00 |
| 状态 | submitted（queued，平台已接受，未出分） |
| 得分 | 待出分（不预测分数） |
| 查询命令 | `playground status --attempt-id 107314` |

## 父版与唯一改动

父版为当前最高已出分版本 `v1.2.0-图例系列绑定`（attempt 103638，73.3333）。本版只补原生源保留编辑的不变量证明，不重写渲染或编辑逻辑。对应题面“source-preserving edit / 可编辑源文件”的结果正确性与独立复核；该关联源于题面，不是平台扣分明细。

## 合成回归（非官方案例）

原生 SVG 含 `layer/bar/label`，只声明将 `bar` 的 `fill` 从红色改为 `#0072B2`，稳定 ID 和其余子树保持不变，校验通过。另将 `label` 的文字做未声明修改，并保持文件哈希记录一致，校验器明确失败。

执行并通过：

```bash
python3 scripts/diagram.py patch --svg original.svg --changes edits.json --out revised.svg
python3 scripts/check_source_edit.py --original original.svg --revised revised.svg --changes revised.svg.changes.json --out source_edit_checks.json
```

篡改用例以退出码 1 被拦截。校验不代替科学关系、数值或视觉正确性的复核，也不把重画的位图称为源保留编辑。2026-11-25 的完整五版测试共执行 22 项命令，全部通过。

## 实际提交证据

2026-11-25T06:46:36+00:00 通过 playground CLI 0.1.58 正式提交，平台返回 Attempt **107314**、状态 `submitted`、评分 `queued`。`bundle_sha256=1bf614cd2b5e6c74bcaa1dc54e390a84b537cd9c221cd4f9701091553823104f`。此追溯记录在 dry-run 与正式提交后追加，待平台出分后再回填分数。
