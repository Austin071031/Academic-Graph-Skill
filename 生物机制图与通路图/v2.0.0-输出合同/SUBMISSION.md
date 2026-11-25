# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107895 |
| 挑战赛 | `challenge-83d4f050` — 生物机制图与通路图 |
| 提交时间 | 2026-11-25T08:00:53+00:00 |
| 状态 | submitted / queued（待出分，2026-11-25T08:04:30+00:00 查分） |
| 得分 | 待出分（displayScore=null，scoreIsFinal=false；score=0 为平台占位，不记为成绩） |
| Bundle SHA-256 | `d4672f7393cdf9717d6ba057608b30e53ea681e3fd62f728cc904f6c548de0f1` |
| 查询命令 | `playground status --attempt-id 107895 --json` |

本目录全部文件是本版实际提交根目录，父版为 **v1.0.0 / attempt 85718 / 73 / 100**。
不把父版成绩视作本版成绩。score、hash、attempt 均以正式返回回填。

## 方向与最小增量

输出合同。`make_result.py` 支持字典/列表字段、显式 path、完整扩展名映射；
`validate.py` 检查必需文件 null/缺件/错格式，optional 缺失不 HARD；两轮汇编防止 stale check。
不合并图例、布局、图表、draw.io 或源图编辑改动。

## 父版未通过与本地复验

父版曾将 `figure_png` 与 `figure_svg` 都映射到 `figure.drawio`。
本版实际执行：
```bash
python3 scripts/make_result.py work output
python3 scripts/validate.py work/graph.json output work/brief.json
python3 scripts/make_result.py work output
```
合成输入覆盖 dict/list、显式路径、可选缺失和必需缺失：**23/23 通过**。
正确输出 `figure.png`、`figure.svg`、`figure.drawio`，final 与 check_report 一致；
删除必需 drawio 后返回 HARD/partial。非正式案例答案，证据仅证明接口行为。

## 依据与限制

40→5 可核验性；同时修复 40 分闭环交付。平台未提供父版分项扣分，本版不推断
具体提升分值。回归命令/路径记录见本任务的 `bohrium/regression_report.md`（开发记录，
不属于 Skill 安装资源），不是正式结果或预测分。
