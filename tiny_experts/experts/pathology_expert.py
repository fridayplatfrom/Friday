"""Compatibility import; use tiny_experts.components.pathology_candidates."""
import sys
from ..components import pathology_candidates as _implementation
sys.modules[__name__] = _implementation
