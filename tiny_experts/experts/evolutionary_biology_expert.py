"""Compatibility import; use tiny_experts.components.evolution_reference."""
import sys
from ..components import evolution_reference as _implementation
sys.modules[__name__] = _implementation
