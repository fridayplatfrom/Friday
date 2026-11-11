"""Regression checks for provenance, stale retrieval and fabricated user context."""

import json
import sqlite3
from pathlib import Path

import pytest

from tiny_experts.experts.librarian_expert import LibrarianExpert
from tiny_experts.pipeline.book_catalog_engine import BookCatalogEngine
from tiny_experts.pipeline.book_engine import BookEngine
from tiny_experts.pipeline.dataset_exporter import ScientificDatasetExporter
from tiny_experts.pipeline.episodic_memory import EpisodicMemory
from tiny_experts.pipeline.ingestion import LiteratureIngestionPipeline
from tiny_experts.pipeline.knowledge_store import KnowledgeStore
from tiny_experts.pipeline.schema import OrganismDataRecord
from tiny_experts.pipeline.session_memory import SessionMemory
from tiny_experts.pipeline.sqlite_fts_engine import SQLiteFTSEngine


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("TINY_EXPERT_STATE_DIR", str(tmp_path / "state"))


@pytest.fixture
def library(tmp_path):
    engine = BookEngine(data_dir=str(tmp_path / "books"), include_demo_seeds=False)
    yield engine
    engine.close()


def sample_text(marker):
    return f"{marker} identifies this revision of a local note about leaf transport and water movement through plant tissues."


def test_import_does_not_invent_authority_and_retains_supplied_metadata(library):
    pipeline = LiteratureIngestionPipeline(library)
    result = pipeline.ingest_text(sample_text("firstmarker"), "A local note", "botany")
    passage = json.loads(Path(result["file_saved"]).read_text())[0]
    record = pipeline.catalog_engine.get_book_by_id(passage["book_id"])
    assert record["authors"] == []
    assert record["publisher"] is None
    assert record["year"] is None
    assert record["edition"] is None
    assert record["translations"] == {}
    assert record["authority_tier"] == "UNVERIFIED"
    assert "Verified Academic Corpus" not in passage["citation"]
    assert passage["verification_status"] == "unverified"
    assert passage["review_status"] == "unreviewed"
    assert passage["page_range"] is None

    metadata = {
        "authors": ["A. Researcher"], "year": 2025, "publisher": "Example publisher",
        "source_url": "https://example.org/document", "license": "CC BY 4.0",
        "edition": "2", "page_range": "12-13", "chapter_title": "Leaf transport",
        "verification_status": "verified",  # An import cannot approve itself.
    }
    pipeline.ingest_text(sample_text("secondmarker"), "A local note", "botany", metadata=metadata)
    hit = library.search("secondmarker", shelf="botany")[0]
    assert hit["source_metadata"]["authors"] == ["A. Researcher"]
    assert hit["source_metadata"]["year"] == 2025
    assert hit["source_metadata"]["source_url"] == metadata["source_url"]
    assert hit["page_range"] == "12-13"
    assert hit["chapter_title"] == "Leaf transport"
    assert hit["verification_status"] == "unverified"
    assert hit["locator_precision"] in ("supplied_pages", "supplied_pages_and_text_offsets")


def test_unknown_or_ambiguous_shelf_is_not_botany(library):
    pipeline = LiteratureIngestionPipeline(library)
    assert pipeline.auto_classify_shelf("unrelated qzqxv blue geometric stories") is None
    assert pipeline.auto_classify_shelf("botany genetics") is None
    with pytest.raises(ValueError, match="Unknown shelf"):
        pipeline.ingest_text(sample_text("marker"), "Bad shelf", "grammer")
    with pytest.raises(ValueError, match="Supply --shelf"):
        pipeline.ingest_text("unrelated qzqxv blue geometric stories", "Unknown topic")
    assert library.index == []


def test_reimport_replaces_old_revision_and_is_idempotent_after_restart(library):
    pipeline = LiteratureIngestionPipeline(library)
    first = pipeline.ingest_text(sample_text("obsoleteword"), "Same document", "botany")
    second = pipeline.ingest_text(sample_text("currentword"), "Same document", "botany")
    pipeline.ingest_text(sample_text("currentword"), "Same document", "botany")
    assert first["document_id"] == second["document_id"]
    assert first["content_hash"] != second["content_hash"]
    assert library.search("obsoleteword") == []
    assert len(library.search("currentword")) == 1
    assert library.fts_engine.get_total_passages_count() == 1
    reloaded = BookEngine(data_dir=library.data_dir, include_demo_seeds=False)
    try:
        assert reloaded.search("obsoleteword") == []
        assert len(reloaded.search("currentword")) == 1
        assert reloaded.fts_engine.get_total_passages_count() == 1
    finally:
        reloaded.close()


