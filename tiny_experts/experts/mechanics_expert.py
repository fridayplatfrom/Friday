"""Compatibility import; use tiny_experts.components.mechanics_calculator."""
import sys
from ..components import mechanics_calculator as _implementation
sys.modules[__name__] = _implementation
