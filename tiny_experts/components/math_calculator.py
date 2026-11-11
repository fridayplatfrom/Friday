import math
import re
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.cas_engine import SymbolicCASEngine
from ..pipeline.quantity_parser import NUMBER


class MathCalculator(BaseComponent):
    """Runs deterministic arithmetic, unit conversion and bounded symbolic calculations."""
    name = 'Math Calculator'
    description = 'Runs deterministic arithmetic, unit conversion and bounded symbolic calculations.'
    component_kind = 'symbolic_tool'
    uses_neural_model = False
    updates_parameters_at_inference = False

    def __init__(self):
        super().__init__(name='Math Calculator', description='Runs deterministic arithmetic, unit conversion and bounded symbolic calculations.')

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = str(context.get("query", "")).strip().rstrip("?").strip()
        q_lower = query.lower()
        botany = context.get("botany_info") or {}
        results = {"performed_calculation": False, "details": [], "symbolic_cas": None, "errors": [], "assumptions": []}

        def record(result, detail):
            results["symbolic_cas"] = result
            if result.get("success"):
                results["performed_calculation"] = True
                results["details"].append(detail)
            else:
                results["errors"].append(result.get("error", "The requested symbolic operation was not evaluated."))

        diff = re.search(r"\b(?:diff(?:erentiate)?|derivative\s+of|d/d([a-z]))\s+(.+)$", query, re.I)
        integral = re.search(r"\b(?:integrate|integral\s+of)\s+(.+)$", query, re.I)
        solve = re.search(r"\b(?:solve|find\s+roots?\s+of|zeros?\s+of)\s+(.+)$", query, re.I)
        if diff:
            expression = diff.group(2).strip()
            variable = diff.group(1) or "x"
            var = re.search(r"\s+with\s+respect\s+to\s+([a-z])$", expression, re.I)
            if var:
                variable, expression = var.group(1), expression[:var.start()].strip()
            answer = SymbolicCASEngine.differentiate(expression, var_str=variable)
            record(answer, {"type": "Symbolic Differentiation", "expression": expression,
                            "derivative": answer.get("result"), "latex": answer.get("result_latex")})
        elif integral:
            expression = integral.group(1).strip()
            variable, lower, upper = "x", None, None
            var = re.search(r"\s+(?:with\s+respect\s+to\s+|d)([a-z])$", expression, re.I)
            if var:
                variable, expression = var.group(1), expression[:var.start()].strip()
            bounds = re.search(rf"\s+from\s+({NUMBER})\s+to\s+({NUMBER})$", expression, re.I)
            if bounds:
                lower, upper, expression = float(bounds.group(1)), float(bounds.group(2)), expression[:bounds.start()].strip()
            var = re.search(r"\s+(?:with\s+respect\s+to\s+|d)([a-z])$", expression, re.I)
            if var:
                variable, expression = var.group(1), expression[:var.start()].strip()
            answer = SymbolicCASEngine.integrate(expression, var_str=variable, lower=lower, upper=upper)
            record(answer, {"type": "Symbolic Integration", "expression": expression, "integral": answer.get("result"),
                            "numerical_value": answer.get("numerical_value"), "latex": answer.get("result_latex"),
                            "integration_constant_required": answer.get("integration_constant_required")})
        elif solve:
            equation, variable = solve.group(1).strip(), "x"
            var = re.search(r"\s+for\s+([a-z])$", equation, re.I)
            if var:
                variable, equation = var.group(1), equation[:var.start()].strip()
            answer = SymbolicCASEngine.solve_algebra(equation, var_str=variable)
            record(answer, {"type": "Algebraic Equation Solver", "equation": equation,
                            "roots": answer.get("solutions"), "latex": answer.get("latex_solutions")})
        elif re.search(r"\b(?:derive|derivation)\b", q_lower):
            for law in ["carnot", "projectile", "rc"]:
                if re.search(rf"\b{law}\b", q_lower):
                    answer = SymbolicCASEngine.derive_physics_law(law)
                    record(answer, {"type": "Predefined Symbolic Derivation", "law": answer.get("law"),
                                    "formula": answer.get("symbolic_formula"), "latex": answer.get("latex")})
                    break
        else:
            arithmetic = re.fullmatch(r"(?:calculate|compute|evaluate|what\s+is)?\s*([\d\s.eE+*/^()\-]+)", query, re.I)
            if arithmetic and re.search(r"[+*/^\-]", arithmetic.group(1)):
                expression = arithmetic.group(1).strip()
                answer = SymbolicCASEngine.calculate(expression)
                record(answer, {"type": "Arithmetic", "expression": expression,
                                "result": answer.get("result"), "exact_result": answer.get("exact_result")})

        planting_intent = (re.search(r"\b(?:spacing|planting\s+density|plot\s+capacity)\b", q_lower)
                           or ("how many" in q_lower and re.search(r"\b(?:plants?|garden|row|plot)\b", q_lower)))
        if planting_intent:
            spacing_match = re.search(rf"\bspacing\s*(?:=|:|of)?\s*({NUMBER})\s*(cm|m|inches?|in)\b", query, re.I)
            try:
                spacing = (float(spacing_match.group(1)) * {"cm": .01, "m": 1, "in": .0254, "inch": .0254, "inches": .0254}[spacing_match.group(2).lower()]
                           if spacing_match else float(botany["spacing_cm"]) / 100 if botany.get("spacing_cm") is not None else None)
            except (ValueError, TypeError):
                spacing = None
            dimensions = re.search(rf"({NUMBER})\s*(?:x|×|by)\s*({NUMBER})\s*(m|meters?|metres?|ft|feet)\b", query, re.I)
            row = re.search(rf"({NUMBER})\s*(m|meters?|metres?|ft|feet)\b", query, re.I)
            length = width = None
            if dimensions:
                scale = .3048 if dimensions.group(3).lower() in {"ft", "feet"} else 1
                length, width = float(dimensions.group(1)) * scale, float(dimensions.group(2)) * scale
            elif row and (not spacing_match or row.span()[0] != spacing_match.start(1)):
                length = float(row.group(1)) * (.3048 if row.group(2).lower() in {"ft", "feet"} else 1)
                width = length if re.search(r"\bsquare\b", q_lower) else None
            if spacing is None or length is None:
                results["errors"].append("Plant capacity requires a positive spacing and an explicit row length or plot dimensions.")
            elif spacing < 1e-6 or not all(math.isfinite(v) and 0 < v <= 1e6 for v in [spacing, length] + ([width] if width is not None else [])):
                results["errors"].append("Spacing and plot dimensions must be finite, positive and at most 1e6 meters.")
            else:
                count = math.floor(length / spacing)
                detail = {"type": "Plot Density Calculation", "length_m": length, "width_m": width, "spacing_m": spacing,
                          "recommended_spacing": f"{spacing * 100:g} cm", "row_capacity_count": count,
                          "row_capacity": f"{count} plants per {length:g} m row"}
                if width is not None:
                    total = count * math.floor(width / spacing)
                    detail.update(total_capacity=total, area_sq_meters=length * width,
                                  square_plot_capacity=f"{total} plants in a {length:g} m x {width:g} m rectangular plot")
                results["details"].append(detail)
                results["performed_calculation"] = True
                results["assumptions"].append("Each plant occupies one spacing cell; paths and border clearances are excluded.")
        if botany.get("height_meters") is not None:
            try:
                height = float(botany["height_meters"])
                if not math.isfinite(height) or height < 0:
                    raise ValueError
                results["details"].append({"type": "Height Unit Conversion", "metric": f"{height:g} meters", "imperial": f"{height / .3048:.2f} feet"})
                results["performed_calculation"] = True
            except (ValueError, TypeError):
                results["errors"].append("Botanical height must be a finite, nonnegative number.")
        results["status"] = ("partial_result" if results["performed_calculation"] and results["errors"] else
                             "computed" if results["performed_calculation"] else "invalid_input" if results["errors"] else "reference_only")
        return results


# Compatibility for existing integrations and model-training imports.
MathExpert = MathCalculator
