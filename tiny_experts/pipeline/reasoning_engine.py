"""Render the recorded execution log; do not generate a simulated thinking trace."""
import json
from typing import Any, Dict, List, Optional


class ReasoningEngine:
    @classmethod
    def generate_thinking_trace(cls, query: str, resolved_species: Optional[str], autonomous_tool_called: bool,
                                active_experts: List[str], aggregated_data: Dict[str, Any]) -> str:
        """Keep the legacy interface while displaying only recorded events.

        Stage outcomes are not evidence of factual correctness. In particular,
        expert selection does not imply execution, and retrieval does not imply
        source validation.
        """
        steps = []
        for event in aggregated_data.get("execution_events", []):
            if not isinstance(event, dict) or not event.get("stage") or not event.get("status"):
                continue
            detail = event.get("detail", "")
            if isinstance(detail, (dict, list)):
                detail = json.dumps(detail, ensure_ascii=False, default=str)
            detail = str(detail).replace("\r", " ").replace("\n", " ")[:1200]
            stage = str(event["stage"]).replace("\n", " ")[:120]
            status = str(event["status"]).replace("\n", " ")[:80]
            steps.append(f"[{stage}: {status}] {detail}".rstrip())
        if not steps:
            return "Execution log unavailable: no completed stage events were recorded."
        return "Execution log (recorded stage outcomes; no global confidence score)\n" + "\n".join(steps)
