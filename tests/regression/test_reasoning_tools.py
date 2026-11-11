"""Regression coverage for bounded math, measured inputs and honest evidence.

These tests use actual tool implementations and an empty local literature stub;
no model training, remote service or external corpus is required.
"""
import json
import subprocess
from unittest.mock import patch

import pytest

from tiny_experts.experts.electronics_expert import ElectronicsExpert
from tiny_experts.experts.math_expert import MathExpert
from tiny_experts.experts.mechanics_expert import MechanicsExpert
from tiny_experts.experts.thermodynamics_expert import ThermodynamicsExpert
from tiny_experts.pipeline.automated_contradiction_engine import AutomatedContradictionEngine
from tiny_experts.pipeline.bayesian_calibrator import BayesianCalibrator
from tiny_experts.pipeline.biochemical_engine import BiochemicalEngine
from tiny_experts.pipeline.cas_engine import SymbolicCASEngine
from tiny_experts.pipeline.critic import ScientificCritic
from tiny_experts.pipeline.dag_orchestrator import TopologicalDAGOrchestrator
from tiny_experts.pipeline.debate_engine import MultiAgentDebateEngine
from tiny_experts.pipeline.diagnostic_tree_engine import DiagnosticTreeEngine
from tiny_experts.pipeline.disease_triangle_engine import DiseaseTriangleEngine
from tiny_experts.pipeline.reasoning_engine import ReasoningEngine
from tiny_experts.pipeline.universal_concept_graph import UniversalConceptGraph


class EmptyBooks:
    def search(self, **kwargs):
        return []


def evaluate(expert_class, query):
    return expert_class(book_engine=EmptyBooks()).evaluate({"query": query})


@pytest.mark.parametrize("expression", ["eval(chr(49))", "__import__('math')", "x.__class__", "[x][0]", "(lambda: 1)()", "x**999999", "9**9**9"])
def test_cas_rejects_code_and_unbounded_powers(expression):
    result = SymbolicCASEngine.differentiate(expression)
    assert result["success"] is False
    assert result["status"] == "invalid_or_unsupported"


def test_cas_solves_and_checks_a_polynomial():
    result = SymbolicCASEngine.solve_algebra("x^2 - 4 = 0")
    assert result["success"]
    assert set(result["solutions"]) == {"-2", "2"}
    assert result["verified_by_substitution"] is True


@pytest.mark.parametrize("expression", ["x/x = 1", "x*x^-1 = 1"])
def test_polynomial_solver_does_not_lose_domain_exclusions(expression):
    result = SymbolicCASEngine.solve_algebra(expression)
    assert result["success"] is False
    assert result["status"] == "invalid_or_unsupported"


def test_cas_calculus_and_implicit_multiplication():
    derivative = SymbolicCASEngine.differentiate("sin(x) + 3x^2")
    assert derivative["success"] and derivative["result"] == "6*x + cos(x)"
    integral = SymbolicCASEngine.integrate("t^2", var_str="t", lower=0, upper=3)
    assert integral["success"] and integral["numerical_value"] == 9


def test_cas_matrix_operation_validation():
    result = SymbolicCASEngine.solve_matrix([[1, 2], [3, 4]])
    assert result["result"]["determinant"] == -2
    assert not SymbolicCASEngine.solve_matrix([[1, 2], [3, 4]], operation="unknown")["success"]
    assert not SymbolicCASEngine.solve_matrix([["eval(chr(49))"]])["success"]


