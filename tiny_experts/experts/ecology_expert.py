"""Compatibility import; use tiny_experts.components.ecology_reference."""
import sys
from ..components import ecology_reference as _implementation
sys.modules[__name__] = _implementation