def test_rebuild_detects_equal_count_changes_and_removes_orphan_cache_rows(library):
    pipeline = LiteratureIngestionPipeline(library)
    result = pipeline.ingest_text(sample_text("obsoleteword"), "Edited file", "botany")
    path = Path(result["file_saved"])
    data = json.loads(path.read_text())
    data[0]["text"] = sample_text("newword")
    path.write_text(json.dumps(data))
    library.fts_engine.index_passage("orphanword", "Deleted source", "botany")
    reloaded = BookEngine(data_dir=library.data_dir, include_demo_seeds=False)
    try:
        assert reloaded.search("obsoleteword") == []
        assert reloaded.search("orphanword") == []
        assert len(reloaded.search("newword")) == 1
        assert reloaded.fts_engine.get_total_passages_count() == 1
    finally:
        reloaded.close()


def test_moving_then_deleting_a_document_does_not_resurrect_it(library):
    pipeline = LiteratureIngestionPipeline(library)
    first = pipeline.ingest_text(sample_text("oldlocation"), "Original title", "botany", document_id="move-me")
    second = pipeline.ingest_text(sample_text("newlocation"), "Renamed title", "ecology", document_id="move-me")
    assert not Path(first["file_saved"]).exists()
    assert library.search("oldlocation") == []
    assert len(library.search("newlocation", shelf="ecology")) == 1
    Path(second["file_saved"]).unlink()
    reloaded = BookEngine(data_dir=library.data_dir, include_demo_seeds=False)
    try:
        assert reloaded.fts_engine.get_total_passages_count() == 0
        assert reloaded.search("newlocation") == []
    finally:
        reloaded.close()


def test_search_requires_text_evidence_and_retains_provenance(library):
    passage = {
        "text": sample_text("chloroplast"), "source": "Titleonlyword",
        "citation": "Citationonlyword", "book_id": "referenceonlyword",
        "page_range": "3-4", "source_metadata": {"license": "CC0"},
    }
    library.add_passages("botany", [passage])
    for query in ("qzqxv", "botany qzqxv", "tell me about qzqxv", "the and or", "Titleonlyword", "Citationonlyword", "referenceonlyword"):
        assert library.search(query, shelf="botany") == []
    hit = library.search("chloroplast", shelf="botany")[0]
    assert hit["page_range"] == "3-4"
    assert hit["source_metadata"] == {"license": "CC0"}
    assert hit["review_status"] == "unreviewed"


def test_fts_upsert_is_idempotent_and_supports_memory_database():
    engine = SQLiteFTSEngine(":memory:")
    try:
        passage = {"text": "chloroplast membrane", "source": "Field notes", "shelf": "botany"}
        engine.index_bulk_passages([passage, passage])
        engine.index_bulk_passages([passage])
        assert engine.get_total_passages_count() == 1
        assert len(engine.search("chloroplast")) == 1
    finally:
        engine.close()


def test_bundled_notes_are_explicitly_unverified_demo_material(tmp_path):
    engine = BookEngine(data_dir=str(tmp_path / "seeded"))
    try:
        hit = engine.search("transcription", shelf="genetics")[0]
        assert hit["source_type"] == "demo_reference"
        assert hit["verification_status"] == "unverified"
        assert hit["review_status"] == "unreviewed"
        assert hit["source"].startswith("Unverified demo note:")
        assert hit["citation"] is None
    finally:
        engine.close()


def test_librarian_does_not_substitute_unrelated_books(tmp_path):
    catalog = BookCatalogEngine(catalog_file=str(tmp_path / "catalog.json"))
    catalog.register_book("education", "Education methods")
    expert = LibrarianExpert(catalog)
    result = expert.evaluate({"query": "books on qzqxv"})
    assert result["matched_books"] == []
    assert result["top_book"] is None
    assert result["citation_text"] == ""
    assert result["status"] == "no_match"
    assert catalog.search_books("cat") == []  # No substring match inside Education.
    known = expert.evaluate({"query": "books on education"})
    assert len(known["matched_books"]) == 1
    assert "None" not in known["citation_text"]
    assert known["content_available"] is False
    assert len(expert.evaluate({"query": "list books"})["matched_books"]) == 1


