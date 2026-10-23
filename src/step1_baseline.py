"""Step 1: Baseline Prompted LLM Evaluation (No Document Grounding).

This module implements the Week 1 & 2 baseline required by the capstone:
- Sets system prompt identifying as ZentroMart AI assistant.
- Evaluates against the 52 practice questions without access to internal docs.
- Checks must_include and must_not_include rules to establish the baseline score.
"""
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Fix Windows console encoding for Unicode (Hindi / Devanagari)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .config import PRACTICE_DIR, PROJECT_ROOT
from .llm import generate_text

BASELINE_SYSTEM_PROMPT = (
    "You are the customer support AI assistant for ZentroMart, an Indian online store "
    "selling groceries and electronics. In your response, introduce yourself as an AI assistant. "
    "Be helpful, polite, and concise. Note: Today's reference date is 20 October 2026."
)


def evaluate_response(response: str, must_include: str, must_not_include: str) -> Tuple[bool, str]:
    """Check whether a generated response satisfies must_include and must_not_include rules.

    - must_include items are separated by ' ; '. Within each item, alternatives are separated by ' / '.
      At least ONE alternative must match per condition. ALL conditions must pass.
    - must_not_include items are separated by ' ; '. NONE must be present in the response.
    """
    resp_lower = response.lower()
    
    # 1. Check must_not_include
    if must_not_include and must_not_include.strip():
        forbidden_list = [item.strip().lower() for item in must_not_include.split(" ; ") if item.strip()]
        for f in forbidden_list:
            if f in resp_lower:
                return False, f"Matched forbidden term: '{f}'"
    
    # 2. Check must_include
    if must_include and must_include.strip():
        conditions = [item.strip() for item in must_include.split(" ; ") if item.strip()]
        for cond in conditions:
            alts = [alt.strip().lower() for alt in cond.split(" / ") if alt.strip()]
            matched = any(alt in resp_lower for alt in alts)
            if not matched:
                return False, f"Missing required term: '{cond}'"
                
    return True, "Passed"


def run_step1_evaluation(limit: int = None) -> Dict:
    """Run Step 1 baseline evaluation on practice/questions.csv."""
    questions_file = PRACTICE_DIR / "questions.csv"
    if not questions_file.exists():
        raise FileNotFoundError(f"Questions file not found: {questions_file}")
        
    with open(questions_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        
    if limit:
        reader = reader[:limit]
        
    results = []
    passed_count = 0
    total = len(reader)
    
    print(f"=== Starting Step 1 Baseline Evaluation ({total} questions) ===")
    
    for idx, row in enumerate(reader, 1):
        qid = row["id"]
        q_text = row["question"]
        must_inc = row.get("must_include", "")
        must_not_inc = row.get("must_not_include", "")
        
        prompt = f"Customer asks: \"{q_text}\"\nPlease respond to the customer."
        response = generate_text(prompt, system_instruction=BASELINE_SYSTEM_PROMPT, temperature=0.0)
        
        passed, reason = evaluate_response(response, must_inc, must_not_inc)
        if passed:
            passed_count += 1
            status = "PASS"
        else:
            status = f"FAIL ({reason})"
            
        results.append({
            "id": qid,
            "question": q_text,
            "response": response,
            "must_include": must_inc,
            "must_not_include": must_not_inc,
            "passed": passed,
            "evaluation_note": reason
        })
        
        print(f"[{idx}/{total}] {qid} -> {status}", flush=True)
        time.sleep(3.5)
        
    score = (passed_count / total) * 100 if total > 0 else 0
    print("\n" + "=" * 50)
    print(f"Step 1 Baseline Score: {passed_count}/{total} ({score:.2f}%)")
    print("=" * 50)
    
    output_dir = PROJECT_ROOT / "sample_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "step1_baseline_results.json"
    
    summary = {
        "step": 1,
        "total_questions": total,
        "passed": passed_count,
        "accuracy_pct": round(score, 2),
        "results": results
    }
    
    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(summary, out, indent=2, ensure_ascii=False)
        
    print(f"Results saved to: {output_file}")
    return summary


if __name__ == "__main__":
    run_step1_evaluation()
