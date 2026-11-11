"""Read-only ExpertOS source capability catalog. No neural models are loaded."""
import json
from collections import Counter
from pathlib import Path
PATH=Path(__file__).resolve().parent/"data"/"expert_registry.json"
def load_catalog():
    c=json.loads(PATH.read_text(encoding="utf-8"))
    if c.get("schema_version") not in {"1.0.0", "1.1.0"}: raise ValueError("Unknown registry schema")
    ids=[e.get("id") for e in c.get("entries",[])]
    if len(ids)!=len(set(ids)): raise ValueError("Duplicate catalog IDs")
    if dict(Counter(e["kind"] for e in c["entries"])) != c["counts"]:
        raise ValueError("Catalog counts do not match entries")
    return c
def available_core(registered_keys):
    keys=set(registered_keys)
    return [e for e in load_catalog()["entries"] if e["kind"] in {"component", "expert"} and e["lifecycle"]=="registered_in_main" and e["route_key"] in keys]
def search(text,kind=None,include_planned=False):
    kind = {"expert": "component", "task_specialist": "task_component"}.get(kind, kind)
    q=text.casefold()
    return [e for e in load_catalog()["entries"] if (not kind or e["kind"]==kind) and (include_planned or e["kind"]!="planned") and q in (e["id"]+" "+e["name"]+" "+e["category"]+" "+e["description"]).casefold()]

def describe_components(components):
    """Runtime identities distinguish adapters from available learned models."""
    result = []
    for key, component in components.items():
        uses_model = bool(getattr(component, "uses_neural_model", False))
        classifier = getattr(component, "classifier", None)
        available = bool(getattr(classifier, "available", getattr(classifier, "is_trained", False)))
        available = available or bool(getattr(component, "vision_bundles", {}))
        result.append({"route_key": key, "name": component.name,
                       "component_type": component.component_kind,
                       "uses_neural_model": uses_model,
                       "neural_model_available": available if uses_model else False,
                       "updates_parameters_at_inference": False})
    return result
