import math
import re
from typing import Any, Dict, Optional
from ..pipeline.book_engine import BookEngine
from ..pipeline.diagram_engine import DiagramEngine
from ..pipeline.cas_engine import SymbolicCASEngine
from ..pipeline.quantity_parser import NUMBER, read_quantity


class CircuitCalculator:
    """Calculates supported ideal resistor and RC circuit quantities."""
    name = 'Circuit Calculator'
    description = 'Calculates supported ideal resistor and RC circuit quantities.'
    component_kind = 'symbolic_tool'
    uses_neural_model = False
    updates_parameters_at_inference = False

    RESISTANCE_UNITS = {"ohm": 1, "ohms": 1, "ω": 1, "kohm": 1000, "kohms": 1000,
                        "kω": 1000, "kiloohm": 1000, "kiloohms": 1000}

    def __init__(self, book_engine: Optional[BookEngine] = None):
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("vernacular_meta", {}).get("normalized_query") or context.get("query", "")
        q_lower = query.lower()
        calculations, principles, errors, assumptions = {}, [], [], []
        svg_diagram = symbolic_derivation = None
        network = "parallel" if re.search(r"\bparallel\b|समानांतर|समांतर", q_lower) else (
            "series" if re.search(r"\bseries\b|श्रेणी", q_lower) else None)

        def read(labels, units, default, name, standalone=False):
            return read_quantity(query, labels, units, default, errors, assumptions, name=name, standalone=standalone)

        v = read(r"voltage|v|वोल्टता|वोल्ट", {"v": 1, "volt": 1, "volts": 1, "mv": .001, "kv": 1000}, "v", "voltage", True)
        current = read(r"current|i|धारा", {"a": 1, "amp": 1, "amps": 1, "ampere": 1, "amperes": 1,
                                             "ma": .001, "ua": 1e-6, "µa": 1e-6, "μa": 1e-6}, "a", "current", True)
        resistance = read(r"resistance|r|प्रतिरोध", self.RESISTANCE_UNITS, "ohm", "resistance", not network)
        capacitance = read(r"capacitance|c|धारिता", {"f": 1, "farad": 1, "farads": 1,
                         "mf": 1e-3, "uf": 1e-6, "µf": 1e-6, "μf": 1e-6, "microfarad": 1e-6,
                         "microfarads": 1e-6, "nf": 1e-9, "pf": 1e-12}, "f", "capacitance", True)
        if resistance is not None and resistance < 0:
            errors.append("Resistance must be nonnegative for this passive-resistor model.")
            resistance = None

        if v is not None and resistance is not None and current is None:
            if resistance == 0:
                errors.append("I = V/R is undefined for zero resistance; no finite current is inferred.")
            else:
                calculated_i = v / resistance
                calculations["ohms_law"] = {"voltage_volts": v, "resistance_ohms": resistance,
                    "calculated_current_amperes": calculated_i, "calculated_current_mA": calculated_i * 1000,
                    "power_dissipation_watts": v * calculated_i, "formula": "I = V / R, P = V * I"}
        elif current is not None and resistance is not None and v is None:
            calculations["ohms_law"] = {"current_amperes": current, "resistance_ohms": resistance,
                "calculated_voltage_volts": current * resistance, "power_dissipation_watts": current ** 2 * resistance,
                "formula": "V = I * R, P = I^2 * R"}
        elif v is not None and current is not None and resistance is None and not network:
            if current == 0:
                errors.append("R = V/I is undefined for zero current; no finite resistance is inferred.")
            elif v / current < 0:
                errors.append("Voltage and current signs imply negative resistance, outside this passive-resistor model.")
            else:
                calculations["ohms_law"] = {"voltage_volts": v, "current_amperes": current,
                    "calculated_resistance_ohms": v / current, "power_dissipation_watts": v * current,
                    "formula": "R = V / I, P = V * I"}
        elif v is not None and current is not None and resistance is not None:
            if not math.isclose(v, current * resistance, rel_tol=1e-6, abs_tol=1e-9):
                errors.append("Provided voltage, current and resistance do not satisfy V = I * R.")
        if "ohms_law" in calculations:
            principles.append("Ohm's Law for an ideal resistor")

        if network:
            unit_pattern = "|".join(re.escape(u) for u in sorted(self.RESISTANCE_UNITS, key=len, reverse=True))
            matches = re.finditer(rf"(?<![\w.])({NUMBER})\s*({unit_pattern})(?!\w)", query, re.I)
            resistors = [float(m.group(1)) * self.RESISTANCE_UNITS[m.group(2).lower()] for m in matches]
            if not resistors:
                # Unitless lists are accepted only inside an explicit resistor clause.
                clause = re.search(r"\bresistors?\s+(.+?)\s+(?:in\s+)?(?:series|parallel)\b", query, re.I)
                parts = re.split(r"\s*(?:,|;|\band\b|&)\s*", clause.group(1)) if clause else []
                if len(parts) >= 2 and all(re.fullmatch(NUMBER, part.strip(), re.I) for part in parts):
                    resistors = [float(part) for part in parts]
                    assumptions.append("Unitless resistor-list values interpreted as ohms.")
            if not 2 <= len(resistors) <= 16:
                errors.append("Specify 2 to 16 resistor values with units, or an explicit unitless resistor list.")
            elif any(not math.isfinite(r) or r < 0 or r > 1e12 for r in resistors):
                errors.append("Resistor values must be finite and between 0 and 1e12 ohms.")
            else:
                equivalent = sum(resistors) if network == "series" else (0.0 if 0 in resistors else 1 / sum(1 / r for r in resistors))
                calculations["resistor_network"] = {"configuration": network.title(), "resistors": resistors,
                    "equivalent_resistance_ohms": equivalent,
                    "formula": "R_eq = sum(R_i)" if network == "series" else "1 / R_eq = sum(1 / R_i)"}
                principles.append(f"{network.title()} resistor network")
                if len(resistors) == 2 and v is not None:
                    svg_diagram = DiagramEngine.generate_circuit_svg(config=network, r_vals=resistors, v_val=v)

        if resistance is not None and capacitance is not None:
            if resistance <= 0 or capacitance <= 0:
                errors.append("A finite RC time constant and cutoff require positive resistance and capacitance.")
            else:
                tau = resistance * capacitance
                calculations["rc_transient"] = {"resistance_ohms": resistance, "capacitance_farads": capacitance,
                    "time_constant_tau_seconds": tau, "time_to_99_percent_seconds": -math.log(.01) * tau,
                    "cutoff_frequency_Hz": 1 / (2 * math.pi * tau), "formula": "tau = R * C, f_c = 1 / (2 * pi * R * C)"}
                principles.append("Ideal RC transient and cutoff frequency")
        if re.search(r"\b(?:derive|derivation)\b", q_lower) and re.search(r"\b(?:rc|filter|cutoff)\b", q_lower):
            symbolic_derivation = SymbolicCASEngine.derive_physics_law("rc")
        if re.search(r"\b(?:kirchhoff|kcl|kvl)\b|किरचॉफ", q_lower):
            principles.append("Kirchhoff's circuit laws (reference only)")
        if not calculations and not errors and any(c.isdigit() for c in query):
            uni_solve = SymbolicCASEngine.solve_numerical_word_problem(query, preferred_subdomain="electromagnetism")
            if uni_solve.get("solved"):
                calculations["universal_formula_solver"] = uni_solve
                principles.append(uni_solve.get("formula_name") or "Universal SymPy Formula Solver")

        literature = self.book_engine.search(shelf="electronics", query=query, top_k=2)
        if not literature:
            literature = self.book_engine.search(shelf="physics", query=query, top_k=2)
        status = "partial_result" if calculations and errors else "computed" if calculations else "invalid_input" if errors else "reference_only"
        return {"expert": "CircuitCalculator", "active": True, "status": status, "detected_principles": principles,
                "calculations": calculations, "errors": errors, "assumptions": assumptions,
                "svg_diagram": svg_diagram, "symbolic_derivation": symbolic_derivation,
                "governing_laws": ["V = I * R", "P = V * I", "tau = R * C", "f_c = 1 / (2 * pi * R * C)"],
                "textbook_citations": [{"source": lit.get("source"), "excerpt": str(lit.get("text") or "")[:280],
                    "book_id": lit.get("book_id"), "citation": lit.get("citation")} for lit in literature]}


# Compatibility for existing integrations and model-training imports.
ElectronicsExpert = CircuitCalculator
