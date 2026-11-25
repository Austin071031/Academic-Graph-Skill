# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| 版本 | v2.0.0 |
| 父版本 | v1.0.1（attempt 73746，官方终分 72.6667 / 100） |
| 唯一改进方向 | 逐元素来源反查：文件存在性、SHA256、精确定位、引文/数值及 spec/SVG ID 双向对账 |
| 基础渲染器 | `scripts/diagram.py` 与 v1.0.1 逐字节一致 |
| 合成检查 | 通过；有效映射通过，哈希漂移拒绝，空规格拒绝（独立回归共17组中的本版3组） |
| Playground Attempt ID | **107334** |
| 提交时间 | 2026-11-25T06:57:33+00:00 |
| 状态 | submitted；评分状态 queued，`scoreIsFinal=false` |
| 得分 | 待出分（当前 score=0 仅为占位，不是评分结论） |
| Bundle SHA256 | `de2dc2d93ca6b51270d561195e81612a32913033b2550bbec9ed0a4a9953a959` |
| 查询命令 | `playground status --attempt-id 107334` |

首次上传因 CLI 的 `--raw-messages` 打包未含 `native_trace/` 被 Worker 拒绝；改用同一实际会话轨迹的 `--trace` 接口重新打包后，向原 attempt 107334 补传成功，没有重复创建提交。

本目录不包含正式案例、预制图稿或统计成绩。工具通过不证明科学正确性；平台正式结果返回后回填，不预写分数。
