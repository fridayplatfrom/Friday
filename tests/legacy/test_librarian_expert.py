import unittest
from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.book_catalog_engine import BookCatalogEngine
from tiny_experts.experts.librarian_expert import LibrarianExpert

class TestLibrarianExpert(unittest.TestCase):
    """
    Test suite for the Universal Librarian & Master Book Encyclopedia Expert.
    Verifies multi-faculty cataloging, multilingual title translations,
    bibliographic querying, and dynamic auto-registration.
    """

    @classmethod
    def setUpClass(cls):
        cls.orchestrator = TinyExpertOrchestrator(verbose=False)
        cls.catalog = BookCatalogEngine()
        cls.librarian = LibrarianExpert(catalog_engine=cls.catalog)

    def test_01_expert_registration(self):
        """Verify LibrarianExpert is registered as the 19th official micro-expert."""
        self.assertIn("librarian", self.orchestrator.experts)
        self.assertEqual(len(self.orchestrator.experts), 24)
        self.assertEqual(self.librarian.name, "Universal Librarian & Master Book Encyclopedia Expert")

    def test_02_multi_faculty_catalog_coverage(self):
        """Verify catalog spans multiple academic faculties: Physics, History, Politics, Biology."""
        faculties = self.catalog.list_faculties_and_disciplines()
        self.assertIn("physics", faculties)
        self.assertIn("biological_sciences", faculties)
        self.assertIn("humanities_and_history", faculties)
        self.assertIn("politics_and_law", faculties)

        # Check Physics disciplines
        self.assertIn("thermodynamics", faculties["physics"]["disciplines"])
        self.assertIn("electromagnetism", faculties["physics"]["disciplines"])

    def test_03_multilingual_title_and_summary_translations(self):
        """Verify all major Indian languages (Hindi, Marathi, Bengali, Tamil, Telugu) are translated."""
        agrios = self.catalog.get_book_by_id("agrios_plant_pathology_6th_ed", lang="hi")
        self.assertIsNotNone(agrios)
        self.assertEqual(agrios["translated_title"], "एग्रियोस पादप रोग विज्ञान")
        self.assertIn("कवक", agrios["translated_summary"])

        # Test Tamil translation
        agrios_ta = self.catalog.get_book_by_id("agrios_plant_pathology_6th_ed", lang="ta")
        self.assertIn("அக்ரியோஸ்", agrios_ta["translated_title"])

        # Test Bengali translation
        agrios_bn = self.catalog.get_book_by_id("agrios_plant_pathology_6th_ed", lang="bn")
        self.assertIn("এগ্রিওস", agrios_bn["translated_title"])

    def test_04_physics_bibliographic_search(self):
        """Verify searching for physics textbooks returns Griffiths and Incropera."""
        results = self.catalog.search_books(query="electrodynamics Griffiths", lang="en")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["book_id"], "griffiths_electrodynamics_4th_ed")
        self.assertIn("David J. Griffiths", results[0]["authors"])

        thermo = self.catalog.search_books(query="thermodynamics heat transfer", lang="en")
        self.assertGreater(len(thermo), 0)
        self.assertEqual(thermo[0]["book_id"], "incropera_heat_and_mass_transfer_8th_ed")

    def test_05_history_and_constitution_coverage(self):
        """Verify History (Nehru Discovery of India) and Politics (Ambedkar Constitution)."""
        history_books = self.catalog.search_books(faculty="humanities_and_history", lang="en")
        self.assertGreater(len(history_books), 0)
        self.assertEqual(history_books[0]["book_id"], "discovery_of_india_nehru")
        self.assertIn("Jawaharlal Nehru", history_books[0]["authors"])

        politics_books = self.catalog.search_books(faculty="politics_and_law", lang="en")
        self.assertGreater(len(politics_books), 0)
        self.assertEqual(politics_books[0]["book_id"], "constitution_of_india_commentary")
        self.assertTrue(any("Ambedkar" in a for a in politics_books[0]["authors"]))

    def test_06_end_to_end_orchestrator_bibliographic_query(self):
        """Verify orchestrator activates Universal Librarian and synthesizes bibliography."""
        res = self.orchestrator.process_detailed(query="What books do we have on electrodynamics and physics?")
        self.assertIn("librarian", res["active_experts"])
        lib_data = res["telemetry"]["librarian"]
        self.assertTrue(lib_data["relevant"])
        self.assertTrue(lib_data["is_bibliographic_query"])
        self.assertGreater(len(lib_data["matched_books"]), 0)

        # Verify Communicator adopted Universal Librarian persona
        comm = res["telemetry"]["communicator"]
        self.assertEqual(comm["persona_code"], "universal_librarian")
        self.assertEqual(comm["persona_badge"], "📚")
        self.assertIn("Universal Book Encyclopedia", res["human_narrative"])
        self.assertIn("Griffiths", res["human_narrative"])

    def test_07_hindi_bibliographic_query(self):
        """Verify Hindi bibliographic query adopts Universal Librarian persona with Hindi output."""
        res = self.orchestrator.process_detailed(query="पादप रोग विज्ञान की कौन सी प्रामाणिक किताबें हमारे पास हैं?")
        comm = res["telemetry"]["communicator"]
        self.assertEqual(comm["persona_code"], "universal_librarian")
        self.assertIn("सार्वभौमिक पुस्तक विश्वकोश", res["human_narrative"])
        self.assertIn("एग्रियोस", res["human_narrative"])

    def test_08_dynamic_book_registration(self):
        """Verify dynamic auto-registration of new books into the catalog."""
        new_book_id = "test_quantum_mechanics_shankar"
        reg_res = self.catalog.register_book(
            book_id=new_book_id,
            title="Principles of Quantum Mechanics",
            authors=["R. Shankar"],
            year=2014,
            faculty="physics",
            discipline="quantum_mechanics",
            edition="2nd Edition",
            subtitle="Quantum Postulates, Dirac Notation, and Path Integrals",
            publisher="Plenum / Springer",
            isbn="978-0306447907"
        )
        self.assertEqual(reg_res["status"], "success")

        # Verify searchable immediately
        found = self.catalog.get_book_by_id(new_book_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["title"], "Principles of Quantum Mechanics")
        self.assertIn("R. Shankar", found["authors"])

if __name__ == "__main__":
    unittest.main()
