"""Compatibility import; use tiny_experts.components.cell_biology_reference."""
import sys
from ..components import cell_biology_reference as _implementation
sys.modules[__name__] = _implementation
