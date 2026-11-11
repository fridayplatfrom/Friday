"""Compatibility import; use tiny_experts.components.output_formatter."""
import sys
from ..components import output_formatter as _implementation
sys.modules[__name__] = _implementation
