---
name: html-report-generator
description: "市场分析报告 HTML 演示文稿生成：基于 Markdown 报告生成麦肯锡钴蓝风格的 HTML 演示文稿，全屏幻灯片、键盘翻页、进度条、自定义圆形光标特效"
metadata: {"clawdbot":{"emoji":"📊"}, "openclaw": {"tools": ["generate_html_report"]}}
---

# HTML 报告生成 Skill

## 功能说明

基于 Markdown 报告生成专业咨询风格的 HTML 演示文稿（幻灯片模式），完全参照 D:\2024年度工作日志和备忘录\7.0 吕力\PPT策划制作与咨询风工作流标准指南.html 的设计风格。

## 设计特征（强制要求）

| 维度 | 规格 |
|---|---|
| 主色调 | 麦肯锡钴蓝 `#1d4ed8` |
| 配色辅助 | 朱砂红 `#c0392b`（风险）/ 琥珀 `#d97706`（强调）/ 绿 `#15803d`（正向） |
| 字体 | Outfit + Noto Sans SC + JetBrains Mono（Google Fonts） |
| 布局 | 全屏幻灯片 deck，每页独立 slide |
| 交互 | 键盘 ←→ 翻页 + 触摸滑动 + 进度条 + 页码 `01/07` 格式 + 悬停动画 |
| 特效 | **自定义圆形光标**（蓝色 32px 圆圈，悬停控件时变大为 52px） |
| 内容 | 完整保留报告所有内容（不删减章节），支持浏览器 Ctrl+F 搜索 |

## 工具列表

| 工具 | 用途 | 参数 |
|---|---|---|
| `generate_html_report` | 生成 HTML 演示文稿 | markdown_path, html_output_path, report_title, slides_data |

## 输入参数

| 参数 | 类型 | 说明 |
|---|---|---|
| markdown_path | string | Markdown 报告源文件路径 |
| html_output_path | string | HTML 报告输出路径 |
| report_title | string | 报告标题 |
| slides_data | list[dict] | 幻灯片数据，每项包含 section_title / section_content |

## 输出格式

```json
{
  "success": true,
  "html_path": "E:\\xxx\\报告名.html",
  "file_size": 30285,
  "slides_count": 8,
  "validation": {
    "keyboard_navigation": true,
    "touch_swipe": true,
    "progress_bar": true,
    "page_indicator": true,
    "animations": true,
    "all_slides_accessible": true,
    "no_js_errors": true
  },
  "features": {
    "custom_cursor": true,
    "google_fonts": true,
    "mckinsey_blue_theme": true
  }
}
```

## 必须遵守的硬性规范

1. **必须包含 updateUI() 函数**：负责翻页后同步更新进度条和页码显示（曾因此缺失导致零跑 HTML 无法翻页，必须保证）
2. **必须初始化调用 updateUI()**：脚本末尾必须有 `updateUI()` 调用，确保首屏进度条和页码正确显示
3. **必须包含自定义光标**：HTML 中 `<div class="cursor" id="cursor"></div>` + CSS `.cursor` / `.cursor.hovering` + JS 鼠标跟踪逻辑
4. **必须保证 slide 数量正确**：页码格式 `01/07` 中分母必须等于 slide 总数

## 校验清单（生成后自检）

| 检查项 | 验证方法 |
|---|---|
| 键盘翻页 ←→ | 按方向键翻页，确认进度条和页码同步更新 |
| 触摸滑动 | 移动端左右滑动 |
| 进度条更新 | 翻页后确认进度条宽度变化 |
| 页码显示 | 格式 `01/07` |
| 动画效果 | slide 切换 fade + translateY 动画 |
| 所有 slides 可访问 | 逐页翻阅确认 |
| 无 JS 报错 | 浏览器 Console 无红色错误 |
| 自定义光标 | 鼠标在页面上显示蓝色圆圈，悬停控件时变大 |

## 正确流程

HTML 生成 → 自检验证 → 发现问题 → 修复 → 再次验证 → 确认无误 → 交付

## 不允许

- 不允许手动拼接 HTML（必须调用本 skill）
- 不允许省略 updateUI() 函数
- 不允许省略自定义光标特效
- 不允许省略校验清单自检
- 不允许在 HTML 中新增或修改报告内容（报告内容必须与 Markdown 一致）

## 适用范围

所有需要交付 HTML 演示文稿的场景：
- 业务复盘报告
- 战略分析报告
- 市场研究报告
- 竞品分析报告
- 政策解读报告