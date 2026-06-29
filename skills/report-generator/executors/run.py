#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""executors/run.py - report-generator skill execution entry"""
import sys
import json
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "missing parameters", "usage": "python executors/run.py <question> <output_path>"}, ensure_ascii=False))
        return 1

    if sys.argv[1] == "--json":
        params = json.loads(sys.argv[2])
        question = params.get("question", "")
        out_path = params.get("output_path")
    else:
        question = sys.argv[1]
        out_path = sys.argv[2]

    try:
        from report_generator import generate_report
        result = generate_report(
            question=question,
            intent_type="strategy_report",
            market_data={},
            brand_result={},
            pest_result={},
            porter_result={},
            swot_result={},
            fourp_result={},
            vector_results=[],
            sql_results=[],
            sentiment_results=[],
            output_format="markdown",
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result.get("markdown", ""))
        print(json.dumps({
            "success": True,
            "question": question,
            "output_path": out_path,
            "markdown_length": len(result.get("markdown", "")),
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "question": question,
            "output_path": out_path,
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())