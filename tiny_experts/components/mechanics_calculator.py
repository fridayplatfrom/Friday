import math
import re
from typing import Any, Dict, Optional
from ..pipeline.book_engine import BookEngine
from ..pipeline.cas_engine import SymbolicCASEngine
from ..pipeline.quantity_parser import read_quantity


class MechanicsCalculator:
    """Parses supported mechanical quantities and applies numerical and symbolic formulas."""
    name = 'Mechanics Calculator'
    description = 'Parses supported mechanical quantities and applies numerical and symbolic formulas.'
    component_kind = 'symbolic_tool'
    uses_neural_model = False
    updates_parameters_at_inference = False

    GRAVITY_G = 9.80665

    def __init__(self, book_engine: Optional[BookEngine] = None):
        self.book_engine = book_engine or BookEngine()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("vernacular_meta", {}).get("normalized_query") or context.get("query", "")
        q_lower = query.lower()
        calculations, principles, errors, assumptions = {}, [], [], []
        symbolic_derivation = None

        def read(labels, units, default, name, standalone=False):
            return read_quantity(query, labels, units, default, errors, assumptions, name=name, standalone=standalone)

        mass = read(r"mass|m|द्रव्यमान", {"kg": 1, "g": .001, "gram": .001, "grams": .001, "kilograms": 1}, "kg", "mass", True)
        acceleration = read(r"acceleration|accelerates\s+at|accelerating\s+at|accel|a|त्वरण",
                            {"m/s^2": 1, "m/s2": 1, "m/s²": 1, "cm/s^2": .01}, "m/s^2", "acceleration", True)
        force = read(r"force|f|बल", {"n": 1, "newton": 1, "newtons": 1, "kn": 1000}, "n", "force", True)
        speed_units = {"m/s": 1, "km/h": 1 / 3.6, "kph": 1 / 3.6, "mph": .44704, "cm/s": .01}
        initial = read(r"initial\s+velocity|initial_?vel(?:ocity)?|u|प्रारंभिक\s+वेग", speed_units, "m/s", "initial velocity")
        velocity = read(r"(?<!initial )velocity|speed|moving\s+at|v|वेग|चाल", speed_units, "m/s", "velocity", initial is None)
        length_units = {"m": 1, "meter": 1, "meters": 1, "metre": 1, "metres": 1, "cm": .01, "mm": .001, "km": 1000}
        height = read(r"height|altitude|h|ऊंचाई", length_units, "m", "height")
        radius = read(r"radius|r|त्रिज्या", length_units, "m", "radius")
        time = read(r"time|t|समय", {"s": 1, "sec": 1, "seconds": 1, "ms": .001, "min": 60, "minutes": 60}, "s", "time")
        if mass is not None and mass <= 0:
            errors.append("Mass must be positive for these classical particle calculations.")
            mass = None
        if radius is not None and radius <= 0:
            errors.append("Centripetal motion requires a positive radius.")
            radius = None
        if time is not None and time < 0:
            errors.append("Elapsed time must be nonnegative.")
            time = None

        if mass is not None and acceleration is not None and force is None:
            calculations["newtons_second_law"] = {"mass_kg": mass, "acceleration_m_s2": acceleration,
                "force_Newtons": mass * acceleration, "formula": "F = m * a"}
        elif force is not None and mass is not None and acceleration is None:
            calculations["newtons_second_law"] = {"mass_kg": mass, "force_Newtons": force,
                "acceleration_m_s2": force / mass, "formula": "a = F / m"}
        elif force is not None and mass is not None and acceleration is not None:
            if not math.isclose(force, mass * acceleration, rel_tol=1e-6, abs_tol=1e-9):
                errors.append("Provided force, mass and acceleration do not satisfy F = m * a.")
        if "newtons_second_law" in calculations:
            principles.append("Newton's second law")
        if mass is not None and velocity is not None:
            calculations["kinetic_energy_and_momentum"] = {"mass_kg": mass, "velocity_m_s": velocity,
                "kinetic_energy_Joules": .5 * mass * velocity ** 2, "linear_momentum_kg_m_s": mass * velocity,
                "formula": "E_k = 0.5 * m * v^2, p = m * v"}
            principles.append("Kinetic energy and signed linear momentum")
        if mass is not None and height is not None:
            calculations["gravitational_potential_energy"] = {"mass_kg": mass, "height_meters": height,
                "gravity_g": self.GRAVITY_G, "potential_energy_Joules": mass * self.GRAVITY_G * height,
                "formula": "E_p = m * g * h"}
            assumptions.append("Uniform standard gravity 9.80665 m/s^2; height is measured relative to the chosen datum.")
            principles.append("Gravitational potential energy")
        if initial is not None and acceleration is not None and time is not None:
            calculations["kinematics_1d"] = {"initial_velocity_m_s": initial, "acceleration_m_s2": acceleration,
                "time_seconds": time, "final_velocity_m_s": initial + acceleration * time,
                "displacement_meters": initial * time + .5 * acceleration * time ** 2,
                "formulas": ["v = u + a*t", "s = u*t + 0.5*a*t^2"]}
            assumptions.append("Acceleration is constant throughout the stated time interval.")
            principles.append("One-dimensional constant-acceleration kinematics")
        if mass is not None and velocity is not None and radius is not None:
            calculations["centripetal_dynamics"] = {"mass_kg": mass, "velocity_m_s": velocity,
                "radius_meters": radius, "centripetal_acceleration_m_s2": velocity ** 2 / radius,
                "centripetal_force_Newtons": mass * velocity ** 2 / radius, "formula": "F_c = m * v^2 / r"}
            principles.append("Uniform circular motion")
        if re.search(r"\b(?:derive|derivation)\b", q_lower) and re.search(r"\b(?:projectile|trajectory|range)\b", q_lower):
            symbolic_derivation = SymbolicCASEngine.derive_physics_law("projectile")
        if not calculations and not errors and any(c.isdigit() for c in query):
            uni_solve = SymbolicCASEngine.solve_numerical_word_problem(query, preferred_subdomain="classical_mechanics")
            if uni_solve.get("solved"):
                calculations["universal_formula_solver"] = uni_solve
                principles.append(uni_solve.get("formula_name") or "Universal SymPy Formula Solver")
        literature = self.book_engine.search(shelf="mechanics", query=query, top_k=2)
        status = "partial_result" if calculations and errors else "computed" if calculations else "invalid_input" if errors else "reference_only"
        return {"expert": "MechanicsCalculator", "active": True, "status": status, "detected_principles": principles,
                "calculations": calculations, "errors": errors, "assumptions": assumptions,
                "symbolic_derivation": symbolic_derivation,
                "governing_laws": ["F = m * a", "E_k = 0.5 * m * v^2", "p = m * v", "E_p = m * g * h"],
                "textbook_citations": [{"source": lit.get("source"), "excerpt": str(lit.get("text") or "")[:280],
                    "book_id": lit.get("book_id"), "citation": lit.get("citation")} for lit in literature]}


# Compatibility for existing integrations and model-training imports.
MechanicsExpert = MechanicsCalculator
