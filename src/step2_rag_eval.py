"""Step 2: RAG Grounding Evaluation over 52 Practice Questions.

Evaluates the RAG pipeline against practice/questions.csv:
- Checks answer accuracy via must_include and must_not_include.
- Measures retrieval accuracy against gold_evidence section IDs.
- Quantifies performance improvement over the Step 1 baseline.
"""
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .config import PRACTICE_DIR, PROJECT_ROOT
from .rag import answer_with_rag, get_retriever
from .step1_baseline import evaluate_response


def evaluate_retrieval(retrieved_chunks: List[str], gold_evidence: str) -> bool:
    """Check if at least one of the gold evidence section IDs was retrieved."""
    if not gold_evidence or not gold_evidence.strip():
        return True  # Unsupported question, no evidence expected
    
    expected_ids = [e.strip() for e in gold_evidence.split(" ; ") if e.strip()]
    return any(eid in retrieved_chunks for eid in expected_ids)


def run_step2_evaluation(limit: int = None) -> Dict:
    """Run Step 2 RAG evaluation across practice/questions.csv."""
    print("=== Initializing Knowledge Base & Vector Index ===", flush=True)
    retriever = get_retriever()
    
    questions_file = PRACTICE_DIR / "questions.csv"
    with open(questions_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        
    if limit:
        reader = reader[:limit]
        
    total = len(reader)
    passed_count = 0
    retrieval_hit_count = 0
    results = []
    
    print(f"\n=== Starting Step 2 RAG Grounded Evaluation ({total} questions) ===", flush=True)
    
    for idx, row in enumerate(reader, 1):
        qid = row["id"]
        q_text = row["question"]
        must_inc = row.get("must_include", "")
        must_not_inc = row.get("must_not_include", "")
        gold_ev = row.get("gold_evidence", "")
        
        # Grounded RAG turn
        rag_output = answer_with_rag(q_text, top_k=4)
        response = rag_output["response"]
        retrieved = rag_output["retrieved_chunks"]
        used_sections = rag_output["used_section_ids"]
        
        # Check answer correctness
        passed, reason = evaluate_response(response, must_inc, must_not_inc)
        if passed:
            passed_count += 1
            status = "PASS"
        else:
            status = f"FAIL ({reason})"
            
        # Check retrieval hit
        retrieval_ok = evaluate_retrieval(retrieved, gold_ev)
        if retrieval_ok:
            retrieval_hit_count += 1
            
        results.append({
            "id": qid,
            "question": q_text,
            "response": response,
            "must_include": must_inc,
            "must_not_include": must_not_inc,
            "gold_evidence": gold_ev,
            "retrieved_chunks": retrieved,
            "used_sections": used_sections,
            "retrieval_hit": retrieval_ok,
            "passed": passed,
            "evaluation_note": reason
        })
        
        print(f"[{idx}/{total}] {qid} -> {status} (Retrieval: {'HIT' if retrieval_ok else 'MISS'})", flush=True)
        time.sleep(3.5)  # Pace requests within RPM limits
        
    ans_score = (passed_count / total) * 100 if total > 0 else 0
    ret_score = (retrieval_hit_count / total) * 100 if total > 0 else 0
    
    print("\n" + "=" * 55)
    print(f"Step 2 Grounded RAG Score: {passed_count}/{total} ({ans_score:.2f}%)")
    print(f"Step 2 Retrieval Hit Rate: {retrieval_hit_count}/{total} ({ret_score:.2f}%)")
    print("=" * 55)
    
    output_dir = PROJECT_ROOT / "sample_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "step2_rag_results.json"
    
    summary = {
        "step": 2,
        "total_questions": total,
        "passed": passed_count,
        "accuracy_pct": round(ans_score, 2),
        "retrieval_hits": retrieval_hit_count,
        "retrieval_hit_pct": round(ret_score, 2),
        "results": results
    }
    
    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(summary, out, indent=2, ensure_ascii=False)
        
    print(f"Results saved to: {output_file}")
    return summary


if __name__ == "__main__":
    run_step2_evaluation()
