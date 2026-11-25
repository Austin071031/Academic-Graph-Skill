# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| Attempt ID | 107897 |
| 挑战赛 | `challenge-83d4f050` — 生物机制图与通路图 |
| 提交时间 | 2026-11-25T08:01:02+00:00 |
| 状态 | submitted / queued（待出分，2026-11-25T08:04:30+00:00 查分） |
| 得分 | 待出分（displayScore=null，scoreIsFinal=false；score=0 为平台占位，不记为成绩） |
| Bundle SHA-256 | `a8f0956039ba210fbc3c3f0bb26746a1a0614f5cb086e2034c6d5ca5ebcd53ac` |
| 查询命令 | `playground status --attempt-id 107897 --json` |

本目录为本版独立提交根目录；父版为 **v1.0.0 / attempt 85718 / 73 / 100**。

## 方向与最小增量

原生引用布局。`build_svg.py` 配合 `render_mechanism.py` 做结构归一、缺省区室、
按成员扩容、坐标覆盖、原生来源、冲突绕行及测量，不改图表或合同实现。
新增 `routing_aabb.json`，不以外部图片代替科学 glyph。

## 父版未通过与本地复验

父版无 compartments 时不画节点/边；固定右侧图例可与节点相交；缺 caption 时
来源只在 metadata/title。运行 `python3 scripts/build_svg.py work/graph.json output/figure.svg`：
1/2/10/20 节点均无节点/图例/出处重叠，受体中心与膜带一致，引用为真实 SVG 文本；
A→C 穿过 B 时改走正交通道且 native 与 Shapely 均无自交。**25/25 通过**。
CairoSVG 另测将 context-stroke 修正为显式颜色小 marker，并人工确认图面可读。

## 依据与限制

40→5 结果正确性/可核验性。每个 source.loc/quote 保留并派生到可见引用，
证据强度独立记录；不凭空生成实体/定位/型号。显式坐标重叠会标 false，
不能自证完整。以上均为合成测试，不声称官方案例得分或 80 分已达。
