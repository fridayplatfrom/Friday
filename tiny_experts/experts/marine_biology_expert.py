"""Compatibility import; use tiny_experts.components.marine_biology_reference."""
import sys
from ..components import marine_biology_reference as _implementation
sys.modules[__name__] = _implementation
