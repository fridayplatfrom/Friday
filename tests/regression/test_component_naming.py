"""Functional identities must survive legacy imports and actual execution."""
import importlib
import json
from types import SimpleNamespace

from tiny_experts import ComponentOrchestrator, TinyExpertOrchestrator
from tiny_experts.capability_registry import load_catalog, describe_components, search
from tiny_experts.components import MathCalculator, PathologyCandidateAdapter
from tiny_experts.experts.math_expert import MathExpert
from tiny_experts.pipeline.dictionary_lookup import DictionaryLookupService
from tiny_experts.pipeline.lexicon_engine import LexiconEngine


def test_legacy_imports_are_the_same_implementation():
    assert TinyExpertOrchestrator is ComponentOrchestrator
    assert MathExpert is MathCalculator
    assert LexiconEngine is DictionaryLookupService
    result = MathExpert().evaluate({'query': '12 + 8'})
    assert result['performed_calculation']
    assert result['symbolic_cas']['result'] == 20
    # Legacy monkeypatch targets must continue to address canonical globals.
    old_module = importlib.import_module('tiny_experts.experts.math_expert')
    new_module = importlib.import_module('tiny_experts.components.math_calculator')
    assert old_module is new_module


def test_catalog_implementation_names_resolve_and_do_not_imply_training():
    for entry in load_catalog()['entries']:
        if entry['kind'] != 'component':
            continue
        module = importlib.import_module(entry['implementation']['path'][:-3].replace('/', '.'))
        cls = getattr(module, entry['implementation']['class'])
        assert cls.name == entry['name']
        assert cls.uses_neural_model == entry['uses_neural_model']
        assert cls.updates_parameters_at_inference is False
    assert search('Dictionary Lookup Service')
    assert search('Math Calculator', kind='expert')  # Legacy filter alias.


def test_runtime_status_distinguishes_an_adapter_from_a_loaded_model():
    candidate = PathologyCandidateAdapter(book_engine=SimpleNamespace(), classifier=SimpleNamespace(available=False))
    rows = describe_components({'math': MathCalculator(), 'pathology': candidate})
    assert rows[0]['name'] == 'Math Calculator'
    assert rows[0]['uses_neural_model'] is False
    assert rows[1]['uses_neural_model'] is True
    assert rows[1]['neural_model_available'] is False


def test_dictionary_lookup_does_not_rewrite_or_train_the_dictionary(tmp_path):
    path = tmp_path / 'dictionary.json'
    raw = json.dumps([{'term': 'entropy', 'definitions': {'physics': 'A state function.'}}])
    path.write_text(raw, encoding='utf-8')
    lookup = DictionaryLookupService(str(path))
    assert lookup.lookup_term('entropy')['term'] == 'entropy'
    assert lookup.search_dictionary('entropy')[0]['term'] == 'entropy'
    assert path.read_text(encoding='utf-8') == raw
    assert lookup.updates_parameters_at_inference is False


def test_leech_extraction_reports_pattern_counts_honestly(tmp_path):
    from tiny_experts.knowledge_core import KnowledgeCore
    from tiny_experts.source_studio.director import TrainingDirector
    with KnowledgeCore(tmp_path / 'core', curator=True) as core:
        source = core.register_source('fixture', 'Pattern fixture', source_type='book')
        text = 'Isaac Newton (1643-1727). Systemic Acquired Resistance (SAR). F = m * a\nFigure 1.1: Force diagram of a particle.'
        revision = core.ingest(source, text.encode(), media_type='text/plain',
                               rights={'store': True, 'retrieve': True}, license_note='Test fixture')['revision_id']
        core.add_segment(revision, {'type': 'text', 'start': 0, 'end': len(text)})
        director = TrainingDirector(core)
        result = director.extract_source_candidates(revision)
        assert result['formula_candidates_stored'] >= 1
        assert result['dictionary_patterns_detected'] >= 1
        assert result['biography_patterns_detected'] >= 1
        assert result['dictionary_entries_added'] == 0
        assert result['parameters_updated'] is False
        assert director.run_leech_bus.__func__ is director.extract_source_candidates.__func__
