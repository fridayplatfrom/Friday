"""Combining components must add relevant evidence, not manufactured certainty."""
from types import SimpleNamespace

import pytest
from unittest.mock import patch

from tiny_experts.pipeline.answer_coordination import AnswerCoordinator
from tiny_experts.harness_engine import TinyExpertHarnessEngine
from tiny_experts.pipeline.cas_engine import SymbolicCASEngine


@pytest.mark.parametrize('expression,expected', [('20+6', 26), ('34444+5444', 39888),
    ('0.1+0.2', .3), ('2(3+4)', 14), ('2^-3', .125)])
def test_numeric_arithmetic_does_not_need_to_launch_a_symbolic_worker(expression, expected):
    with patch('tiny_experts.pipeline.cas_engine.subprocess.run', side_effect=AssertionError('worker should not run')):
        result = SymbolicCASEngine.calculate(expression)
    assert result['success'] and result['result'] == pytest.approx(expected)


@pytest.mark.parametrize('expression', ['12/0', '0^-1', '9**9**9', '1000000000001',
    '((((0.000001**12)**12)**12)**12)', '__import__("os")'])
def test_arithmetic_bounds_and_code_rejection(expression):
    result = SymbolicCASEngine.calculate(expression)
    assert result['success'] is False


def test_nested_fractional_power_falls_back_to_bounded_symbolic_worker():
    result = SymbolicCASEngine.calculate('2^(1/2) + 3')
    assert result['success'] and result['result'] == pytest.approx(2**.5 + 3)


class Calculator:
    name = 'Mechanics Calculator'
    def __init__(self, value):
        self.value = value
        self.calls = 0
    def evaluate(self, context):
        self.calls += 1
        return {'status': 'computed', 'calculations': {'newtons_second_law': {'force_Newtons': self.value}}}


def solution(value=1, unit='N'):
    return {'solved': True, 'target_variable': 'F', 'si_unit': unit, 'final_value': value}


def test_relevant_calculator_cross_checks_and_conflicting_value_is_withheld():
    calculator = Calculator(1)
    irrelevant = Calculator(400)
    components = {'mechanics': calculator, 'electronics': irrelevant}
    result = AnswerCoordinator.review_calculation('mass=0.5 kg acceleration=2', 'classical_mechanics', solution(), components)
    assert result['cross_check']['status'] == 'agrees'
    assert result['claims_independently_verified'] is False
    assert calculator.calls == 1 and irrelevant.calls == 0
    calculator.value = 2
    conflict = AnswerCoordinator.review_calculation('mass=0.5 kg acceleration=2', 'classical_mechanics', solution(), components)
    assert conflict['numerical_solution']['solved'] is False
    assert conflict['numerical_solution']['status'] == 'component_disagreement'
    trace, answer = TinyExpertHarnessEngine._format_physics_turn(query='force', phys={
        'numerical_solution': conflict['numerical_solution'], 'coordination': conflict,
        'component_contributions': conflict['contributions']})
    assert 'disagreement' in answer and 'Exact Symbolic & Numerical Solution' not in answer


@pytest.mark.parametrize('primary,reviewer,unit,expected', [
    (0.0, 0.0, 'N', 'agrees'),
    (1e-20, 2e-20, 'N', 'conflict'),
    (1, 1, 'kN', 'no_comparable_calculation'),
])
def test_cross_check_preserves_zero_small_values_and_units(primary, reviewer, unit, expected):
    result = AnswerCoordinator.review_calculation('force', 'classical_mechanics', solution(primary, unit), {'mechanics': Calculator(reviewer)})
    assert result['cross_check']['status'] == expected


def test_repeated_solver_is_not_an_independent_check():
    repeated = SimpleNamespace(name='Mechanics Calculator', evaluate=lambda context: {
        'status': 'computed', 'calculations': {'universal_formula_solver': solution()}})
    report = AnswerCoordinator.review_calculation('force', 'classical_mechanics', solution(), {'mechanics': repeated})
    assert report['cross_check']['status'] == 'no_comparable_calculation'


def test_dictionary_definitions_require_whole_terms_and_no_evidence_is_not_a_pass():
    dictionary = SimpleNamespace(name='Dictionary Lookup Service', dictionary=[
        {'term': 'ant', 'definitions': {'biology': 'An insect.'}},
        {'term': 'quantum', 'definitions': {'physics': 'A discrete quantity.'}},
    ])
    result = AnswerCoordinator.collect_context('Explain quantum mechanics', dictionary, [])
    assert [entry['term'] for entry in result['definitions']] == ['quantum']
    assert result['citation_audit']['status'] == 'insufficient_comparable_evidence'


def test_component_failure_is_reported_and_does_not_claim_agreement():
    def fail(context):
        raise ValueError('unsupported units')
    report = AnswerCoordinator.review_calculation('force', 'classical_mechanics', solution(), {
        'mechanics': SimpleNamespace(name='Mechanics Calculator', evaluate=fail)})
    assert report['cross_check']['status'] == 'reviewer_failed'
    assert report['contributions'][0]['status'] == 'error'


@pytest.fixture(scope='module')
def runtime(tmp_path_factory):
    import os
    from tiny_experts import ComponentOrchestrator
    old = os.environ.get('TINY_EXPERT_STATE_DIR')
    os.environ['TINY_EXPERT_STATE_DIR'] = str(tmp_path_factory.mktemp('coordinated-runtime'))
    app = ComponentOrchestrator()
    yield app
    app.book_engine.close()
    if old is None:
        os.environ.pop('TINY_EXPERT_STATE_DIR', None)
    else:
        os.environ['TINY_EXPERT_STATE_DIR'] = old


def test_live_physics_combines_calculator_retrieval_and_rendering(runtime):
    turn = TinyExpertHarnessEngine.answer_harness_request(runtime, query='A mass = 500 g has acceleration = 2 m/s^2. Calculate its force.')
    assert '1.0 N' in turn['answer_markdown']
    assert turn['metadata']['cross_check']['status'] == 'agrees'
    ids = {component['id'] for component in turn['metadata']['component_contributions']}
    assert {'mechanics', 'retrieval', 'explanation', 'citation_comparison'} <= ids
    assert 'Components in This Answer' in turn['answer_markdown']


def test_harness_combines_multiple_reference_components_without_shared_memory(runtime):
    initial = set(runtime.sessions)
    turn = TinyExpertHarnessEngine.answer_harness_request(runtime, query='Explain CRISPR gene editing and photosynthesis in plant cells.')
    assert turn['metadata']['domain'] == 'reference_workflow'
    assert {'genetics', 'cell_biology'} <= set(turn['metadata']['active_components'])
    assert 'Guide RNA' in turn['answer_markdown']
    assert 'Genetics Reference Lookup' in turn['answer_markdown']
    assert 'Cell Biology Reference Lookup' in turn['answer_markdown']
    assert set(runtime.sessions) == initial


def test_newton_ordinal_wording_is_not_routed_to_current(runtime):
    out = runtime.dispatch_physics_hierarchy('3rd law of newton')
    assert out['concept_prediction'] == 'newton_third_law'
    assert 'Third Law' in out['teacher_markdown']