def test_cas_timeout_is_an_explicit_failure():
    with patch("tiny_experts.pipeline.cas_engine.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 5)):
        result = SymbolicCASEngine.integrate("sin(x)")
    assert result["success"] is False and result["status"] == "timeout"


def test_math_division_by_zero_is_never_reported_as_zero():
    result = MathExpert().evaluate({"query": "12 / 0"})
    assert result["performed_calculation"] is False
    assert result["status"] == "invalid_input"
    assert result["details"] == []
    assert result["errors"] and "zero" in result["errors"][0]


def test_math_expression_is_not_truncated_to_first_binary_operation():
    result = MathExpert().evaluate({"query": "Calculate -2.5 + 3 * 4"})
    assert result["details"][0]["result"] == 9.5


def test_math_integral_variable_and_bounds_are_preserved():
    result = MathExpert().evaluate({"query": "integrate t^2 dt from 0 to 3"})
    assert result["symbolic_cas"]["variable"] == "t"
    assert result["details"][0]["numerical_value"] == 9


def test_plant_capacity_requires_dimensions_and_does_not_invent_a_square():
    missing = MathExpert().evaluate({"query": "How many plants?", "botany_info": {"spacing_cm": 50}})
    assert not missing["performed_calculation"] and missing["errors"]
    short_row = MathExpert().evaluate({"query": "How many plants in a 0.1 m row with spacing 50 cm?"})
    detail = short_row["details"][0]
    assert detail["row_capacity_count"] == 0
    assert "square_plot_capacity" not in detail


def test_plot_spacing_zero_is_an_explicit_error():
    result = MathExpert().evaluate({"query": "Plot capacity 5 x 5 m spacing 0 cm"})
    assert not result["performed_calculation"] and result["errors"]


@pytest.mark.parametrize("query, expected", [("voltage=5V resistance=2kohm", .0025), ("voltage=5 V resistance=2 kΩ", .0025)])
def test_electronics_kiloohms_are_local_to_resistance(query, expected):
    result = evaluate(ElectronicsExpert, query)
    assert not result["errors"]
    assert result["calculations"]["ohms_law"]["calculated_current_amperes"] == pytest.approx(expected)


def test_electronics_milliamps_are_not_lost_in_other_words():
    result = evaluate(ElectronicsExpert, "Calculate voltage for current=2mA and resistance=1000ohm")
    assert result["calculations"]["ohms_law"]["calculated_voltage_volts"] == 2


@pytest.mark.parametrize("capacitance,tau", [("1 f", 100), ("1 uf", .0001)])
def test_explicit_farads_and_next_assignment(capacitance, tau):
    result = evaluate(ElectronicsExpert, f"r=100 c={capacitance}")
    assert not result["errors"]
    assert result["calculations"]["rc_transient"]["time_constant_tau_seconds"] == pytest.approx(tau)


def test_resistor_network_excludes_voltage_and_handles_a_short_circuit():
    result = evaluate(ElectronicsExpert, "voltage=12V resistors 10ohm and 20ohm in series")
    assert result["calculations"]["resistor_network"]["resistors"] == [10, 20]
    assert result["calculations"]["resistor_network"]["equivalent_resistance_ohms"] == 30
    short = evaluate(ElectronicsExpert, "resistors 0ohm and 20ohm in parallel")
    assert short["calculations"]["resistor_network"]["equivalent_resistance_ohms"] == 0


@pytest.mark.parametrize("query", ["v=12 r=0", "v=12 i=0", "r=10 c=0f"])
def test_electronics_undefined_quantities_do_not_get_fabricated_values(query):
    result = evaluate(ElectronicsExpert, query)
    assert not result["calculations"] and result["errors"]


def test_mechanics_scales_grams_and_preserves_negative_acceleration():
    result = evaluate(MechanicsExpert, "mass=500 g acceleration=-2 m/s^2")
    assert result["calculations"]["newtons_second_law"]["force_Newtons"] == -1
    assert "kinetic_energy_and_momentum" not in result["calculations"]


def test_mechanics_signed_kinematics():
    result = evaluate(MechanicsExpert, "u=10 a=-2 t=3")
    assert result["calculations"]["kinematics_1d"]["final_velocity_m_s"] == 4
    assert result["calculations"]["kinematics_1d"]["displacement_meters"] == 21


def test_mechanics_rejects_unsupported_mass_units():
    result = evaluate(MechanicsExpert, "mass=10 pounds acceleration=2")
    assert "newtons_second_law" not in result["calculations"]
    assert result["errors"]


def test_thermodynamics_mixed_absolute_units_and_difference():
    result = evaluate(ThermodynamicsExpert, "Carnot T_H=500K T_C=20C k=1 area=1 thickness=1")
    assert result["calculations"]["carnot_efficiency"]["T_C_Kelvin"] == pytest.approx(293.15)
    assert result["calculations"]["fourier_conduction"]["delta_T_Kelvin"] == pytest.approx(206.85)


@pytest.mark.parametrize("query", ["Carnot T_H=100 T_C=20", "Carnot T_H=500K T_C=-1K", "Carnot T_H=200K T_C=300K"])
def test_thermodynamics_does_not_guess_units_or_accept_invalid_reservoirs(query):
    result = evaluate(ThermodynamicsExpert, query)
    assert "carnot_efficiency" not in result["calculations"] and result["errors"]


def test_zero_conductivity_does_not_divide_by_zero():
    result = evaluate(ThermodynamicsExpert, "k=0 area=4 thickness=0.1 delta_T=50")
    calculation = result["calculations"]["fourier_conduction"]
    assert calculation["heat_rate_watts"] == 0
    assert calculation["thermal_resistance_K_per_W"] is None
    assert calculation["thermal_resistance_status"] == "unbounded_zero_conductance"


def test_weather_missing_inputs_remain_unknown():
    result = DiseaseTriangleEngine.evaluate_outbreak_risk("Late Blight", query="temperature 20C")
    assert result["status"] == "insufficient_data"
    assert set(result["missing_inputs"]) == {"rh_percent", "leaf_wetness_hours"}
    assert result["weather_measurements"]["rh_percent"] is None
    assert result["outbreak_probability_pct"] is None
    assert result["risk_level"] == "UNKNOWN"


def test_weather_rule_remains_a_real_computation_without_fake_probability():
    result = DiseaseTriangleEngine.evaluate_outbreak_risk("Late Blight", query="20C humidity 95% leaf wetness 16 hours")
    assert result["status"] == "computed_rule_index"
    assert result["severity_value"] == "SV 3/4"
    assert result["outbreak_probability_pct"] is None
    assert result["model_validation"] == "not_validated"
    assert "spray" not in result["preventative_action"].lower()


def test_invalid_weather_and_unrelated_percentages():
    invalid = DiseaseTriangleEngine.evaluate_outbreak_risk("Late Blight", query="20C humidity 180% leaf wetness 16 hours")
    assert invalid["status"] == "invalid_data"
    assert DiseaseTriangleEngine.extract_weather_from_text("Model accuracy 95% at 20C")["rh_percent"] is None


def test_lookalike_features_are_pair_specific_and_handle_hairless():
    hairy = BayesianCalibrator.evaluate("hemlock hairy stem")
    hairless = BayesianCalibrator.evaluate("hemlock hairless stem")
    assert hairy["calibrated_posterior"][1]["evidence_score"] > hairless["calibrated_posterior"][1]["evidence_score"]
    assert hairless["calibrated"] is False
    assert all(candidate["probability"] is None for candidate in hairless["calibrated_posterior"])
    assert not BayesianCalibrator.evaluate("mushroom with three examples")["observed_evidence"]
    assert not BayesianCalibrator.evaluate("hemlock not hairy")["observed_evidence"]


def test_biochemical_pair_detection_requires_two_relevant_mentions():
    assert not BiochemicalEngine.evaluate("aspirin")["detected_drug_interactions"]
    nsaid = BiochemicalEngine.evaluate("willow and aspirin")["detected_drug_interactions"]
    assert len(nsaid) == 1 and "NSAID" in nsaid[0]["class"]
    anticoagulant = BiochemicalEngine.evaluate("willow and warfarin")["detected_drug_interactions"]
    assert len(anticoagulant) == 1 and "Anticoagulant" in anticoagulant[0]["class"]
    assert not BiochemicalEngine.evaluate("willow; not taking aspirin")["detected_drug_interactions"]


def test_diagnostic_procedure_honors_crop_and_does_not_claim_execution(tmp_path):
    source = tmp_path / "keys.json"
    source.write_text(json.dumps([{"condition": "Early Blight", "crop": "Tomato", "test_name": "Observe lesions", "in_field_steps": ["A marker confirms the condition"], "rapid_diagnostic_outcome": "Confirmed disease"}]))
    engine = DiagnosticTreeEngine(str(source))
    assert engine.get_in_field_test(condition="Early Blight", crop="Rice") is None
    result = engine.get_in_field_test(condition="Early Blight", crop="Tomato")
    assert result["status"] == "procedure_reference"
    assert "not been executed" in result["rapid_diagnostic_outcome"]
    assert "confirms" not in result["in_field_steps"][0]


def test_concept_links_do_not_match_punctuation():
    assert UniversalConceptGraph.find_cross_connections("A & B") == []
    links = UniversalConceptGraph.find_cross_connections("solar radiation and photosynthesis")
    assert links and links[0]["inference_performed"] is False


def test_contradiction_checks_convert_units_and_require_comparable_context():
    same = AutomatedContradictionEngine.discover_contradictions([
        {"source": "A", "text": "The target temperature is 25°C."},
        {"source": "B", "text": "The target temperature is 298.15 K."}], query="temperature")
    assert same["comparisons_performed"] == 1 and not same["contradiction_detected"]
    unrelated = AutomatedContradictionEngine.discover_contradictions([
        {"text": "The room temperature is 25°C."}, {"text": "The core temperature is 70°C."}], query="temperature")
    assert unrelated["comparisons_performed"] == 0 and not unrelated["contradiction_detected"]
    conflict = AutomatedContradictionEngine.discover_contradictions([
        {"text": "The target temperature is 25°C."}, {"text": "The target temperature is 35°C."}], query="temperature")
    assert conflict["contradiction_detected"] and not conflict["automatically_resolved"]
    assert "Unresolved" in conflict["reconciliations"][0]["synthesis"]


def test_discourse_markers_are_not_proof_of_disagreement():
    result = AutomatedContradictionEngine.discover_contradictions([{"text": "However, this is an example."}, {"text": "Another example."}], "examples")
    assert not result["contradiction_detected"] and result["discourse_markers"]


def test_dag_is_deterministic_and_orders_actual_data_dependency():
    first = TopologicalDAGOrchestrator.compute_execution_order(["math", "botany", "genetics", "pathology"])
    second = TopologicalDAGOrchestrator.compute_execution_order(["pathology", "genetics", "botany", "math"])
    assert first == second
    assert first.index("botany") < first.index("math")


def test_dag_refuses_a_cycle(monkeypatch):
    monkeypatch.setattr(TopologicalDAGOrchestrator, "DEPENDENCIES", {"a": {"b"}, "b": {"a"}})
    with pytest.raises(ValueError, match="cycle"):
        TopologicalDAGOrchestrator.compute_execution_order(["a", "b"])


def test_critic_reports_scope_and_fixes_the_real_botany_field():
    empty = ScientificCritic.audit_and_correct({}, "")
    assert empty["audit_passed"] is None and empty["status"] == "no_applicable_checks"
    data = {"toxicity": {"is_hazardous": True}, "botany": {"recommendation": "Safe to handle with bare hands."}}
    audit = ScientificCritic.audit_and_correct(data, "")
    assert audit["corrections_applied"]
    assert "bare hands" not in data["botany"]["recommendation"]
    assert "100%" not in audit["summary"]


def test_debate_lists_only_actual_outputs_without_claiming_consensus():
    assert MultiAgentDebateEngine.evaluate_debate("tomato blight", ["pathology"], {}) is None
    result = MultiAgentDebateEngine.evaluate_debate("tomato blight", ["pathology", "botany", "toxicity"],
        {"pathology": {"relevant": True}, "botany": {"relevant": True}})
    assert result["squads_participating"] == ["botany", "pathology"]
    assert result["consensus_score"] is None and result["consensus_established"] is False


def test_trace_uses_actual_events_and_never_invents_verification():
    data = {"execution_events": [{"stage": "pathology", "status": "failed", "detail": "Model unavailable"}]}
    trace = ReasoningEngine.generate_thinking_trace("query", None, False, ["pathology", "toxicity"], data)
    assert "[pathology: failed] Model unavailable" in trace
    assert "ASPCA" not in trace and "95%" not in trace and "<think>" not in trace
    assert "multi_agent_debate" not in data
    assert "unavailable" in ReasoningEngine.generate_thinking_trace("query", None, False, [], {})
