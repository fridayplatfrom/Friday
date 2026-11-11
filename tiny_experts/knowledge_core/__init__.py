"""ExpertOS shared knowledge and capability core, version 0.1.

Standard-library-only core; image/video and legacy-model adapters are optional.
"""
from .store import Store, CoreError, AccessDenied
from .knowledge import Knowledge
from .sources import Sources
from .training import Training
from .runtime import Runtime
from .adapters import Adapters, CoreBookView, HarnessCoreAdapter
from .media import Media


class KnowledgeCore(Knowledge, Sources, Training, Runtime, Adapters, Media, Store):
    """Single transactional API for connected registries and controlled execution."""


__all__ = ['KnowledgeCore','CoreError','AccessDenied','CoreBookView','HarnessCoreAdapter','CoreExpertSystem']


def __getattr__(name):
    if name == 'CoreExpertSystem':
        from .system import CoreExpertSystem
        return CoreExpertSystem
    raise AttributeError(name)
