# TOOLS.md - report-agent 报告工具与模板

## 本地模板

| 模板 | 路径 | 用途 |
|---|---|---|
| market-report | `references/templates/market-report.md` | 市场战略分析报告基础模板 |

## Skills

| Skill | 路径 | 用途 |
|---|---|---|
| report-generator | `skills/report-generator/` | Markdown 报告生成 |
| html-report-generator | `skills/html-report-generator/` | HTML 演示文稿生成（含自定义光标特效） |

## 输出格式

| 格式 | 说明 |
|---|---|
| Markdown | 默认结构化报告 |
| HTML | 专业咨询风格演示文稿，适合留存检索和业务展示 |

### required_output_schema 规范

report-agent 执行报告生成前必须检查 `required_output_schema.formats`：

| formats 值 | 交付要求 |
|-----------|---------|
| `["markdown"]` | 仅 Markdown |
| `["html"]` | 仅 HTML（需要同时提供 markdown_report 输入） |
| `["markdown", "html"]` | 双格式（必须同时交付） |
| 未指定 | 默认 `["markdown", "html"]`（符合 SOUL.md 双格式原则） |

**重要**：如果 `output_format` 与 `required_output_schema.formats` 不一致，report-agent 必须：
1. 告警并补充缺失格式
2. 不能静默跳过任何 required 格式
3. 记录补全动作到 errors 字段

**HTML 触发条件**：
- 除非明确指定 `formats: ["markdown"]`，否则 report-agent 默认必须同时生成 HTML
- HTML 生成依赖 Markdown 结果，两者必须串行执行

## HTML 报告生成规范（强制）

### 强制调用 skill

生成 HTML 时**必须调用** `skills/html-report-generator/html_report_generator.py`：

```python
from skills.html_report_generator.html_report_generator import generate_from_markdown

result = generate_from_markdown(
    markdown_path="xxx/报告.md",
    output_path="xxx/报告.html"
)
```

### 设计标准

| 维度 | 规格 |
|---|---|
| 主色调 | 麦肯锡钴蓝 `#1d4ed8` |
| 配色辅助 | 朱砂红 `#c0392b` / 琥珀 `#d97706` / 绿 `#15803d` |
| 字体 | Outfit + Noto Sans SC + JetBrains Mono |
| 布局 | 全屏幻灯片 deck |
| 交互 | 键盘 ←→ 翻页 + 触摸滑动 + 鼠标滚轮 + 进度条 + 页码 `01/07` |
| 特效 | 自定义圆形蓝色光标（32px，悬停时 52px） |

### 输出路径规则

- Markdown: `{output_path}/{报告名}.md`
- HTML: `{output_path}/{报告名}.html`

### 文件要求

- 完整保留报告所有内容（不删减章节）
- 不新增或修改任何报告内容
- 保持与 Markdown 版本内容一致
- 支持浏览器搜索（Ctrl+F）

## HTML 交付前校验流程（强制）

**生成 HTML 后必须执行以下校验，不得直接交付：**

### 校验清单（7 项）

| 检查项 | 验证方法 | 失败影响 |
|--------|----------|----------|
| 键盘翻页 ←→ | 按方向键，确认页码变化 | 无法翻页 |
| 触摸滑动 | 移动端测试左右滑动 | 移动端失效 |
| 进度条更新 | 翻页后确认进度条宽度变化 | 失去位置感 |
| 页码显示 | 格式 `01/07`（零填充） | 显示混乱 |
| 动画效果 | slide 切换 fade + translateY | 体验生硬 |
| 所有 slides 可访问 | 逐页翻阅确认 | 部分内容丢失 |
| 无 JS 报错 | 浏览器 Console 无红色错误 | 功能异常 |
| 自定义光标 | 鼠标在页面上显示蓝色圆圈，悬停控件变大 | 失去品牌特色 |

### 历史教训

- **2026-06-28**：零跑 HTML 无法翻页 → 根因是 JavaScript 缺少 `updateUI()` 函数定义和初始化调用 → 修复：在脚本末尾添加 `updateUI()` 初始化调用
- **2026-06-29**：重构了 `updateUI` 函数实现，但**必须保证它在每个翻页函数（`goTo` / `next` / `prev`）内部被调用**，且在 `DOMContentLoaded` 时被初始化

### 正确流程

HTML 生成 → 自检验证 → 发现问题 → 修复 → 再次验证 → 确认无误 → 交付

## 工具使用规则

- 只处理编排专家传入的数据包、分析包和证据账本
- 不自行新增数据源
- 不自行新增战略判断
- 每个关键结论必须能映射到 evidence_mapping
- 输出前必须检查事实、置信度、风险、缺口是否保留
- **必须校验 `required_output_schema.formats` 是否全部满足**
- **生成 HTML 必须调用 skill，不允许手动拼接**

## 标准职责表达

基于 `data-agent` / `analysis-agent` 提供的数据和战略支撑，通过专业报告生成能力（`report-generator` + `html-report-generator` 两个 skill），生成行业专业级报告（Markdown + HTML 双版本），返回给 `strategy-orchestrator`。