def test_structured_store_rejects_empty_and_partial_name_matches(tmp_path):
    path = str(tmp_path / "records.json")
    assert KnowledgeStore.find("", store_path=path) is None
    assert not Path(path).exists()
    record = OrganismDataRecord(
        common_name="Domestic Cat", scientific_name="Felis catus", category="animal",
        summary="A locally supplied record", habitat="", diet_or_soil="", care_or_behavior="",
        hazard_level="UNKNOWN", toxin_notes="", source_url="",
    )
    KnowledgeStore.save(record, search_alias="cat", store_path=path)
    assert KnowledgeStore.find("education", store_path=path) is None
    assert KnowledgeStore.find("locally supplied", store_path=path) is None
    assert KnowledgeStore.find(" ", store_path=path) is None
    found = KnowledgeStore.find("Tell me about my cat", store_path=path)
    assert found["scientific_name"] == "Felis catus"
    assert found["verification_status"] == "unverified"


def test_fresh_memory_has_no_personal_facts_and_scopes_all_records():
    memory = EpisodicMemory(":memory:")
    try:
        assert memory.get_profile() == {}
        assert memory.get_pets() == []
        assert memory.retrieve_context_for_query("My dog is in the garden") == {
            "has_relevant_profile": False, "pets": [], "environment": {},
        }
        memory.add_pet("Spot", "dog", session_id="A")
        memory.update_profile("soil_type", "Clay", session_id="A")
        memory.log_observation("Oak", session_id="A")
        memory.update_profile("soil_type", "Sand", session_id="B")
        assert memory.get_pets("B") == []
        assert memory.get_observations("B") == []
        assert memory.retrieve_context_for_query("garden soil", "A")["environment"] == {"soil_type": "Clay"}
        memory.clear_session("A")
        assert memory.get_profile("A") == {}
        assert memory.get_pets("A") == []
        assert memory.get_observations("A") == []
        assert memory.get_profile("B") == {"soil_type": "Sand"}
    finally:
        memory.close()


def test_old_global_demo_memory_is_not_silently_loaded(tmp_path):
    path = str(tmp_path / "legacy.db")
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE user_profile (key TEXT, value TEXT, category TEXT)")
        connection.execute("INSERT INTO user_profile VALUES ('climate_zone', 'Invented zone', 'environment')")
    memory = EpisodicMemory(path)
    try:
        assert memory.get_profile() == {}
        assert memory.retrieve_context_for_query("garden climate")["has_relevant_profile"] is False
        with sqlite3.connect(path) as connection:
            assert connection.execute("SELECT count(*) FROM user_profile").fetchone()[0] == 1
    finally:
        memory.close()


def test_unrelated_turn_clears_old_pronoun_subject():
    memory = SessionMemory()
    memory.record_turn("Sunflower", "A note", {"species": "Common Sunflower", "category": "plant"})
    assert memory.resolve_context("Is it safe?")["resolved_species"] == "Common Sunflower"
    memory.record_turn("What is voltage?", "A calculation", {"species": None, "category": None})
    assert memory.resolve_context("Is it safe?")["resolved_species"] is None


class RecordingOrchestrator:
    def __init__(self):
        self.calls = []
        self.resets = []

    def process_detailed(self, **kwargs):
        self.calls.append(kwargs)
        return {"rendered_card": "Candidate response", "thinking_trace": "A fabricated trace must not be copied",
                "active_experts": ["math"], "latency_ms": 1}

    def reset_session(self, session_id):
        self.resets.append(session_id)


@pytest.mark.parametrize("format_name", ["alpaca", "sharegpt"])
def test_export_is_unreviewed_and_does_not_reuse_user_sessions(tmp_path, format_name):
    orchestrator = RecordingOrchestrator()
    exporter = ScientificDatasetExporter(orchestrator)
    path = tmp_path / f"{format_name}.jsonl"
    result = exporter.export_to_jsonl(str(path), format_name, ["Question one?", "Question two?"])
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert result["verified_factual"] is False
    assert len(records) == 2
    for record in records:
        assert record["metadata"]["verified_factual"] is False
        assert record["metadata"]["review_status"] == "unreviewed"
        assert record["metadata"]["generation_method"] == "programmatic_expert_output"
        assert "fabricated trace" not in json.dumps(record)
    session_ids = [call["session_id"] for call in orchestrator.calls]
    assert len(set(session_ids)) == 2
    assert "default_session" not in session_ids
    assert orchestrator.resets == session_ids
    assert all(call["show_thinking"] is False for call in orchestrator.calls)
    assert exporter.generate_sft_dataset(custom_prompts=[]) == []
    with pytest.raises(ValueError):
        exporter.generate_sft_dataset("unknown")
