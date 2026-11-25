# 输出合同与交付清单

## /app/output 必须包含

| 文件 | 性质 | 说明 |
|---|---|---|
| result.json | 结构化结果 | case_id、status、main_results、sources、uncertainty、change_log、artifacts、validation；并补齐 case.json output_contract 声明的全部字段 |
| figure.svg | 可编辑源文件（主） | 分层（区室/节点/边/图例四组）、id 命名、<metadata> 含来源、<title> 提示含逐元素出处 |
| figure.drawio | 可编辑源文件（副） | draw.io 可打开，改标签后可重导出；与 SVG 同源（graph.json） |
| figure.png / figure.pdf | 导出件 | 预览；render_report.json 记录渲染器与失败原因 |
| check_report.json | 核验记录 | validate.py 的全部检查结果 |
| run_log.md | 过程记录 | 步骤、判断、预算消耗、异常与处置 |

图表类案例另含：chart.svg、chart.png、chart_data.csv（数值表，可复核）。

## result.json 五要素（缺一不可）
1. case_id — 与 case.json 完全一致
2. status — complete / partial（partial 必须说明缺什么）
3. sources — 每个关键图面元素的出处（材料路径 + 页/图 + 引文摘录）
4. uncertainty — 方向不明、证据弱、矛盾处等
5. change_log — 相对输入材料的每一次取舍/修正（含自动简化）

## 诚实性红线
- 不虚构软件状态、不伪造数值；图上的数字必须能指到材料里的数字。
- partial 也是有效交付：先存诚实 partial，再增量改进（预算约束下尤其如此）。
- 示意输出（examples/）不得冒充正式案例结果。
