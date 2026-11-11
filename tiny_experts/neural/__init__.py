"""Neural components are loaded lazily; data preparation needs no PyTorch import."""

__all__ = ["DeepSeekMoERouterNet", "NeuralRouterNet", "NeuralMoERouter", "NeuralRoutingClassifier", "NeuralTextClassifier"]


def __getattr__(name):
    if name in {"DeepSeekMoERouterNet", "NeuralRouterNet", "NeuralMoERouter", "NeuralRoutingClassifier"}:
        from . import neural_router
        return getattr(neural_router, name)
    if name == "NeuralTextClassifier":
        from .text_expert import NeuralTextClassifier
        return NeuralTextClassifier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
