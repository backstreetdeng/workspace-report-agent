# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20260526-001] correction

**Logged**: 2026-05-26T19:22:00+08:00
**Priority**: critical
**Status**: promoted
**Area**: config

### Summary
未在任何配置文件中看到 car_market 数据库，却声称其存在——这是凭空捏造的严重错误

### Details
用户询问数据库情况时，我检查了以下文件的数据库配置：
- knowledge_base.py → database: vectordb
- pgvector_client.py → database: vectordb
- 	est_pg.py → database: vectordb

远程 192.168.3.146 上实际只有 ectordb 数据库，从未存在 car_market。

我没有任何依据就提到了 car_market，这是完全凭空捏造的错误。

### Suggested Action
1. 以后所有信息必须基于实际看到的文件/代码/查询结果
2. 不确定的信息必须明确标注「未经核实」
3. 绝不能用"可能"、"或许"等推测性语言当作事实

### Metadata
- Source: user_feedback
- Related Files: E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\market_strategy\knowledge_base.py
- Tags: database, configuration, factuality
- Pattern-Key: factuality.never-fabricate
- Recurrence-Count: 1
- First-Seen: 2026-05-26
- Last-Seen: 2026-05-26

---


---

## [LRN-20260526-002] best_practice

**Logged**: 2026-05-26T19:35:00+08:00
**Priority**: critical
**Status**: pending
**Area**: config

### Summary
安全性不好的 skill 绝对不安装——这是不可妥协的绝对原则

### Details
审查 proactive-agent skill 时，发现：
- ClawHub 标记为 SUSPICIOUS
- VirusTotal Code Insight 标记为 risky
- 包含 eval、外部 API 调用等可疑模式

用户明确指示：安全性不好的绝对不安装。

### Suggested Action
1. 任何 skill 安装前必须通过 skill-vetter 审查
2. 标记为 SUSPICIOUS/HIGH/⛔ EXTREME 的 skill 一律不安装
3. 未经人工审查的代码不安装到工作环境

### Metadata
- Source: user_feedback
- Tags: security, skill-installation, principle
- Pattern-Key: security.never-compromise

---
