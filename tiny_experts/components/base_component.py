from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseComponent(ABC):
    """Shared evaluate(context) interface; no model or learning behavior."""
    name = 'Component'
    description = 'Shared evaluate(context) interface; no model or learning behavior.'
    component_kind = 'interface'
    uses_neural_model = False
    updates_parameters_at_inference = False

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input context and return the component's structured result."""
        pass


# Compatibility for existing integrations and model-training imports.
BaseExpert = BaseComponent
