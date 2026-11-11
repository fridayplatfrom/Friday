"""Compatibility import; use tiny_experts.components.botany_reference."""
import sys
from ..components import botany_reference as _implementation
sys.modules[__name__] = _implementation
