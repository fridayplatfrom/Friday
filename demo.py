"""Small deterministic demonstration; no external requests or model downloads."""
import sys
from tiny_experts import ComponentOrchestrator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_scenarios():
    app = ComponentOrchestrator()
    queries = [
        "12 + 8",
        "mass=500 g acceleration=2",
        "r=100 ohm c=1 F",
        "Explain CRISPR gene editing.",
        "Explain Early Blight.",
        "The lab ruled out Fusarium wilt. My plant is healthy.",
        "Can I eat these unidentified wild berries?",
        "Correct this sentence: He go to school yesterday.",
    ]
    for index, query in enumerate(queries):
        print(f"\nQuestion: {query}")
        print(app.process(query, session_id=f"demo-{index}"))

    print("\n" + "=" * 72)
    print("  7-CORE UNIVERSAL SYSTEM LIVE DEMONSTRATION")
    print("=" * 72)
    universal_demos = [
        ("Core 2+4 (Physics Hierarchy + Unseen Reverse Numerical)",
         "A body of mass = 2 kg has kinetic energy = 100 J. Find the velocity.", {}),
        ("Core 4 (2-Hop Physics Chaining: Ramp Height -> PE -> Spring Compression)",
         "A 2 kg block slides down a 5 m high ramp into a spring with spring constant 400 N/m. How far does the spring compress?", {}),
        ("Core 5 (GST Return Workflow & Human Commit Gate)",
         "Prepare GSTR-3B return workflow",
         {"workflow_payload": {
             "supplier_gstin": "27AABCU9603R1ZM",
             "return_period": "2026-10",
             "invoices": [{"invoice_no": "INV-101", "buyer_gstin": "27BBBCU1234R1Z5", "taxable_value": 10000.0, "gst_rate": 18.0}],
             "itc_available": 500.0,
         }}),
        ("Core 6A (Excel Spreadsheet with Live =SUM Formulas)",
         "Build an Excel spreadsheet for GST invoices", {}),
        ("Core 6B (AST-Verified & Unit-Tested Python Code Synthesis)",
         "Write Python code for kinetic energy physics calculation", {}),
        ("Core 6C (Tone-Aware GST Notice Reply Email Composer)",
         "Draft a GST notice reply email regarding ITC reconciliation",
         {"workflow_payload": {"key_facts": ["Reconciled INR 1,800 in GSTR-2B"]}}),
        ("Core 2+7 (History/Politics + Dialectical Arbitration + Temporal Fact Clock)",
         "How does the Basic Structure doctrine limit Article 368 constitutional amendment power?",
         {"workflow_payload": {"entity_key": "gst_rate_solar_cells"}, "as_of": "2020-05-01"}),
    ]
    for title, u_query, kwargs in universal_demos:
        out = app.dispatch_universal_core(u_query, **kwargs)
        print(f"\n[{title}]")
        print(f"  Query : {u_query}")
        print(f"  Core  : {out.get('core')} | Domain: {out.get('domain')}")
        if out.get("domain") == "physics":
            res = out["result"]
            num = res.get("numerical_solution") or {}
            print(f"  Field : {res.get('specialist_expert_id')} (Concept: {res.get('concept_prediction')})")
            print(f"  Solve : {num.get('target_variable')} = {num.get('final_value')} {num.get('unit', '')} (mode={num.get('mode')})")
        elif out.get("domain") == "gst_and_software_control":
            res = out["result"]
            print(f"  GSTIN : {res['supplier_gstin']} | Net Cash Payable: INR {res['net_cash_payable']} | Human Commit Gate: {res['requires_human_commit_gate']}")
        elif out.get("domain") == "excel_form_generation":
            res = out["result"]
            print(f"  Sheet : {res['sheet_title']} ({res['row_count']} rows) | Totals: {res['evaluated_totals']}")
        elif out.get("domain") == "coding_expert":
            res = out["result"]
            print(f"  Topic : {out.get('topic_prediction')} | Function: {res['function_name']} | Unit Test Passed: {res['verification']['test_passed']}")
        elif out.get("domain") == "mail_and_chat_composer":
            res = out["result"]
            print(f"  Subj  : {res['subject']} | Tone: {res['tone']}")
        elif out.get("domain") == "history_and_politics":
            print(f"  Topic : {out.get('topic_prediction')} | Dialectical Conflict: {out['contradiction_analysis']['has_contradiction']}")
            print(f"  Clock : {out['temporal_facts']['active_facts'][0]['claim']} (as_of=2020-05-01)")


if __name__ == "__main__":
    run_scenarios()
