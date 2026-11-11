"""Compatibility import; use tiny_experts.components.mycology_reference."""
import sys
from ..components import mycology_reference as _implementation
sys.modules[__name__] = _implementation
