"""Compatibility import; use tiny_experts.components.toxicity_reference."""
import sys
from ..components import toxicity_reference as _implementation
sys.modules[__name__] = _implementation
