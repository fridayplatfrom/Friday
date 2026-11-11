"""Compatibility import; use tiny_experts.components.review_lookup."""
import sys
from ..components import review_lookup as _implementation
sys.modules[__name__] = _implementation
