"""Compatibility import; use tiny_experts.components.result_renderer."""
import sys
from ..components import result_renderer as _implementation
sys.modules[__name__] = _implementation
