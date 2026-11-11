"""Compatibility import; use tiny_experts.components.ornithology_reference."""
import sys
from ..components import ornithology_reference as _implementation
sys.modules[__name__] = _implementation
