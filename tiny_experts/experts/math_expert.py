"""Compatibility import; use tiny_experts.components.math_calculator."""
import sys
from ..components import math_calculator as _implementation
sys.modules[__name__] = _implementation
