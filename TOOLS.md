# TOOLS.md - report-agent 报告工具与模板

## 本地模板

| 模板 | 路径 | 用途 |
|---|---|---|
| market-report | 	emplates/market-report.md | 市场战略分析报告基础模板 |

## Skills

| Skill | 路径 | 用途 |
|---|---|---|
| report-generator | skills/report-generator/ | Markdown报告生成 |
| html-report-generator | skills/html-report-generator/ | HTML报告生成 |

## 输出格式

| 格式 | 说明 |
|---|---|
| Markdown | 默认结构化报告 |
| HTML | 专业咨询风格演示文稿，适合留存检索和业务展示 |

### required_output_schema 规范

report-agent 执行报告生成前必须检查 required_output_schema.formats：

| formats 值 | 交付要求 |
|-----------|---------|
| ["markdown"] | 仅 Markdown |
| ["html"] | 仅 HTML（需要同时提供 markdown_report 输入） |
| ["markdown", "html"] | 双格式（必须同时交付） |
| 未指定 | 默认 ["markdown", "html"]（符合 SOUL.md 双格式原则） |

**重要**：如果 output_format 与 required_output_schema.formats 不一致，report-agent 必须：
1. 告警并补充缺失格式
2. 不能静默跳过任何 required 格式
3. 记录补全动作到 errors 字段

**HTML 触发条件**：
- 除非明确指定 formats: ["markdown"]，否则 report-agent 默认必须同时生成 HTML
- HTML 生成依赖 Markdown 结果，两者必须串行执行

### HTML报告生成规范

当编排专家要求生成报告时，除了Markdown版本外，**必须同时生成HTML版本**：

**输出路径规则**：
- Markdown: {output_path}/{报告名}.md
- HTML: {output_path}/{报告名}.html

**HTML设计标准**：
- 主色调：#1d4ed8（麦肯锡钴蓝）
- 字体：Outfit + Noto Sans SC + JetBrains Mono
- 布局：全屏幻灯片，响应式设计
- 交互：键盘翻页、触摸滑动、进度条

**HTML文件要求**：
- 完整保留报告所有内容（不删减章节）
- 不新增或修改任何报告内容
- 保持与Markdown版本完全一致
- 支持浏览器搜索（Ctrl+F）

## HTML交付前校验流程

**生成HTML后必须执行以下校验，不得直接交付：**

### 校验清单

| 检查项 | 验证方法 |
|--------|----------|
| 键盘翻页 | 按左右键，确认页码变化 |
| 触摸滑动 | 移动端测试左右滑动 |
| 进度条 | 翻页后确认进度条更新 |
| 页码显示 | 确认格式为 01/07 |
| 动画效果 | 确认stagger动画正常 |
| 所有slides可访问 | 逐页翻阅确认 |
| 无JS报错 | 浏览器Console无红色错误 |

### 正确流程

HTML生成 → 自检校验 → 发现问题 → 修复 → 再次校验 → 确认无误 → 交付

---

## 工具使用规则

- 只处理编排专家传入的数据包、分析包和证据账本
- 不自行新增数据源
- 不自行新增战略判断
- 每个关键结论必须能映射到 evidence_mapping
- 输出前必须检查事实、置信度、风险、缺口是否保留
- **必须校验 required_output_schema.formats 是否全部满足**

## 标准职责表达

基于 data-agent / analysis-agent 提供的数据和战略支撑，通过专业报告生成能力，生成行业专业级报告（Markdown + HTML双版本），返回给 strategy-orchestrator。
