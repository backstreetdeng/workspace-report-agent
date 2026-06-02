"""
工作流调试脚本 - 逐个验证每个skill
使用正确的方式导入skill（目录名含连字符）
"""

import sys
import os
from pathlib import Path

# 添加路径
RAG_ENGINE = r"E:\AI\data\envs\car_agent_env\ai-decision\rag-engine"
SKILLS = r"C:\Users\11489\.openclaw\workspace-market\skills"
WORKFLOW = r"C:\Users\11489\.openclaw\workspace-market\workflows"

sys.path.insert(0, RAG_ENGINE)
sys.path.insert(0, WORKFLOW)

# 加载环境变量
env_path = os.path.join(os.path.dirname(RAG_ENGINE), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def import_skill(skill_dir_name: str, module_file: str):
    """
    导入skill模块（处理连字符目录名）
    skill目录名: intent-classifier, pg-vector-search
    模块文件名: intent_classifier.py, vector_search.py
    """
    skill_path = Path(SKILLS) / skill_dir_name
    if skill_path.exists():
        sys.path.insert(0, str(skill_path))
        module_name = module_file.replace(".py", "")
        import importlib
        return importlib.import_module(module_name)
    else:
        raise ImportError(f"Skill not found: {skill_path}")


print("=" * 60)
print("工作流调试脚本")
print("=" * 60)

# ========================================
# Step 1: 意图识别
# ========================================
print("\n【Step 1】意图识别 - intent_classifier")
print("-" * 40)
try:
    ic = import_skill("intent-classifier", "intent_classifier.py")
    classifier = ic.IntentClassifier()

    question = "分析比亚迪的市场战略"
    result = classifier.classify(question)

    print(f"问题: {question}")
    print(f"意图: {result.intent_type}")
    print(f"置信度: {result.confidence}")
    print(f"品牌: {result.brands_mentioned}")
    print("✅ intent_classifier 正常")
except Exception as e:
    print(f"❌ intent_classifier 失败: {e}")
    import traceback
    traceback.print_exc()

# ========================================
# Step 2: 向量检索
# ========================================
print("\n【Step 2】向量检索 - pg_vector_search")
print("-" * 40)
try:
    pvs = import_skill("pg-vector-search", "vector_search.py")

    query = "比亚迪市场战略分析"
    result = pvs.vector_search(query=query, top_k=3, search_mode="hybrid")

    print(f"查询: {query}")
    print(f"成功: {result.get('success')}")
    print(f"结果数: {result.get('count', 0)}")
    if result.get('results'):
        for i, r in enumerate(result['results'][:2], 1):
            print(f"  [{i}] Score: {r.get('score', 0):.4f}")
            print(f"      内容: {r.get('content', '')[:80]}...")
    print("✅ pg_vector_search 正常")
except Exception as e:
    print(f"❌ pg_vector_search 失败: {e}")
    import traceback
    traceback.print_exc()

# ========================================
# Step 3: 结构化查询
# ========================================
print("\n【Step 3】结构化查询 - nl2sql_pg")
print("-" * 40)
try:
    nsql = import_skill("nl2sql-pg", "nl2sql.py")

    question = "比亚迪最近销量如何"
    result = nsql.query(question, execute=True)

    print(f"问题: {question}")
    print(f"成功: {result.get('success')}")
    print(f"SQL: {result.get('sql', '')[:100]}...")
    print(f"记录数: {result.get('record_count', 0)}")
    if result.get('results'):
        for r in result['results'][:3]:
            print(f"  - {r}")
    print("✅ nl2sql_pg 正常")
except Exception as e:
    print(f"❌ nl2sql_pg 失败: {e}")
    import traceback
    traceback.print_exc()

# ========================================
# Step 4-6: 四大框架分析
# ========================================
print("\n【Step 4-6】四大框架分析 - automotive_strategy_analysis")
print("-" * 40)
try:
    asa = import_skill("automotive-strategy-analysis", "strategy_analysis.py")

    # PEST分析
    print("4.1 PEST分析...")
    pest_result = asa.pest_analysis()
    print(f"   成功: {pest_result.get('success')}")

    # 波特五力
    print("4.2 波特五力分析...")
    porter_result = asa.porter_analysis()
    print(f"   成功: {porter_result.get('success')}")

    # SWOT分析
    print("4.3 SWOT分析...")
    swot_result = asa.swot_analysis("比亚迪")
    print(f"   成功: {swot_result.get('success')}")
    if swot_result.get('success'):
        data = swot_result.get('data', {})
        swot = data.get('swot', {})
        print(f"   优势: {len(swot.get('strengths', []))}条")

    # 4P分析
    print("4.4 4P分析...")
    fourp_result = asa.fourp_analysis("比亚迪")
    print(f"   成功: {fourp_result.get('success')}")

    print("✅ automotive_strategy_analysis 正常")
except Exception as e:
    print(f"❌ automotive_strategy_analysis 失败: {e}")
    import traceback
    traceback.print_exc()

# ========================================
# Step 7: 报告生成
# ========================================
print("\n【Step 7】报告生成 - report_generator")
print("-" * 40)
try:
    rpg = import_skill("report-generator", "report_generator.py")

    pest_r = asa.pest_analysis()
    porter_r = asa.porter_analysis()
    swot_r = asa.swot_analysis("比亚迪")

    result = rpg.generate_report(
        question="分析比亚迪的市场战略",
        intent_type="综合分析",
        pest_result=pest_r,
        porter_result=porter_r,
        swot_result=swot_r
    )

    print(f"成功: {result.get('success')}")
    if result.get('success'):
        markdown = result.get('markdown', '')
        print(f"报告长度: {len(markdown)} 字符")
        print(f"\n报告预览（前300字符）:\n{markdown[:300]}...")
    print("✅ report_generator 正常")
except Exception as e:
    print(f"❌ report_generator 失败: {e}")
    import traceback
    traceback.print_exc()

# ========================================
# 完整工作流测试
# ========================================
print("\n" + "=" * 60)
print("完整工作流测试")
print("=" * 60)

try:
    from car_analysis_workflow import run_analysis

    result = run_analysis("分析比亚迪的市场战略", verbose=False)

    if result.get('success'):
        print("✅ 完整工作流执行成功!")
        print(f"意图: {result['intent']['intent_type']}")
        print(f"置信度: {result['intent']['confidence']}")
        print(f"Hybrid RAG: {result['hybrid']['rag_available']}")
        print(f"数据源: {result['hybrid']['data_source']}")
        print(f"耗时: {result['elapsed_seconds']:.2f}秒")
    else:
        print(f"❌ 工作流失败: {result.get('error')}")
except Exception as e:
    print(f"❌ 完整工作流失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
