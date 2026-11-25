# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107899 |
| 挑战赛 | `challenge-83d4f050` — 生物机制图与通路图 |
| 提交时间 | 2026-11-25T08:01:09+00:00 |
| 状态 | submitted / queued（待出分，2026-11-25T08:04:30+00:00 查分） |
| 得分 | 待出分（displayScore=null，scoreIsFinal=false；score=0 为平台占位，不记为成绩） |
| Bundle SHA-256 | `f3c620c77630dbc7a32261672897177528c0e04b2f9849717262713f80cc5c25` |
| 查询命令 | `playground status --attempt-id 107899 --json` |

本目录为本版独立提交根目录；父版为 **v1.0.0 / attempt 85718 / 73 / 100**。

## 方向与最小增量

source-preserving 编辑。`source_edit.py` 用 lxml 定向修改真实源文件的原生标签/
文本与受控样式，不重建图；`edit_check.py` 同时验证 SVG 和 draw.io。
保存 *_edit_proof.json，重解析产物并验证非目标子树与几何拓扑不变。

## 父版未通过与本地复验

父版只改生成源的文本，缺真实输入编辑流程及非目标/几何证明；无 SVG 渲染器时
preview 可来自 graph.json 父图而非 edited SVG。实际运行：
```bash
python3 scripts/source_edit.py --input original.svg --changes edit_spec.json \
  --output edited_figure.svg --preview
```
SVG/drawio 标签与白名单样式成功，非目标摘要与 geometry/topology/viewBox 不变；
缺失 ID、坐标修改和非白名单属性均明确失败。**修复后 22/22 通过**。

## 依据与限制

40→5 source-preserving 与可核验性。缺渲染器如实 partial，不生成父图替代预览。
原生输入路径、目标 ID、前后值都留证。非正式案例结果，不保证官方 80 分。
