"""Compatibility import; use dictionary_lookup.DictionaryLookupService."""
import sys
from . import dictionary_lookup as _implementation
sys.modules[__name__] = _implementation
