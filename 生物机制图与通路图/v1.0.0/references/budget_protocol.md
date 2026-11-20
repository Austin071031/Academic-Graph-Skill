# 预算与稳定性协议（可靠体验）

## 调用预算分配（上限 64 次模型请求 / 900s）
| 阶段 | 预算 | 内容 |
|---|---|---|
| 0 预检 | ≤2 | inspect_case + 读 task.md |
| 1 抽取 | ≤10 | 按 task.md 线索定位读 PDF 章节；禁止全文摘要式阅读 |
| 2 结构化 | ≤12 | graph.json + chart.json 编写；lint 修复 1 轮 |
| 3-5 渲染/导出/核验 | 0 | 纯脚本 |
| 缓冲 | ~10 | 核验修复、可读性微调、异常处置 |
| 保留 | 余量 | 不出手，留作保险 |

触发线：任一指标过半（>32 次或 >450s）→ 立即切换到**最小路径**：
lint→build_svg→render_preview→make_result，先落盘诚实 partial，再视余量增补。

## 跨通路类型的稳定性（重复运行一致性）
- 每次运行必走同一六步顺序与同一脚本版本（脚本内 GEN 版本号写死），产物结构（文件名、
  图层命名、result.json 字段）逐字节级稳定，仅内容随案例变化。
- 线性/分支/反馈环/多区室四类拓扑在 lint 通过后跑 topology.py 留档 layout_hints.json，
  证明布局决策可复现。
- 同一案例重复运行：graph.json 的元素集合应一致（来源决定论）；若第二次抽取漏元素，
  以第一次的 ledger 为准补齐——差异写入 change_log。

## 失败恢复点（每步落盘即检查点）
work/brief.json → source_text/*.txt → graph.json(+lint) → output/figure.* → result.json。
任一步崩溃：从上一个落盘文件恢复，不重做已完成步骤；run_log.md 记录断点与恢复动作。

## 异常速查（详见 failure_playbook.md）
渲染器缺失→matplotlib 兜底；PDF 无文本层→OCR→仍失败则 partial；合同字段不明→五要素保底；
改图任务→source-preserving edit，不重排坐标；数据矛盾→以数据表为准 + uncertainty 声明。
