"""Compatibility import; use tiny_experts.components.wildlife_reference."""
import sys
from ..components import wildlife_reference as _implementation
sys.modules[__name__] = _implementation
