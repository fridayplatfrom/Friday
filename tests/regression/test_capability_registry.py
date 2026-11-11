from tiny_experts.capability_registry import load_catalog, available_core

def test_component_capability_atlas():
    c=load_catalog()
    assert c["counts"]["component"]==24
    assert c["counts"]["support_service"]==45
    assert c["counts"]["neural_model"]==5
    assert {x["route_key"] for x in available_core({"botany","math","unknown"})}=={"botany","math"}
