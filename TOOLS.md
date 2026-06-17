# TOOLS.md - 市场战略分析师工具集

## 统一运行约定（P0）

所有 `E:\AI\data\envs\car_agent_env\ai-decision\rag-engine` 下的市场数据、RAG、竞品、配置、报告工具，必须使用虚拟环境解释器：

```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe
```

不要使用系统默认 `python`。默认工作目录建议设为：

```bash
E:\AI\data\envs\car_agent_env\ai-decision\rag-engine
```

## 架构概览

本 Agent 采用**深度集成架构**（方案B），核心是 `HybridMarketAgent`，自动融合：

```
┌─────────────────────────────────────────────────────────────┐
│                    HybridMarketAgent                         │
│                                                             │
│  统一入口: analyze(query)                                   │
│           ↓                                                 │
│  意图理解 → 判断使用哪些数据源                              │
│           ↓                                                 │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │  结构化数据查询   │ + │  RAG 语义检索    │              │
│  │  PostgreSQL      │  │  向量数据库       │              │
│  │  销量/品牌/配置  │  │  行业报告/政策   │              │
│  └──────────────────┘  └──────────────────┘              │
│           ↓                     ↓                            │
│  ┌──────────────────────────────────────────────────┐      │
│  │            综合分析与输出                           │      │
│  │  市场洞察 + 竞品分析 + 机会识别 + 置信度评估      │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 深度集成 vs 轻量集成

| 方式 | 说明 |
|------|------|
| **深度集成（推荐）** | HybridMarketAgent 自动组合结构化数据 + RAG 上下文，用户只需调用 `analyze()` |
| **轻量集成（备用）** | 独立工具调用，需手动组合结果 |

---

## 核心工具

### 工具1: HybridMarketAgent（深度集成）

**推荐使用**，一个入口，自动完成：
- 结构化数据查询（销量/品牌/配置）
- RAG 上下文检索（行业报告/政策/历史）
- 综合分析输出

**Python 调用**：
```python
from market_strategy.hybrid_agent import HybridMarketAgent

agent = HybridMarketAgent()
output = agent.analyze(
    MarketInput(
        query="分析比亚迪市场策略",
        time_range="最近12个月"
    )
)
```

**Agent 状态检查**：
```python
status = agent.get_status()
# {'rag_available': True, 'llm_available': False, 'db_connected': True}
```

---

### 工具2: 市场数据查询

查询销量、品牌排名、细分市场分布、趋势数据

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\market_data_query.py <参数>
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| --action | str | 是 | 查询类型 | overview/brand/model/trend/segment |
| --time_range | str | 否 | 时间范围 | 最近12个月/最近6个月 |
| --tech_type | str | 否 | 技术类型 | 纯电动/插电式混合动力 |
| --segment | str | 否 | 细分市场 | SUV/A/B/C |
| --top_n | int | 否 | 返回数量 | 10/20/50 |

**使用示例**：
```bash
# 查询市场概况
E:\AI\data\envs\car_agent_env\Scripts\python.exe market_data_query.py --action overview

# 查询品牌排名 Top 10
E:\AI\data\envs\car_agent_env\Scripts\python.exe market_data_query.py --action brand --top_n 10

# 查询纯电动品牌排名
E:\AI\data\envs\car_agent_env\Scripts\python.exe market_data_query.py --action brand --tech_type 纯电动 --top_n 10

# 查询销量趋势
E:\AI\data\envs\car_agent_env\Scripts\python.exe market_data_query.py --action trend

