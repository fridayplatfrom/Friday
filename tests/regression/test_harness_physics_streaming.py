"""Failures reproduced through the native Harness integration."""
import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import sympy as sp

from tiny_experts.harness_engine import TinyExpertHarnessEngine
from tiny_experts.pipeline.cas_engine import SymbolicCASEngine
from tiny_experts.pipeline.pedagogical_synthesizer import PedagogicalSynthesizer
from tiny_experts.web.server import TinyExpertServerHandler
from tiny_experts.orchestrator import TinyExpertOrchestrator


def test_arithmetic_does_not_fall_through_to_physics():
    app = TinyExpertOrchestrator.__new__(TinyExpertOrchestrator)
    result = app.dispatch_universal_core('solve 2+8')
    assert result['domain'] == 'mathematics'
    assert result['result']['success']
    assert str(result['result']['result']) in {'10', '10.0', '10.0000000000000'}
    _, answer = TinyExpertHarnessEngine._format_universal_core_turn(query='solve 2+8', universal_out=result)
    assert '**Result: 10**' in answer
    invalid = app.dispatch_universal_core('calculate 12/0')
    assert invalid['result']['success'] is False


def test_speed_formula_branch_agrees_with_the_answer():
    result = SymbolicCASEngine.solve_numerical_word_problem(
        "A body has mass = 2 kg and kinetic energy = 100 J. Find its speed.")
    assert result['final_value'] == pytest.approx(10)
    step = result['steps'][0]
    rhs = step['isolated_symbolic_form'].split('=', 1)[1]
    evaluated = sp.sympify(rhs).subs({sp.Symbol(k): v for k, v in step['knowns_used'].items()})
    assert float(evaluated) == pytest.approx(result['final_value'])


def test_zero_is_preserved_in_harness_output():
    result = SymbolicCASEngine.solve_numerical_word_problem(
        "A body has mass = 2 kg and velocity = 0 m/s. Calculate its kinetic energy.")
    trace, answer = TinyExpertHarnessEngine._format_physics_turn(
        query='zero kinetic energy', phys={'numerical_solution': result})
    assert '0.0 J' in answer and 'None J' not in answer
    assert '0.0 J' in trace
    assert 'E_k = E_k =' not in answer


@pytest.mark.parametrize('query,expected', [
    ('A Carnot engine has hot temperature = 600 K and cold temperature = 300 K. Find efficiency.', .5),
    ('A Carnot engine operates between 300 K and 600 K. Find efficiency.', .5),
    ('A Carnot engine has hot temperature = 300 K and cold temperature = 600 K. Find efficiency.', None),
    ('A Carnot engine has T_H = 600 K and T_C = 600 K. Find efficiency.', None),
    ('A Carnot engine operates between -10 K and 600 K. Find efficiency.', None),
])
def test_carnot_respects_reservoir_roles(query, expected):
    result = SymbolicCASEngine.solve_numerical_word_problem(query)
    if expected is None:
        assert result['solved'] is False and result['physical_violations']
    else:
        assert result['solved'] and result['final_value'] == pytest.approx(expected)


def test_no_unrelated_oscillator_derivation_or_experimental_reader(monkeypatch):
    monkeypatch.delenv('TINY_EXPERT_ALLOW_EXPERIMENTAL_READER', raising=False)
    assert PedagogicalSynthesizer._get_neural_reader() is None
    assert SymbolicCASEngine.derive_from_first_principles('classical_mechanics', 'kinetic energy')['derived'] is False
    assert SymbolicCASEngine.derive_from_first_principles('electromagnetism', 'ohms law')['derived'] is False
    assert SymbolicCASEngine.derive_from_first_principles('classical_mechanics', 'harmonic oscillator')['derived'] is True


@pytest.mark.parametrize('fail', [False, True])
def test_sse_delivers_status_before_computation_finishes(fail):
    entered, release = threading.Event(), threading.Event()
    def answer(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        if fail:
            raise RuntimeError('test failure')
        return {'reasoning_trace': 'Computed.', 'reasoning_chunks': ['Computed.'],
                'answer_markdown': '0 J', 'answer_chunks': ['0 ', 'J'], 'usage': {}}
    class Handler(TinyExpertServerHandler):
        orchestrator = SimpleNamespace()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
    try:
        with patch.object(TinyExpertHarnessEngine, 'answer_harness_request', side_effect=answer):
            conn.request('POST', '/api/harness/stream', json.dumps({'query': 'energy'}), {'Content-Type': 'application/json'})
            response = conn.getresponse()
            assert response.status == 200
            first = response.readline()
            assert b'block-start' in first
            assert entered.wait(2)
            # The first event arrived while computation is still blocked.
            assert not release.is_set()
            release.set()
            raw = first + response.read()
            chunks = [json.loads(frame[6:]) for frame in raw.decode().split('\n\n') if frame.startswith('data: ')]
            if fail:
                assert chunks[-1]['type'] == 'error'
                assert not any(c['type'] == 'finish' for c in chunks)
            else:
                assert chunks[-1]['type'] == 'finish'
                assert sum(c['type'] == 'block-start' and c['index'] == 0 for c in chunks) == 1
                text = ''.join(c['text'] for c in chunks if c['type'] == 'text-delta')
                assert text == '0 J'
    finally:
        release.set()
        conn.close()
        server.shutdown(); server.server_close(); thread.join(2)
