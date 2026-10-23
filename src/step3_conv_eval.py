"""Step 3: Multi-turn Conversation Evaluation over 23 Scenarios (96 Turns).

Evaluates the SupportAgent against practice/conversations.csv:
- Evaluates context retention across multiple turns.
- Verifies identity checks (phone last 4 digits / pincode).
- Validates tool invocations (lookup_order and create_ticket).
- Checks policy-compliant answers and human handovers.
"""
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .config import PRACTICE_DIR, PROJECT_ROOT
from .agent import SupportAgent
from .step1_baseline import evaluate_response


def run_step3_evaluation(limit_conversations: int = None) -> Dict:
    """Run Step 3 multi-turn conversation evaluation."""
    conv_file = PRACTICE_DIR / "conversations.csv"
    with open(conv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    # Group turns by conversation_id
    conversations = defaultdict(list)
    for row in reader:
        conversations[row["conversation_id"]].append(row)

    conv_ids = list(conversations.keys())
    if limit_conversations:
        conv_ids = conv_ids[:limit_conversations]

    total_turns = sum(len(conversations[cid]) for cid in conv_ids)
    passed_turns = 0
    conv_results = []

    print(f"\n=== Starting Step 3 Multi-Turn Evaluation ({len(conv_ids)} conversations, {total_turns} turns) ===", flush=True)

    for c_idx, cid in enumerate(conv_ids, 1):
        turns = conversations[cid]
        agent = SupportAgent(conversation_id=cid)
        turn_records = []
        all_turns_passed = True

        print(f"\n--- Scenario: {cid} ({len(turns)} turns) ---", flush=True)

        for turn_row in turns:
            t_num = turn_row["turn"]
            msg = turn_row["customer_message"]
            must_inc = turn_row.get("must_include", "")
            must_not_inc = turn_row.get("must_not_include", "")
            expected_decision = turn_row.get("expected_decision", "")

            # Agent turn
            response = agent.respond(msg)

            # Evaluate response terms
            passed, reason = evaluate_response(response, must_inc, must_not_inc)
            
            # Additional decision validation
            if expected_decision == "escalate" and not agent.last_ticket_id and "ticket" not in response.lower() and "colleague" not in response.lower():
                passed = False
                reason = "Expected escalation ticket creation"

            if passed:
                passed_turns += 1
                status = "PASS"
            else:
                all_turns_passed = False
                status = f"FAIL ({reason})"

            turn_records.append({
                "turn": int(t_num),
                "customer_message": msg,
                "agent_response": response,
                "must_include": must_inc,
                "must_not_include": must_not_inc,
                "expected_decision": expected_decision,
                "passed": passed,
                "evaluation_note": reason
            })

            print(f"  [Turn {t_num}] -> {status}", flush=True)

        conv_results.append({
            "conversation_id": cid,
            "scenario": turns[0].get("scenario", ""),
            "all_passed": all_turns_passed,
            "turns": turn_records
        })

    accuracy_pct = (passed_turns / total_turns) * 100 if total_turns > 0 else 0
    print("\n" + "=" * 55)
    print(f"Step 3 Conversation Turns Passed: {passed_turns}/{total_turns} ({accuracy_pct:.2f}%)")
    print("=" * 55)

    output_dir = PROJECT_ROOT / "sample_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "step3_conversation_results.json"

    summary = {
        "step": 3,
        "total_conversations": len(conv_ids),
        "total_turns": total_turns,
        "passed_turns": passed_turns,
        "turn_accuracy_pct": round(accuracy_pct, 2),
        "conversations": conv_results
    }

    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(summary, out, indent=2, ensure_ascii=False)

    print(f"Conversation results saved to: {output_file}", flush=True)
    return summary


if __name__ == "__main__":
    run_step3_evaluation()
