"""Compatibility import; use tiny_experts.components.biography_lookup."""
import sys
from ..components import biography_lookup as _implementation
sys.modules[__name__] = _implementation
