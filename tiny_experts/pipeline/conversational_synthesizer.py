from typing import Dict, Any, Optional

class ConversationalSynthesizer:
    """
    Conversational Human Persona Synthesizer (Bridge to CommunicatorExpert).
    Translates dense multi-expert clinical telemetry (pathology, toxicity, botany, entomology)
    into warm, empathetic, clear, human-like dialogue grounded in agricultural extension pedagogy.
    """

    _expert_instance = None

    @classmethod
    def get_expert(cls):
        if cls._expert_instance is None:
            from ..experts.communicator_expert import CommunicatorExpert
            cls._expert_instance = CommunicatorExpert()
        return cls._expert_instance

    @classmethod
    def synthesize_narrative(cls, query: str, aggregated: Dict[str, Any]) -> str:
        """
        Synthesizes a friendly, human-like narrative delegating to CommunicatorExpert.
        """
        try:
            expert = cls.get_expert()
            res = expert.evaluate({"query": query, "aggregated_results": aggregated})
            return res.get("speech_synthesis", "")
        except Exception:
            return ""