# 查询细分市场分布
E:\AI\data\envs\car_agent_env\Scripts\python.exe market_data_query.py --action segment
```

---

### 工具3: 竞品对比分析

对比分析多个品牌的销量、份额、产品线

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\competitor_compare.py --brands 比亚迪,特斯拉,吉利
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| --brands | str | 是 | 品牌列表（逗号分隔） | 比亚迪,特斯拉,吉利 |
| --action | str | 否 | 分析类型 | compare/ranking |

---

### 工具4: 竞品配置查询

查询车型配置信息（续航、功率、价格等）

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\config_query.py --energy_type 纯电动 --top_n 10
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| --brand | str | 否 | 品牌名称 | 比亚迪 |
| --energy_type | str | 否 | 能源类型 | 纯电动/插电式混合动力 |
| --level | str | 否 | 级别 | A00/A/B/C |
| --top_n | int | 否 | 返回数量 | 10 |

---

### 工具5: 数据总览

获取数据库整体数据统计信息

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\data_summary.py
```

---

### 工具6: 报告生成

生成 Markdown 格式的市场分析报告

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\report_generator.py <参数>
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| --title | str | 是 | 报告标题 | 2026年紧凑型SUV市场分析 |
| --analysis_type | str | 是 | 分析类型 | pest/porter/swot/marketing/full |
| --output | str | 否 | 输出文件路径 | reports/analysis.md |

**使用示例**：
```bash
# 生成完整市场分析报告
E:\AI\data\envs\car_agent_env\Scripts\python.exe report_generator.py --title "比亚迪市场策略分析" --analysis_type full

# 生成PEST分析报告
E:\AI\data\envs\car_agent_env\Scripts\python.exe report_generator.py --title "新能源政策影响评估" --analysis_type pest

# 生成SWOT分析报告
E:\AI\data\envs\car_agent_env\Scripts\python.exe report_generator.py --title "小米汽车竞争优势分析" --analysis_type swot
```

---

## 分析框架工具

### 工具7: PEST 分析框架

执行 PEST（政治/经济/社会/技术）宏观环境分析

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\analysis_frameworks\pest_analysis.py --market 新能源
```

---

### 工具8: 波特五力分析

执行波特五力行业结构分析

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\analysis_frameworks\porter_analysis.py --segment 紧凑型SUV
```

---

### 工具9: SWOT 分析

执行 SWOT（优势/劣势/机会/威胁）分析

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\analysis_frameworks\swot_analysis.py --brand 比亚迪
```

---

### 工具10: 4P 营销分析

执行 4P（产品/价格/渠道/促销）营销组合分析

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\analysis_frameworks\marketing_analysis.py --brand 比亚迪
```

---

## RAG 工具（备用）

### 工具11: RAG 检索（备用接口）

RAG 检索的**备用接口**，仅在需要独立调用 RAG 时使用。**推荐使用 HybridMarketAgent**。

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\rag_retriever.py <参数>
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| --query | str | 是 | 检索查询 | 比亚迪市场策略分析 |
| --top_k | int | 否 | 返回数量 | 5 |
| --no_rerank | flag | 否 | 禁用重排序 | - |
| --source | str | 否 | 来源过滤 | 乘联会 |
| --brand | str | 否 | 品牌过滤 | 比亚迪 |
| --category | str | 否 | 类别过滤 | 行业报告 |

**使用示例**：
```bash
# 语义检索
E:\AI\data\envs\car_agent_env\Scripts\python.exe rag_retriever.py --query "比亚迪市场策略分析" --top_k 5

# 检索乘联会报告
E:\AI\data\envs\car_agent_env\Scripts\python.exe rag_retriever.py --query "新能源市场分析" --source 乘联会
```

---

### 工具12: 文档入库（数据准备）

将市场相关文档向量化存入向量数据库，供 RAG 使用

**调用方式**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\tools\document_ingest.py <参数>
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| --file | str | 否 | 单个文件路径 | 报告.pdf |
| --dir | str | 否 | 批量入库目录 | ./reports |
| --source | str | 是 | 来源 | 乘联会 |
| --brand | str | 否 | 相关品牌 | 比亚迪 |
| --category | str | 否 | 文档类别 | 行业报告 |

