"""Conservative deterministic browser specialists and optional source retrieval.

These are rule-based expert *baselines*, not trained neural networks. Any optional
neural policy must be independently evaluated before it can propose actions.
"""
from __future__ import annotations
import re
from typing import Any
from urllib.parse import urlsplit

# Accessible labels matter more than raw CSS; retain no secret values in logs.
SYNONYMS = {
    "company": {"organization", "organisation", "business", "firm"},
    "name": {"full name", "contact name"},
    "email": {"e-mail", "email address", "work email"},
    "phone": {"mobile", "telephone", "contact number"},
    "address": {"street address", "office address"},
    "postal": {"zip", "pin", "postcode", "pincode"},
    "website": {"url", "homepage"},
    "invoice": {"invoice number", "invoice no", "bill number"},
    "hsn": {"hsn code", "sac code", "hsn sac"},
    "taxable": {"taxable value", "taxable amount", "base amount"},
}
ACTION_TYPES = {"navigate", "extract", "fill_form"}
ALLOWED_TYPES = {"text", "textarea", "search", "email", "tel", "url", "number", "select"}
SENSITIVE = re.compile(r"(?i)(password|passcode|otp|verification code|cvv|card number|credit card|bank account|upi pin|captcha|tax id|aadhaar|social security)")


def norm(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def tokens(s: Any) -> set[str]:
    return {x for x in norm(s).split() if x not in {"the", "your", "enter", "please", "field", "required", "input"}}


def expand(name: str) -> set[str]:
    words = tokens(name)
    candidates = {norm(name), " ".join(sorted(words))}
    for left, aliases in SYNONYMS.items():
        if left in words:
            candidates |= {norm(s) for s in aliases}
        if norm(name) in {norm(a) for a in aliases}:
            candidates.add(left)
    return {c for c in candidates if c}


def controls_map(data: dict[str, Any]) -> dict[str, Any]:
    """Map user values to observed controls; abstain on ambiguity/sensitivity."""
    fields, values = data.get("controls"), data.get("values")
    if not isinstance(fields, list) or len(fields) > 200 or not isinstance(values, dict) or len(values) > 100:
        return {"status": "invalid_input", "matches": [], "unmatched": [], "reason": "Expected bounded controls and values"}
    matches: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    claimed: set[int] = set()
    for source_key, value in values.items():
        if not isinstance(source_key, str) or len(source_key) > 100 or not isinstance(value, str) or len(value) > 1000:
            unmatched.append({"key": str(source_key)[:100], "reason": "invalid_value"})
            continue
        if SENSITIVE.search(source_key):
            unmatched.append({"key": source_key, "reason": "sensitive_field_requires_manual_entry"})
            continue
        possible = []
        for field in fields:
            if not isinstance(field, dict) or type(field.get("index")) is not int:
                continue
            idx = field["index"]
            if idx < 0 or idx >= 200 or idx in claimed or field.get("disabled") or not field.get("visible", False):
                continue
            kind = str(field.get("type") or "text").casefold()
            if kind not in ALLOWED_TYPES:
                continue
            desc = " ".join(str(field.get(k) or "")[:250] for k in ("label", "name", "placeholder", "id", "aria_label"))
            if SENSITIVE.search(desc):
                continue
            candidates = expand(source_key)
            field_tokens = tokens(desc)
            best = 0.0
            direct_tokens = tokens(source_key)
            if direct_tokens and direct_tokens <= field_tokens:
                best = 1.2  # Prefer exact field names over loose synonyms.
            for alias in candidates:
                key_tokens = tokens(alias)
                if not key_tokens:
                    continue
                overlap = len(key_tokens & field_tokens) / len(key_tokens)
                if alias and alias in norm(desc):
                    overlap = max(overlap, 1.0)
                if alias != norm(source_key):
                    overlap *= 0.9
                best = max(best, overlap)
            if best >= 0.8:
                possible.append((best, idx, field))
        possible.sort(key=lambda x: (-x[0], x[1]))
        if not possible:
            unmatched.append({"key": source_key, "reason": "no_unambiguous_control"})
            continue
        if len(possible) > 1 and possible[0][0] - possible[1][0] < 0.15:
            unmatched.append({"key": source_key, "reason": "ambiguous_control"})
            continue
        score, idx, field = possible[0]
        claimed.add(idx)
        matches.append({"key": source_key, "index": idx, "type": str(field.get("type") or "text"),
                        "identity": {key: field.get(key) for key in ("id", "name", "type", "label")},
                        "score": round(score, 3), "requires_approval": False})
    return {"status": "mapped" if matches else "abstained", "matches": matches,
            "unmatched": unmatched, "verified": False,
            "note": "Rule-based mapping. Caller must recheck control identity and value after each fill."}


def verify_values(data: dict[str, Any]) -> dict[str, Any]:
    """Pure comparison; never treat a write call alone as confirmed success."""
    expected, actual = data.get("expected"), data.get("actual")
    if not isinstance(expected, dict) or not isinstance(actual, dict) or len(expected) > 100:
        return {"status": "invalid_input", "verified": False, "mismatches": []}
    mismatches = []
    for key, target in expected.items():
        if not isinstance(target, str) or actual.get(key) != target:
            mismatches.append({"key": str(key)[:100], "reason": "value_missing_or_different"})
    return {"status": "verified" if not mismatches else "mismatch", "verified": not mismatches,
            "mismatches": mismatches, "total_checked": len(expected)}


def plan(data: dict[str, Any]) -> dict[str, Any]:
    kind = data.get("kind")
    url = data.get("url")
    if kind not in ACTION_TYPES or not isinstance(url, str) or len(url) > 2048:
        return {"status": "abstained", "actions": [], "reason": "Unrecognized bounded task"}
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        return {"status": "abstained", "actions": [], "reason": "Invalid URL"}
    actions = [{"type": "navigate", "url": url}]
    if kind == "extract":
        actions.append({"type": "extract", "scope": "visible_text", "max_chars": 8000})
    if kind == "fill_form":
        if not isinstance(data.get("values"), dict) or not data["values"]:
            return {"status": "abstained", "actions": [], "reason": "Missing form values"}
        actions.append({"type": "observe_controls"})
        actions.append({"type": "map_fields"})
        actions.append({"type": "fill_fields"})
        actions.append({"type": "verify_fields"})
    return {"status": "planned", "actions": actions, "auto_submit": False,
            "mode": "deterministic_baseline", "note": "Does not bypass authentication, submit, or approve commitments."}


def route(data: dict[str, Any]) -> dict[str, Any]:
    task = data.get("task", "")
    if not isinstance(task, str) or len(task) > 4000:
        return {"status": "invalid_input", "expert": None}
    wordset = tokens(task)
    if wordset & {"form", "fill", "input", "textbox"}:
        expert = "form_mapper"
    elif wordset & {"browser", "website", "navigate", "webpage", "click"}:
        expert = "browser_planner"
    elif wordset & {"book", "passage", "citation", "document", "chapter"}:
        expert = "source_reader"
    elif wordset & {"pathology", "disease", "blight", "leaf"}:
        expert = "pathology_reference"
    elif wordset & {"test", "verify", "validate", "check"}:
        expert = "verifier"
    else:
        expert = None
    return {"status": "routed" if expert else "abstained", "expert": expert,
            "model_type": "deterministic_baseline", "confidence": None}


def recovery(data: dict[str, Any]) -> dict[str, Any]:
    code = data.get("error_code")
    mapping = {
        "control_missing": "reobserve_and_remap",
        "control_changed": "reobserve_and_remap",
        "navigation_timeout": "stop_and_report",
        "verification_mismatch": "stop_and_report",
        "approval_required": "request_human_approval",
        "blocked_origin": "stop_and_report",
    }
    return {"status": "advice", "next_action": mapping.get(code, "stop_and_report"),
            "reason": "Bounded deterministic recovery only; no blind retries."}


def universal_dispatch(data: dict[str, Any]) -> dict[str, Any]:
    """Fast, bounded 7-Core dispatch (Coding, Excel, Mail, GST, Physics CAS) without loading heavy vision weights."""
    query = data.get("query", "")
    if not isinstance(query, str) or not query.strip() or len(query) > 4000:
        return {"status": "invalid_input", "result": None}
    q_lower = query.lower()
    payload = data.get("workflow_payload") if isinstance(data.get("workflow_payload"), dict) else {}

    from tiny_experts.pipeline.structured_synthesis import StructuredSynthesisCore
    if any(k in q_lower for k in ("excel", "spreadsheet", "csv", "invoice table", "workbook")):
        return {
            "status": "completed",
            "core": "core_6_structured_synthesis",
            "domain": "excel_form_generation",
            "result": StructuredSynthesisCore.build_excel_form_spec(
                sheet_title=str(payload.get("sheet_title", query[:60] or "Generated Sheet")),
                rows_data=payload.get("rows_data"),
            ),
        }
    if any(k in q_lower for k in ("write python", "python function", "def ", "code for", "coding", "algorithm")):
        return {
            "status": "completed",
            "core": "core_6_structured_synthesis",
            "domain": "coding_expert",
            "result": StructuredSynthesisCore.synthesize_code(task_query=query, custom_code=payload.get("custom_code")),
        }
    if any(k in q_lower for k in ("reply email", "draft email", "compose email", "formal mail", "gst notice reply")):
        return {
            "status": "completed",
            "core": "core_6_structured_synthesis",
            "domain": "mail_and_chat_composer",
            "result": StructuredSynthesisCore.compose_email_or_chat(
                mode=str(payload.get("mode", "email")),
                tone=str(payload.get("tone", "gst_notice_reply" if "gst" in q_lower else "formal_business")),
                recipient_name=str(payload.get("recipient_name", "Respected Officer")),
                subject_topic=str(payload.get("subject_topic", query[:80])),
                key_facts=list(payload.get("key_facts", [query])),
            ),
        }
    from tiny_experts.pipeline.cas_engine import SymbolicCASEngine
    return {
        "status": "completed",
        "core": "core_4_universal_formula_solver",
        "domain": "physics",
        "result": SymbolicCASEngine.solve_numerical_word_problem(query),
    }


EXPERTS = [
    {"id": "browser_planner", "kind": "deterministic", "ready": True},
    {"id": "form_mapper", "kind": "deterministic", "ready": True},
    {"id": "browser_verifier", "kind": "deterministic", "ready": True},
    {"id": "recovery", "kind": "deterministic", "ready": True},
    {"id": "router", "kind": "deterministic", "ready": True},
    {"id": "source_reader", "kind": "neural_optional", "ready": False},
    {"id": "pathology_reference", "kind": "neural_optional", "ready": False},
    {"id": "browser_action_policy", "kind": "neural_optional", "ready": False},
]
