"""Compatibility import; use tiny_experts.components.neural_classification."""
import sys
from ..components import neural_classification as _implementation
sys.modules[__name__] = _implementation