**使用示例**：
```bash
# 入库单个 PDF
E:\AI\data\envs\car_agent_env\Scripts\python.exe document_ingest.py --file 市场报告.pdf --source 乘联会 --category 行业报告

# 批量入库目录下所有 PDF
E:\AI\data\envs\car_agent_env\Scripts\python.exe document_ingest.py --dir ./reports --source 乘联会 --category 行业报告 --pattern "*.pdf"
```

---

## 使用流程示例

### 流程1: 使用 HybridMarketAgent（推荐）

```python
from market_strategy.hybrid_agent import HybridMarketAgent
from market_strategy.schemas import MarketInput

agent = HybridMarketAgent()

# 直接分析，Agent 自动决定使用哪些数据源
output = agent.analyze(
    MarketInput(
        query="分析比亚迪市场策略",
        time_range="最近12个月"
    )
)

print(f"置信度: {output.confidence}")
print(f"市场规模: {output.market_overview.scale}")
```

### 流程2: 分步使用工具

```bash
# 1. 获取数据总览
E:\AI\data\envs\car_agent_env\Scripts\python.exe data_summary.py

# 2. 查询市场概况
E:\AI\data\envs\car_agent_env\Scripts\python.exe market_data_query.py --action overview

# 3. 查询品牌排名
E:\AI\data\envs\car_agent_env\Scripts\python.exe market_data_query.py --action brand --top_n 10

# 4. 竞品对比
E:\AI\data\envs\car_agent_env\Scripts\python.exe competitor_compare.py --brands 比亚迪,特斯拉,吉利

# 5. 生成分析报告
E:\AI\data\envs\car_agent_env\Scripts\python.exe report_generator.py --title "市场竞争格局分析" --analysis_type full
```

### 流程3: 准备 RAG 数据

```bash
# 1. 入库行业报告
E:\AI\data\envs\car_agent_env\Scripts\python.exe document_ingest.py --dir ./行业报告 --source 乘联会 --category 行业报告

# 2. 入库政策文件
E:\AI\data\envs\car_agent_env\Scripts\python.exe document_ingest.py --dir ./政策文件 --source 工信部 --category 政策文件

# 3. 验证 RAG 检索
E:\AI\data\envs\car_agent_env\Scripts\python.exe rag_retriever.py --query "新能源购置税政策"
```

---

## RAG 数据源规划

### 待向量化文档

| 文档类型 | 来源 | 用途 | 优先级 |
|----------|------|------|--------|
| 行业报告 | 乘联会、中汽协、咨询机构 | 市场趋势分析 | P1 |
| 政策文件 | 工信部、发改委、财政部 | 政策影响评估 | P1 |
| 竞品分析 | 历史分析报告 | 竞品历史对比 | P2 |
| 新闻舆情 | 汽车之家、易车、懂车帝 | 热点事件分析 | P2 |
| 用户评价 | 车质网、论坛 | 用户痛点洞察 | P3 |

### Metadata 设计

```json
{
  "source": "来源机构",
  "brand": "相关品牌",
  "category": "行业报告/政策文件/新闻/用户评价",
  "publish_date": "发布日期",
  "car_model": "相关车型",
  "segment": "细分市场"
}
```

---

## Agent 状态检查

```python
# 检查 Agent 状态
status = agent.get_status()
print(status)

# 输出示例:
# {
#   'rag_available': True,      # RAG 是否可用
#   'rag_init_error': None,    # RAG 初始化错误
#   'llm_available': False,   # LLM 是否可用
#   'db_connected': True       # 数据库是否连接
# }
```

---

## 注意事项

1. **推荐使用 HybridMarketAgent** - 一个入口，自动集成所有能力
2. **RAG 优雅降级** - RAG 不可用时自动降级到纯结构化分析
3. **路径问题** - 所有 Python 命令使用绝对路径
4. **数据时效** - 市场数据更新频率为每月初
5. **置信度** - 所有分析输出包含置信度评估，低于 0.7 需要人工复核

