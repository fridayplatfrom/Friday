"""Compatibility import; use tiny_experts.components.genetics_reference."""
import sys
from ..components import genetics_reference as _implementation
sys.modules[__name__] = _implementation
