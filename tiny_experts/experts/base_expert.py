"""Compatibility import; use tiny_experts.components.base_component."""
import sys
from ..components import base_component as _implementation
sys.modules[__name__] = _implementation
