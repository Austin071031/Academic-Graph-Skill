# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107896 |
| 挑战赛 | `challenge-83d4f050` — 生物机制图与通路图 |
| 提交时间 | 2026-11-25T08:00:57+00:00 |
| 状态 | submitted / queued（待出分，2026-11-25T08:04:30+00:00 查分） |
| 得分 | 待出分（displayScore=null，scoreIsFinal=false；score=0 为平台占位，不记为成绩） |
| Bundle SHA-256 | `88ac281871239fc9bc227ecde1c88e75b42be00abd427f625ebf70f96d705206` |
| 查询命令 | `playground status --attempt-id 107896 --json` |

本目录为本版独立提交根目录；父版为 **v1.0.0 / attempt 85718 / 73 / 100**。
score 与 attempt 待官方返回后回填。

## 方向与最小增量

数值图表。替换 `build_chart.py`，让数值 x 真正线性升序，散点不连线；
类别保持原序，系列可独立横轴，图例与数据 ID 归一，来源文本可见；
同一规范化数组生成 SVG/CSV/PNG。缺测不补零且折线按原始缺口分段。

## 父版未通过与本地复验

父版 x=[100,0,20,10] 仍按等距类别绘制，且 chart.png 未生成。
本版运行 `python3 scripts/build_chart.py work/chart.json output/chart.svg`：
排序后 x=[0,10,20,100] 相邻像素差 [58.620,58.621,468.965]，比例约 8:1:1；
散点只有圆点；CSV/PNG 同源。修复后 **34/34 通过**，含 [1,null,3] 不连线，
[1,2,null,4,5] 恰有两段，per-record source 与独立横轴均通过。

## 依据与限制

40→5 结果正确性与完整性。SVG 原生文本显示 caption 或 series source.loc；
matplotlib 后端实测输出真实 PNG；缺后端如实记录而不使用父图。全部数字为接口合成，
未宣称官方案例复现，正式成绩以 SUBMISSION.md 后续查分为准。
