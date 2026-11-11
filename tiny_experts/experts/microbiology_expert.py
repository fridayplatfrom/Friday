"""Compatibility import; use tiny_experts.components.microbiology_reference."""
import sys
from ..components import microbiology_reference as _implementation
sys.modules[__name__] = _implementation
