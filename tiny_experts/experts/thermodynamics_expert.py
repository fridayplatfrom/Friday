"""Compatibility import; use tiny_experts.components.thermodynamics_calculator."""
import sys
from ..components import thermodynamics_calculator as _implementation
sys.modules[__name__] = _implementation
