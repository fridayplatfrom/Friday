"""Compatibility import; use tiny_experts.components.circuit_calculator."""
import sys
from ..components import circuit_calculator as _implementation
sys.modules[__name__] = _implementation
