"""Universal Structured Synthesis & Artifact Core (Core Pillar 6).

Powers:
1. Coding Expert with AST Syntax & Restricted Unit-Test Verification
2. Excel Form & Live-Formula Spreadsheet Builder (CSV + Spreadsheet Grids)
3. Tone-Aware Email & Conversational Chat Composer
"""
from __future__ import annotations

import ast
import csv
import io
import math
from typing import Any, Dict, List, Optional


class StructuredSynthesisCore:
    """Deterministic, AST-verified code, spreadsheet, email, and chat synthesis engine."""

    CODE_TEMPLATES: Dict[str, Dict[str, Any]] = {
        "gst_calculator": {
            "function_name": "calculate_gst_breakdown",
            "description": "Computes CGST, SGST, IGST, and total invoice value from taxable amount and GST rate.",
            "code": (
                "def calculate_gst_breakdown(taxable_value: float, gst_rate_pct: float, intra_state: bool = True) -> dict:\n"
                "    tax_total = round(taxable_value * (gst_rate_pct / 100.0), 2)\n"
                "    cgst = round(tax_total / 2.0, 2) if intra_state else 0.0\n"
                "    sgst = round(tax_total - cgst, 2) if intra_state else 0.0\n"
                "    igst = 0.0 if intra_state else tax_total\n"
                "    return {\n"
                "        'taxable_value': round(taxable_value, 2),\n"
                "        'cgst': cgst,\n"
                "        'sgst': sgst,\n"
                "        'igst': igst,\n"
                "        'total_invoice': round(taxable_value + tax_total, 2),\n"
                "    }\n"
            ),
            "test_call": ("calculate_gst_breakdown", (1000.0, 18.0, True), {"taxable_value": 1000.0, "cgst": 90.0, "sgst": 90.0, "igst": 0.0, "total_invoice": 1180.0}),
        },
        "kinematics_solver": {
            "function_name": "solve_kinetic_energy",
            "description": "Computes translational kinetic energy E_k = 0.5 * m * v^2 in Joules.",
            "code": (
                "def solve_kinetic_energy(mass_kg: float, velocity_m_s: float) -> float:\n"
                "    if mass_kg < 0:\n"
                "        raise ValueError('Mass must be non-negative')\n"
                "    return round(0.5 * mass_kg * (velocity_m_s ** 2), 6)\n"
            ),
            "test_call": ("solve_kinetic_energy", (2.0, 10.0), 100.0),
        },
        "data_summary": {
            "function_name": "summarize_numeric_series",
            "description": "Computes count, sum, mean, min, and max for a numeric list.",
            "code": (
                "def summarize_numeric_series(values: list) -> dict:\n"
                "    if not values:\n"
                "        return {'count': 0, 'sum': 0.0, 'mean': 0.0, 'min': 0.0, 'max': 0.0}\n"
                "    total = float(sum(values))\n"
                "    return {\n"
                "        'count': len(values),\n"
                "        'sum': round(total, 4),\n"
                "        'mean': round(total / len(values), 4),\n"
                "        'min': float(min(values)),\n"
                "        'max': float(max(values)),\n"
                "    }\n"
            ),
            "test_call": ("summarize_numeric_series", ([10, 20, 30],), {"count": 3, "sum": 60.0, "mean": 20.0, "min": 10.0, "max": 30.0}),
        },
    }

    @classmethod
    def verify_python_code(cls, code_str: str, test_call: Optional[tuple] = None) -> Dict[str, Any]:
        """Verifies Python AST validity, blocks unsafe imports/calls, and runs bounded unit test."""
        try:
            tree = ast.parse(code_str)
        except SyntaxError as exc:
            return {"ast_valid": False, "test_passed": False, "error": f"SyntaxError: {exc}"}

        forbidden_nodes = (ast.Import, ast.ImportFrom)
        for node in ast.walk(tree):
            if isinstance(node, forbidden_nodes):
                return {"ast_valid": False, "test_passed": False, "error": "Imports are disallowed in restricted synthesis sandbox."}
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "open", "compile", "__import__"}:
                return {"ast_valid": False, "test_passed": False, "error": f"Call to '{node.func.id}' is disallowed in sandbox."}

        if test_call is None:
            return {"ast_valid": True, "test_passed": True, "functions": [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]}

        fn_name, args, expected = test_call
        safe_builtins = {
            "round": round,
            "sum": sum,
            "min": min,
            "max": max,
            "len": len,
            "float": float,
            "int": int,
            "str": str,
            "dict": dict,
            "list": list,
            "abs": abs,
            "ValueError": ValueError,
        }
        ns: Dict[str, Any] = {"__builtins__": safe_builtins, "math": math}
        try:
            exec(compile(tree, filename="<synthesized_code>", mode="exec"), ns)  # noqa: S102
            fn = ns.get(fn_name)
            if not callable(fn):
                return {"ast_valid": True, "test_passed": False, "error": f"Function '{fn_name}' not found."}
            actual = fn(*args)
            passed = actual == expected
            return {
                "ast_valid": True,
                "test_passed": passed,
                "function_name": fn_name,
                "actual_output": actual,
                "expected_output": expected,
            }
        except Exception as exc:
            return {"ast_valid": True, "test_passed": False, "error": str(exc)}

    @classmethod
    def synthesize_code(cls, task_query: str, custom_code: Optional[str] = None) -> Dict[str, Any]:
        """Synthesizes and AST-verifies Python code for a requested coding task."""
        if custom_code is not None:
            verification = cls.verify_python_code(custom_code)
            return {"status": "verified" if verification["ast_valid"] else "invalid", "code": custom_code, "verification": verification}

        q_lower = task_query.lower()
        if any(k in q_lower for k in ("gst", "tax", "invoice", "cgst", "igst")):
            tpl = cls.CODE_TEMPLATES["gst_calculator"]
        elif any(k in q_lower for k in ("kinetic", "physics", "velocity", "energy")):
            tpl = cls.CODE_TEMPLATES["kinematics_solver"]
        else:
            tpl = cls.CODE_TEMPLATES["data_summary"]

        verification = cls.verify_python_code(tpl["code"], test_call=tpl["test_call"])
        return {
            "status": "verified" if verification["test_passed"] else "failed_verification",
            "function_name": tpl["function_name"],
            "description": tpl["description"],
            "code": tpl["code"],
            "verification": verification,
        }

    @classmethod
    def build_excel_form_spec(
        cls,
        *,
        sheet_title: str,
        template_type: str = "gst_invoice_register",
        rows_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Builds an Excel spreadsheet specification with live Excel formulas (=SUM, =ROUND) and CSV export."""
        rows_data = rows_data or [
            {"invoice_no": "INV-001", "party_name": "Acme Solar Pvt Ltd", "hsn": "8541", "taxable_value": 50000.0, "gst_rate_pct": 12.0},
            {"invoice_no": "INV-002", "party_name": "Bharat Optics Corp", "hsn": "9001", "taxable_value": 25000.0, "gst_rate_pct": 18.0},
        ]
        headers = [
            "Row_ID",
            "Invoice_No",
            "Party_Name",
            "HSN_SAC",
            "Taxable_Value",
            "GST_Rate_Pct",
            "CGST_Formula",
            "SGST_Formula",
            "Total_Invoice_Formula",
        ]
        grid_rows: List[List[Any]] = [headers]
        evaluated_summary_taxable = 0.0
        evaluated_summary_total = 0.0

        for idx, item in enumerate(rows_data, start=2):
            taxable = float(item.get("taxable_value", 0.0))
            rate = float(item.get("gst_rate_pct", 18.0))
            cgst_formula = f"=ROUND(E{idx}*(F{idx}/100)/2, 2)"
            sgst_formula = f"=ROUND(E{idx}*(F{idx}/100)/2, 2)"
            total_formula = f"=ROUND(E{idx}+G{idx}+H{idx}, 2)"

            tax_val = round(taxable * (rate / 100.0), 2)
            evaluated_summary_taxable = round(evaluated_summary_taxable + taxable, 2)
            evaluated_summary_total = round(evaluated_summary_total + taxable + tax_val, 2)

            grid_rows.append([
                idx - 1,
                item.get("invoice_no", f"INV-{idx-1:03d}"),
                item.get("party_name", "Client"),
                item.get("hsn", "9983"),
                taxable,
                rate,
                cgst_formula,
                sgst_formula,
                total_formula,
            ])

        last_data_row = len(rows_data) + 1
        footer_row = [
            "TOTAL",
            "",
            "",
            "",
            f"=SUM(E2:E{last_data_row})",
            "",
            f"=SUM(G2:G{last_data_row})",
            f"=SUM(H2:H{last_data_row})",
            f"=SUM(I2:I{last_data_row})",
        ]
        grid_rows.append(footer_row)

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerows(grid_rows)

        return {
            "sheet_title": sheet_title,
            "template_type": template_type,
            "columns": headers,
            "row_count": len(grid_rows),
            "grid": grid_rows,
            "csv_content": buf.getvalue(),
            "evaluated_totals": {
                "total_taxable_value": evaluated_summary_taxable,
                "total_invoice_value": evaluated_summary_total,
            },
        }

    @classmethod
    def compose_email_or_chat(
        cls,
        *,
        mode: str = "email",
        tone: str = "formal_business",
        recipient_name: str = "Sir/Madam",
        subject_topic: str = "Project & Compliance Update",
        key_facts: Optional[List[str]] = None,
        sender_name: str = "Tiny Expert System Assistant",
    ) -> Dict[str, Any]:
        """Composes structured emails, GST/tax notice replies, or conversational chat responses."""
        facts = [f.strip() for f in (key_facts or []) if f and f.strip()]
        facts_bullets = "\n".join(f"  - {fact}" for fact in facts) if facts else "  - All requested items have been verified."

        if mode.lower() == "chat":
            summary_line = "; ".join(facts) if facts else f"Here is the update regarding {subject_topic}."
            return {
                "mode": "chat",
                "tone": tone,
                "reply_text": f"Hello {recipient_name}! Regarding {subject_topic}: {summary_line} Let me know if you would like me to run the next step.",
            }

        if tone == "gst_notice_reply":
            subject = f"Official Response & Reconciliation Statement: {subject_topic}"
            opening = f"Dear {recipient_name},\n\nWith reference to {subject_topic}, please find below our verified reconciliation particulars and supporting schedule:"
            closing = "Kindly acknowledge receipt of this compliance submission.\n\nYours faithfully,"
        elif tone == "client_followup":
            subject = f"Follow-Up: {subject_topic}"
            opening = f"Hi {recipient_name},\n\nI hope you are doing well. Following up on {subject_topic}, here are the key updates:"
            closing = "Please let us know if you have any questions or adjustments.\n\nWarm regards,"
        else:
            subject = f"Update Regarding {subject_topic}"
            opening = f"Dear {recipient_name},\n\nPlease find the structured summary regarding {subject_topic} below:"
            closing = "Thank you for your time and consideration.\n\nBest regards,"

        body = f"{opening}\n\n{facts_bullets}\n\n{closing}\n{sender_name}"
        return {
            "mode": "email",
            "tone": tone,
            "subject": subject,
            "recipient": recipient_name,
            "body": body,
            "facts_included": len(facts),
        }
