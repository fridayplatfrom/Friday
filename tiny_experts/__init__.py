"""
Tiny Expert AI System
Local reference lookups, neural adapters and numerical/symbolic tools.
"""

__all__ = ["ComponentOrchestrator", "TinyExpertOrchestrator", "CapabilityRouter", "RouterModel"]


def __getattr__(name):
    """Keep training and small utilities independent of the full runtime."""
    if name in {"ComponentOrchestrator", "TinyExpertOrchestrator"}:
        from .orchestrator import ComponentOrchestrator
        return ComponentOrchestrator
    if name in {"CapabilityRouter", "RouterModel"}:
        from .router import CapabilityRouter
        return CapabilityRouter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
