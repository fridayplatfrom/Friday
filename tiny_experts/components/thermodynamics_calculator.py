import re
from typing import Any, Dict, Optional
from ..pipeline.book_engine import BookEngine
from ..pipeline.diagram_engine import DiagramEngine
from ..pipeline.cas_engine import SymbolicCASEngine
from ..pipeline.quantity_parser import read_quantity, read_temperature


class ThermodynamicsCalculator:
    """Parses supported thermal quantities and applies numerical and symbolic formulas."""
    name = 'Thermodynamics Calculator'
    description = 'Parses supported thermal quantities and applies numerical and symbolic formulas.'
    component_kind = 'symbolic_tool'
    uses_neural_model = False
    updates_parameters_at_inference = False

    STEFAN_BOLTZMANN = 5.670374419e-8

    def __init__(self, book_engine: Optional[BookEngine] = None):
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("vernacular_meta", {}).get("normalized_query") or context.get("query", "")
        q_lower = query.lower()
        calculations, principles, errors, assumptions = {}, [], [], []
        svg_diagram = symbolic_derivation = None
        hot = read_temperature(query, r"t_?h|hot(?:\s+temperature)?|source|उच्च", errors, name="hot reservoir temperature")
        cold = read_temperature(query, r"t_?c|cold(?:\s+temperature)?|sink|निम्न", errors, name="cold reservoir temperature")
        if hot is not None and cold is not None:
            if hot <= cold or cold <= 0:
                errors.append("A Carnot heat engine requires T_H > T_C > 0 K.")
            else:
                efficiency = 1 - cold / hot
                calculations["carnot_efficiency"] = {"T_H_Kelvin": hot, "T_C_Kelvin": cold,
                    "efficiency_fraction": round(efficiency, 8), "efficiency_percent": round(efficiency * 100, 4),
                    "formula": "eta = 1 - T_C / T_H"}
                assumptions.append("Reversible heat engine between the two stated reservoirs; this is an ideal upper bound.")
                principles.append("Carnot maximum reversible efficiency")
                svg_diagram = DiagramEngine.generate_carnot_pv_svg(th_k=hot, tc_k=cold)

        def read(labels, units, default, name):
            return read_quantity(query, labels, units, default, errors, assumptions, name=name)

        conductivity = read(r"conductivity|k|चालकता", {"w/(m*k)": 1, "w/m/k": 1, "w/mk": 1}, "w/(m*k)", "thermal conductivity")
        area = read(r"area|a|क्षेत्रफल", {"m^2": 1, "m2": 1, "m²": 1, "cm^2": 1e-4, "cm2": 1e-4, "cm²": 1e-4}, "m^2", "area")
        thickness = read(r"thickness|length|l|d|मोटाई", {"m": 1, "meters": 1, "cm": .01, "mm": .001}, "m", "thickness")
        delta_t = read(r"delta_?t|temp_diff|dt|तापांतर", {"k": 1, "c": 1, "°c": 1, "f": 5 / 9, "°f": 5 / 9}, "k", "temperature difference")
        if delta_t is None and hot is not None and cold is not None:
            delta_t = hot - cold
        if conductivity is not None and area is not None and thickness is not None and delta_t is not None:
            if conductivity < 0 or area < 0 or thickness <= 0:
                errors.append("Conduction requires nonnegative conductivity/area and positive thickness.")
            else:
                conductance = conductivity * area / thickness
                calculations["fourier_conduction"] = {"thermal_conductivity_k": conductivity, "area_m2": area,
                    "thickness_L_m": thickness, "delta_T_Kelvin": delta_t,
                    "heat_rate_watts": conductance * delta_t, "heat_flux_W_per_m2": conductivity * delta_t / thickness,
                    "thermal_resistance_K_per_W": 1 / conductance if conductance else None,
                    "thermal_resistance_status": "finite" if conductance else "unbounded_zero_conductance",
                    "formula": "Q_dot = k * A * Delta_T / L"}
                assumptions.append("Steady one-dimensional conduction with constant conductivity.")
                principles.append("Fourier conduction")

        if re.search(r"\b(?:radiation|stefan|boltzmann)\b|विकिरण", q_lower):
            temperature = read_temperature(query, r"temperature|temp|t", errors, name="radiating temperature")
            if temperature is not None:
                calculations["stefan_boltzmann_blackbody"] = {"temperature_K": temperature,
                    "blackbody_emissive_power_W_per_m2": self.STEFAN_BOLTZMANN * temperature ** 4,
                    "sigma": self.STEFAN_BOLTZMANN, "formula": "E_b = sigma * T^4"}
                assumptions.append("Ideal blackbody emissivity 1; result is emitted power per area, not net heat exchange.")
                principles.append("Stefan-Boltzmann blackbody emission")
        if re.search(r"\b(?:derive|derivation)\b|व्युत्पत्ति", q_lower) and re.search(r"\b(?:carnot|efficiency)\b|कार्नो", q_lower):
            symbolic_derivation = SymbolicCASEngine.derive_physics_law("carnot")
        if "first law" in q_lower or "प्रथम नियम" in q_lower:
            principles.append("First law of thermodynamics (reference only)")
        if "second law" in q_lower or "entropy" in q_lower or "द्वितीय नियम" in q_lower or "एन्ट्रॉपी" in q_lower:
            principles.append("Second law of thermodynamics (reference only)")
        if not calculations and not errors and any(c.isdigit() for c in query):
            uni_solve = SymbolicCASEngine.solve_numerical_word_problem(query, preferred_subdomain="thermodynamics_stat_mech")
            if uni_solve.get("solved"):
                calculations["universal_formula_solver"] = uni_solve
                principles.append(uni_solve.get("formula_name") or "Universal SymPy Formula Solver")
        literature = self.book_engine.search(shelf="thermodynamics", query=query, top_k=2)
        if not literature:
            literature = self.book_engine.search(shelf="physics", query=query, top_k=2)
        status = "partial_result" if calculations and errors else "computed" if calculations else "invalid_input" if errors else "reference_only"
        return {"expert": "ThermodynamicsCalculator", "active": True, "status": status, "detected_principles": principles,
                "calculations": calculations, "errors": errors, "assumptions": assumptions,
                "svg_diagram": svg_diagram, "symbolic_derivation": symbolic_derivation,
                "governing_laws": ["eta_Carnot = 1 - T_C / T_H", "Q_dot = k * A * Delta_T / L", "E_b = sigma * T^4"],
                "textbook_citations": [{"source": lit.get("source"), "excerpt": str(lit.get("text") or "")[:280],
                    "book_id": lit.get("book_id"), "citation": lit.get("citation")} for lit in literature]}


# Compatibility for existing integrations and model-training imports.
ThermodynamicsExpert = ThermodynamicsCalculator
