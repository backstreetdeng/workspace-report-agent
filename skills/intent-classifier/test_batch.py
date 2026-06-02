# test_batch.py
import sys
sys.path.insert(0, ".")

from intent_classifier import IntentClassifier

classifier = IntentClassifier()

# 标准测试集（已知正确答案）
test_cases = [
    {
        "question": "10-15万紧凑型SUV未来发展趋势如何",
        "expected": "趋势分析"
    },
    {
        "question": "比亚迪在20-30万纯电SUV市场的竞品分析",
        "expected": "竞品分析"
    },
    {
        "question": "分析30-50万豪华SUV的用户画像",
        "expected": "画像分析"
    },
    {
        "question": "2025年新能源补贴退坡政策解读",
        "expected": "政策解读"
    },
    {
        "question": "15-20万插混车型有哪些市场机会",
        "expected": "机会识别"
    },
    {
        "question": "特斯拉Model Y的竞争优势",
        "expected": "竞品分析"
    },
    {
        "question": "纯电和插混哪个更值得买",
        "expected": "综合分析"  # 可能是画像或趋势
    },
    {
        "question": "现在买新能源车合适吗",
        "expected": "趋势分析"
    }
]

# 运行测试
print("=" * 70)
print("批量测试结果")
print("=" * 70)

correct = 0
for i, case in enumerate(test_cases, 1):
    result = classifier.classify(case["question"])
    is_correct = result.intent_type == case["expected"]
    status = "✅" if is_correct else "❌"
    
    if is_correct:
        correct += 1
    
    print(f"\n{status} 测试{i}：{case['question']}")
    print(f"   预期：{case['expected']}")
    print(f"   实际：{result.intent_type} (置信度：{result.confidence})")

print("\n" + "=" * 70)
print(f"准确率：{correct}/{len(test_cases)} = {correct/len(test_cases)*100:.1f}%")