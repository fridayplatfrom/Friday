"""Compatibility import; use tiny_experts.components.entomology_reference."""
import sys
from ..components import entomology_reference as _implementation
sys.modules[__name__] = _implementation
