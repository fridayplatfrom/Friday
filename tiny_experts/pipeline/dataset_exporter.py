"""Export candidate instruction/response examples for independent review.

These records are not classifier labels and are not verified training data. No
model is trained by this module, and execution traces are not gold reasoning.
"""

import json
import os
import tempfile
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..orchestrator import TinyExpertOrchestrator


class ScientificDatasetExporter:
    """Capture programmatic expert responses without claiming factual approval."""

    DEFAULT_PROMPTS = [
        # Botany & Plant Care
        "What is Poison Ivy and how do I care for or avoid it?",
        "What are the light, watering, and soil requirements for Common Sunflower?",
        "How do tracheids and vessel elements transport water in vascular plants?",
        # Toxicology & Chemistry
        "Is Poison Ivy toxic to touch and what is its chemical agent?",
        "What is Deadly Nightshade and what toxin does it contain?",
        "What is the IUPAC name and molecular formula of Urushiol?",
        # Multi-Agent Debate Crossovers
        "Can monarch caterpillars feed on toxic milkweed and become poisonous to avian predators?",
        "What antioxidant enzymes protect corals under thermal stress in marine ecosystems?",
        "How do diazotrophic bacteria reduce atmospheric nitrogen in legume root nodules without oxygen damage?",
        "How do birds maintain oxygenation during extreme high-altitude flight?",
        # Clinical Drug Interactions & Pharmacology
        "My dog is taking aspirin. Is it safe for them to chew on willow bark?",
        "What is the cellular mechanism of action of atropine on muscarinic receptors?",
        "What is the lethal mechanism of amatoxins found in Amanita phalloides?",
        # Lookalike Disambiguation
        "Found a wild mushroom with white gills and a ring in the woods. Can I eat it?",
        "How do I tell Poison Ivy apart from Virginia Creeper?",
        "How can I differentiate Poison Hemlock from Queen Anne's Lace?",
        # Genetics & Cellular Bioenergetics
        "Explain CRISPR-Cas9 endonuclease and mRNA splicing in genetics.",
        "How does ATP synthase generate adenosine triphosphate in mitochondria?",
        # Microbiology & Evolutionary Cladistics
        "What is the role of bacteriophages in microbial lysis?",
        "Explain allopatric speciation and synapomorphies in evolutionary biology.",
        # Zoology & Ethology
        "Tell me about Red Panda and where does it live?",
        "How do animals navigate using geomagnetic inclinations and circadian clocks?",
        # Math & Planting Density
        "Calculate planting capacity for 200 square meters with spacing 0.5 meters."
    ]

    def __init__(self, orchestrator: Optional["TinyExpertOrchestrator"] = None):
        if orchestrator is None:
            from ..orchestrator import TinyExpertOrchestrator
            orchestrator = TinyExpertOrchestrator(verbose=False)
        self.orchestrator = orchestrator

    def generate_sft_dataset(self, output_format: str = "alpaca",
                             custom_prompts: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        output_format = output_format.lower()
        if output_format not in {"alpaca", "sharegpt"}:
            raise ValueError("output_format must be 'alpaca' or 'sharegpt'.")
        prompts = self.DEFAULT_PROMPTS if custom_prompts is None else custom_prompts
        if not all(isinstance(prompt, str) and prompt.strip() for prompt in prompts):
            raise ValueError("Every prompt must be non-empty text.")
        dataset = []
        run_id = uuid.uuid4().hex
        for index, prompt in enumerate(prompts):
            # Never inherit an active user's session or an earlier generated case.
            session_id = f"export_{run_id}_{index}"
            try:
                detailed = self.orchestrator.process_detailed(
                    query=prompt, show_thinking=False, output_format="card", session_id=session_id,
                )
            finally:
                reset = getattr(self.orchestrator, "reset_session", None)
                if callable(reset):
                    reset(session_id)
            rendered = detailed.get("rendered_card", "")
            metadata = {
                "active_experts": detailed.get("active_experts", []),
                "latency_ms": detailed.get("latency_ms"),
                "generation_method": "programmatic_expert_output",
                "review_status": "unreviewed",
                "evaluation_status": "not_evaluated",
                "verified_factual": False,
                "intended_use": "candidate_examples_for_independent_review",
            }
            if output_format == "sharegpt":
                entry = {
                    "id": f"sciexpert_{index + 1}",
                    "conversations": [
                        {"from": "human", "value": prompt},
                        {"from": "gpt", "value": rendered},
                    ],
                    "metadata": metadata,
                }
            else:
                entry = {"instruction": prompt, "input": "", "output": rendered, "metadata": metadata}
            dataset.append(entry)
        return dataset

    def export_to_jsonl(self, filepath: str, output_format: str = "alpaca",
                        custom_prompts: Optional[List[str]] = None) -> Dict[str, Any]:
        dataset = self.generate_sft_dataset(output_format, custom_prompts)
        directory = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(directory, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=directory, suffix=".tmp", encoding="utf-8", delete=False) as f:
                temporary_path = f.name
                for entry in dataset:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            os.replace(temporary_path, filepath)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
        return {
            "status": "success", "filepath": filepath, "format": output_format.lower(),
            "total_samples": len(dataset), "file_size_kb": round(os.path.getsize(filepath) / 1024, 2),
            "review_status": "unreviewed", "verified_factual": False,
        }
