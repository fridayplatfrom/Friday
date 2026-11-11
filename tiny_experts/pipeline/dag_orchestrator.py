import graphlib
from typing import List, Dict, Any, Set

class TopologicalDAGOrchestrator:
    """
    Deterministic ordering of active experts and their active prerequisites.

    This helper orders names only. The caller owns execution, context transfer,
    and failure handling. Inactive prerequisites are not automatically run.
    """

    # Static Expert Dependency Declarations
    # key: expert_name, value: set of prerequisite expert_names that must run before it (if active)
    DEPENDENCIES: Dict[str, Set[str]] = {
        "vision": set(),
        "math": {"botany"},
        "biographer": set(),
        "botany": {"vision"},
        "wildlife": {"vision"},
        "entomology": {"vision"},
        "ornithology": {"vision"},
        "mycology": {"vision", "botany"},
        "pathology": {"vision", "botany"},
        "marine": {"vision"},
        "microbiology": {"vision", "pathology"},
        "cell_biology": {"genetics", "botany"},
        "genetics": set(),
        "evolution": {"genetics", "wildlife"},
        "ecology": {"botany", "wildlife", "pathology"},
        "thermodynamics": {"math", "botany"},
        "electronics": {"math"},
        "mechanics": {"math"},
        "toxicity": {"botany", "pathology", "wildlife"},
        "librarian": set(),
        "review": {"librarian", "pathology", "thermodynamics", "electronics", "mechanics"},
        "communicator": {
            "pathology", "botany", "toxicity", "wildlife", "entomology",
            "librarian", "biographer", "review", "thermodynamics", "electronics", "mechanics"
        },
        "format": {"communicator"}
    }

    @classmethod
    def compute_execution_order(cls, active_experts: List[str]) -> List[str]:
        """
        Takes an unordered list of active micro-experts and computes the
        strict topological dependency order using graphlib.TopologicalSorter.
        """
        active_set = set(active_experts)
        if not active_set:
            return []

        # Build sub-graph containing only the currently active experts
        graph: Dict[str, Set[str]] = {}
        for exp in sorted(active_set):
            prereqs = cls.DEPENDENCIES.get(exp, set())
            # Only retain prerequisites that are actually in the active squad
            active_prereqs = prereqs.intersection(active_set)
            graph[exp] = tuple(sorted(active_prereqs))

        try:
            ts = graphlib.TopologicalSorter(graph)
            ordered = list(ts.static_order())
            return ordered
        except graphlib.CycleError as exc:
            raise ValueError("Expert dependency cycle; execution order is undefined.") from exc
