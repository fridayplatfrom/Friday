"""Compatibility import; use tiny_experts.components.vision_classifier."""
import sys
from ..components import vision_classifier as _implementation
sys.modules[__name__] = _implementation
