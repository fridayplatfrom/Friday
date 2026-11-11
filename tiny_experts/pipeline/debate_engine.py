from typing import Any, Dict, List, Optional


class MultiAgentDebateEngine:
    """Inventory actual expert outputs and scoped checks without simulating debate."""

    @classmethod
    def evaluate_debate(cls, query: str, active_experts: List[str], aggregated_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        participants = []
        for name in sorted(set(active_experts)):
            output = aggregated_data.get(name)
            if (isinstance(output, dict) and output and not output.get("error")
                    and output.get("active") is not False and output.get("relevant") is not False):
                participants.append(name)
        if len(participants) < 2:
            return None
        critic = aggregated_data.get("critic_audit") or {}
        return {"pattern_id": "actual_output_inventory", "status": "OUTPUTS_COLLECTED",
                "consensus_score": None, "consensus_established": False,
                "squads_participating": participants, "round_1_proposition": {},
                "round_2_cross_examination": {}, "round_3_corroboration": None,
                "checks": critic.get("checks", []), "unresolved_issues": critic.get("issues", []),
                "final_consensus": "Outputs were collected from the listed experts. No independent debate, factual consensus or calibrated agreement score was established."}
