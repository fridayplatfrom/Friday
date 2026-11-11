"""Connect a bounded trained classifier and a source shelf to the local mesh."""
from .base_component import BaseComponent
from ..neural.text_expert import NeuralTextClassifier


class NeuralClassificationAdapter(BaseComponent):
    """Runs a packaged neural text classifier, retrieves passages and optionally calls a symbolic calculator."""
    name = 'Neural Classification and Retrieval Adapter'
    description = 'Runs a packaged neural text classifier, retrieves passages and optionally calls a symbolic calculator.'
    component_kind = 'hybrid_adapter'
    uses_neural_model = True
    updates_parameters_at_inference = False
    def __init__(self, expert_id, bundle_dir, book_engine, shelf, *, allow_experimental=False):
        super().__init__(name=f"Neural Classification Adapter ({expert_id})", description="Supervised classification with original-query source retrieval.")
        book_engine.validate_shelf(shelf)
        self.shelf = shelf
        self.book_engine = book_engine
        self.classifier = NeuralTextClassifier(bundle_dir, expected_expert_id=expert_id,
                                              allow_experimental=allow_experimental)

    def evaluate(self, context):
        query = str(context.get("query") or "")
        result = self.classifier.predict(query)
        # Retrieve the actual observations, never a guessed label injected as evidence.
        citations = self.book_engine.search(query=query, shelf=self.shelf, top_k=3)
        predictions = result.get("predictions", {})
        preferred_subdomain = None
        if "subdomain" in predictions and isinstance(predictions["subdomain"], dict):
            preferred_subdomain = predictions["subdomain"].get("label")
        elif "topic" in predictions and isinstance(predictions["topic"], dict):
            preferred_subdomain = predictions["topic"].get("label")

        numerical_solution = None
        if any(ch.isdigit() for ch in query):
            from ..pipeline.cas_engine import SymbolicCASEngine
            solved = SymbolicCASEngine.solve_numerical_word_problem(
                query,
                preferred_subdomain=preferred_subdomain,
            )
            if solved.get("solved") or solved.get("status") == "physical_sanity_violation":
                numerical_solution = solved

        response = {
            "relevant": True,
            "status": "abstained" if (result["abstained"] and not numerical_solution) else "candidate",
            "message": result.get("reason") or "Classification candidate; sources require a separate support check.",
            "model_available": result["available"],
            "model_predictions": predictions,
            "score_type": "uncalibrated_softmax",
            "textbook_citations": citations,
            "claims_verified": False,
        }
        if numerical_solution is not None:
            response["numerical_calculation"] = numerical_solution
            response["calculations"] = numerical_solution
        return response


# Compatibility for existing integrations and model-training imports.
NeuralReferenceExpert = NeuralClassificationAdapter
