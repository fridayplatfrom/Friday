"""Combine relevant bounded components without treating agreement as truth."""
import math

from ..matching import contains_term
from .automated_contradiction_engine import AutomatedContradictionEngine


class AnswerCoordinator:
    DOMAIN_CALCULATORS = {
        'classical_mechanics': 'mechanics',
        'electromagnetism': 'electronics',
        'thermodynamics_stat_mech': 'thermodynamics',
    }
    # Only calculated SI outputs are comparable; input fields are not votes.
    OBSERVABLES = {
        'force_Newtons': ('F', 'N'),
        'acceleration_m_s2': ('a', 'm/s^2'),
        'kinetic_energy_Joules': ('E_k', 'J'),
        'potential_energy_Joules': ('E_p', 'J'),
        'calculated_current_amperes': ('I_elec', 'A'),
        'calculated_voltage_volts': ('V_elec', 'V'),
        'calculated_resistance_ohms': ('R_elec', 'ohm'),
        'equivalent_resistance_ohms': ('R_eq', 'ohm'),
        'efficiency_fraction': ('eta_carnot', 'fraction'),
    }

    @classmethod
    def review_calculation(cls, query, subdomain, numerical, components):
        report = {'contributions': [], 'cross_check': {'status': 'not_applicable'},
                  'numerical_solution': numerical, 'claims_independently_verified': False}
        key = cls.DOMAIN_CALCULATORS.get(subdomain)
        if not numerical or not numerical.get('solved') or key not in components:
            return report
        component = components[key]
        try:
            result = component.evaluate({'query': query})
            contribution = {'id': key, 'name': component.name,
                            'status': result.get('status', 'completed'), 'output': result}
            report['contributions'].append(contribution)
            comparisons = []
            for calculation, fields in (result.get('calculations') or {}).items():
                # A second call into the same formula solver is not an independent check.
                if calculation == 'universal_formula_solver' or not isinstance(fields, dict):
                    continue
                for field, (variable, unit) in cls.OBSERVABLES.items():
                    if variable != numerical.get('target_variable') or unit != numerical.get('si_unit') or field not in fields:
                        continue
                    value = fields[field]
                    primary = numerical.get('final_value')
                    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                           for v in (value, primary)):
                        continue
                    # Allow common rounding of standard g; never use an absolute
                    # tolerance that would make tiny quantum values all agree.
                    agrees = math.isclose(primary, value, rel_tol=1e-3, abs_tol=0.0)
                    comparisons.append({'variable': variable, 'unit': unit, 'primary': primary,
                                        'reviewer': value, 'agrees': agrees})
            if comparisons:
                agreed = all(c['agrees'] for c in comparisons)
                report['cross_check'] = {'status': 'agrees' if agreed else 'conflict',
                                         'comparisons': comparisons, 'reviewer': component.name}
                if not agreed:
                    report['numerical_solution'] = {
                        **numerical, 'solved': False, 'status': 'component_disagreement',
                        'physical_violations': list(numerical.get('physical_violations') or []) + [
                            'The formula solver and domain calculator disagree on the requested SI quantity; no single numerical answer is accepted.']}
            else:
                report['cross_check'] = {'status': 'no_comparable_calculation', 'reviewer': component.name}
        except Exception as exc:
            report['contributions'].append({'id': key, 'name': component.name, 'status': 'error',
                                            'detail': f'{type(exc).__name__}: {exc}'})
            report['cross_check'] = {'status': 'reviewer_failed'}
        return report

    @staticmethod
    def collect_context(query, dictionary, citations):
        definitions, contributions = [], []
        if dictionary is not None:
            try:
                # Whole terms only: fuzzy hits must not pad the answer with unrelated definitions.
                for entry in dictionary.dictionary:
                    term = entry.get('term')
                    if isinstance(term, str) and term and contains_term(query, term):
                        definitions.append(dict(entry))
                    if len(definitions) == 2:
                        break
                contributions.append({'id': 'dictionary', 'name': dictionary.name,
                                      'status': 'matched' if definitions else 'no_match'})
            except Exception as exc:
                contributions.append({'id': 'dictionary', 'name': 'Dictionary Lookup Service',
                                      'status': 'error', 'detail': str(exc)})
        passages = [{'source': c.get('book_title') or c.get('source', ''),
                     'text': c.get('verbatim_excerpt', '')} for c in citations]
        audit = AutomatedContradictionEngine.discover_contradictions(passages, query)
        contributions.append({'id': 'citation_comparison', 'name': 'Passage Conflict Checker',
                              'status': audit['status']})
        return {'definitions': definitions, 'citation_audit': audit, 'contributions': contributions}
