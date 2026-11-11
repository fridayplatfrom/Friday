"""Compatibility import; use tiny_experts.components.biology_reference."""
import sys
from ..components import biology_reference as _implementation
sys.modules[__name__] = _implementation
