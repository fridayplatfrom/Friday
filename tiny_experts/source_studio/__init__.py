"""ExpertOS Source Studio: operator-controlled upload, review and training queue.

Importing or indexing content never certifies it, trains a model, or deploys weights.
"""
from .director import TrainingDirector, MODES

__all__ = ["TrainingDirector", "MODES"]
