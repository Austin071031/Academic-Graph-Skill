# bio-mechanism-pathway-illustrator · v2.0.4 原图编辑

父版：v1.0.0（attempt 85718，73/100）。本版唯一机制增量：对已有 SVG/draw.io
做最小、有界、可证伪编辑，不重新生成图来冒充原图保留编辑。

## 调用与依赖
必需 lxml（本仓库开发环境已实测）；必需依赖缺失时失败并说明，不退回失控正则。
其它生成流水线 Python 标准库。预览沿用内置渲染器，只能渲染改后 SVG。
```bash
python3 scripts/source_edit.py \
  --input /input/original.svg --changes /app/work/edit_spec.json \
  --output /app/output/edited_figure.svg --preview
```
`edit_spec.json` 为 `changes` 数组：真实 `id` 与 `kind:label/value`，或
`kind:attribute/name/value`。完整新图调用另见 `examples/minimal_example.md`。

## 校验
目标必须唯一且已存在；缺文本、几何/拓扑/viewBox 改变、未白名单属性均失败。
`*_edit_proof.json` 记录前后值、非目标 ID 规范化摘要、几何/连接不变性及导出重解析。
无栅格器时如实 partial，不用 graph.json 父图生成假预览。

## 限制
此接口只修改原生标签/文本和声明的样式白名单；任意布局重排不是本接口承诺。
原生输入、素材来源和不确定性必须进入交付记录。
