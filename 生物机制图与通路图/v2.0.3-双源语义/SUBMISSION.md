# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107898 |
| 挑战赛 | `challenge-83d4f050` — 生物机制图与通路图 |
| 提交时间 | 2026-11-25T08:01:05+00:00 |
| 状态 | submitted / queued（待出分，2026-11-25T08:04:30+00:00 查分） |
| 得分 | 待出分（displayScore=null，scoreIsFinal=false；score=0 为平台占位，不记为成绩） |
| Bundle SHA-256 | `79957419b41123cd2bbb367425825d659a8f97c0aa2451669791bf9ccdb7d6b4` |
| 查询命令 | `playground status --attempt-id 107898 --json` |

本目录为本版独立提交根目录；父版为 **v1.0.0 / attempt 85718 / 73 / 100**。

## 方向与最小增量

draw.io 双源语义。完整生成 `mxGraphModel` 原生容器、节点和边对象；保留所有
关系线型/颜色/端点、图例和逐元素出处，SVG 仍由同一 graph.json 生成。

## 父版未通过与本地复验

父版抑制用 open arrow 而非 T-bar，缺 source、title、完整图例且缺省区室会异常。
运行 `python3 scripts/build_drawio.py work/graph.json output/figure.drawio`：
10 节点类型、13 边均保留原生对象与来源；抑制/repression 为原生 `bar`，
binding 无箭头实线，dissociation 无箭头虚线；容器与相对坐标有效，
native-citations 可见，dangling exit1。**18/18 通过**。

## 依据与限制

40→5 可编辑源文件与正确性。计数按实际生成对象，不能跳过悬空边而声称成功。
当前为本地 XML/语义验收，未声称用在线 draw.io 复核或官方 80 分；正式 attempt
与分数待平台返回，文件见 `figure_semantics.json` 的运行产物。
