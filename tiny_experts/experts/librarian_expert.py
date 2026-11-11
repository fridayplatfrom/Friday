"""Compatibility import; use tiny_experts.components.book_catalog_lookup."""
import sys
from ..components import book_catalog_lookup as _implementation
sys.modules[__name__] = _implementation
