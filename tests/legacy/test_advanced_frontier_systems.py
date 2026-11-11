import unittest
import os
import tempfile
from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.dag_orchestrator import TopologicalDAGOrchestrator
from tiny_experts.pipeline.cas_engine import SymbolicCASEngine
from tiny_experts.pipeline.sqlite_fts_engine import SQLiteFTSEngine
from tiny_experts.pipeline.diagram_engine import DiagramEngine
from tiny_experts.pipeline.automated_contradiction_engine import AutomatedContradictionEngine

class TestAdvancedFrontierSystems(unittest.TestCase):
    """
    Rigorously tests Tier 1 - Tier 5 Advanced Scientific Computing Frontiers:
    1. Topological DAG Orchestrator (O(V+E) dependency resolution)
    2. Symbolic Computer Algebra System (CAS derivations, calculus, algebra, matrices via SymPy)
    3. Disk-Backed SQLite FTS5 Engine (C-level BM25 ranked search)
    4. Dynamic SVG Vector Schematic Generator (Circuits, Carnot P-V, Disease Triangle)
    5. Automated Dialectical Contradiction Engine (Thesis-Antithesis-Synthesis matrix)
    6. End-to-End Orchestrator Execution
    """

    def test_01_topological_dag_orchestrator(self):
        # Test 1: Prerequisite ordering
        active = ["communicator", "pathology", "vision", "botany", "toxicity"]
        ordered = TopologicalDAGOrchestrator.compute_execution_order(active)
        
        # Vision must run before Botany
        self.assertLess(ordered.index("vision"), ordered.index("botany"))
        # Botany must run before Pathology
        self.assertLess(ordered.index("botany"), ordered.index("pathology"))
        # Pathology must run before Communicator
        self.assertLess(ordered.index("pathology"), ordered.index("communicator"))
        # Communicator must be last among these
        self.assertEqual(ordered[-1], "communicator")

    def test_02_symbolic_cas_algebra_and_calculus(self):
        # Test polynomial solving: x^2 - 5x + 6 = 0 => roots: [2, 3]
        solve_res = SymbolicCASEngine.solve_algebra("x^2 - 5x + 6 = 0", var_str="x")
        self.assertTrue(solve_res["success"])
        self.assertEqual(solve_res["solutions"], ["2", "3"])
        self.assertEqual(solve_res["numerical_approx"], [2.0, 3.0])

        # Test differentiation: d/dx(x^3 + 2*x) => 3*x^2 + 2
        diff_res = SymbolicCASEngine.differentiate("x^3 + 2*x", var_str="x", order=1)
        self.assertTrue(diff_res["success"])
        self.assertEqual(diff_res["result"], "3*x**2 + 2")

        # Test definite integration: \int_0^3 x^2 dx = 9.0
        int_res = SymbolicCASEngine.integrate("x^2", var_str="x", lower=0, upper=3)
        self.assertTrue(int_res["success"])
        self.assertEqual(int_res["result"], "9")
        self.assertAlmostEqual(int_res["numerical_value"], 9.0, places=3)

    def test_03_symbolic_cas_matrices_and_physics_laws(self):
        # Matrix determinant: [[1, 2], [3, 4]] => det = -2.0
        mat_res = SymbolicCASEngine.solve_matrix([[1, 2], [3, 4]], operation="determinant")
        self.assertTrue(mat_res["success"])
        self.assertEqual(mat_res["result"]["determinant"], -2.0)

        # Carnot derivation
        carnot_res = SymbolicCASEngine.derive_physics_law("carnot")
        self.assertTrue(carnot_res["success"])
        self.assertIn("T_C/T_H", carnot_res["symbolic_formula"])
        self.assertGreaterEqual(len(carnot_res["derivation_steps"]), 5)

        # Projectile derivation
        proj_res = SymbolicCASEngine.derive_physics_law("projectile")
        self.assertTrue(proj_res["success"])
        self.assertIn("sin(2*theta)", proj_res["symbolic_formula"])

        # RC filter derivation
        rc_res = SymbolicCASEngine.derive_physics_law("rc")
        self.assertTrue(rc_res["success"])
        self.assertIn("2*pi*C*R", rc_res["symbolic_formula"])

    def test_04_sqlite_fts5_disk_engine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_fts.db")
            fts = SQLiteFTSEngine(db_path=db_path)
            
            # Index passages
            fts.index_passage(
                text="The Carnot cycle represents the maximum theoretical efficiency achievable by any heat engine.",
                source="Feynman Lectures on Physics Vol. 1",
                shelf="thermodynamics",
                book_id="feynman_vol1",
                citation="Feynman (1964), Ch. 44"
            )
            fts.index_passage(
                text="Ohm's law governs electric current through an ideal resistor: V = I * R.",
                source="Griffiths Electrodynamics",
                shelf="electronics",
                book_id="griffiths_em",
                citation="Griffiths (2017), Ch. 7"
            )

            self.assertEqual(fts.get_total_passages_count(), 2)

            # Query search with BM25 rank
            results = fts.search("heat engine theoretical efficiency", shelf="thermodynamics")
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0]["book_id"], "feynman_vol1")
            self.assertIn("Carnot cycle", results[0]["text"])

    def test_05_dynamic_svg_diagram_generation(self):
        # 1. Circuit diagram
        series_svg = DiagramEngine.generate_circuit_svg(config="series", r_vals=[10.0, 20.0], v_val=12.0)
        self.assertIn("<svg", series_svg)
        self.assertIn("R1: 10.0", series_svg)
        self.assertIn("Series Network", series_svg)

        parallel_svg = DiagramEngine.generate_circuit_svg(config="parallel", r_vals=[15.0, 30.0], v_val=24.0)
        self.assertIn("<svg", parallel_svg)
        self.assertIn("Parallel Network", parallel_svg)

        # 2. Carnot P-V diagram
        carnot_svg = DiagramEngine.generate_carnot_pv_svg(th_k=600.0, tc_k=300.0)
        self.assertIn("<svg", carnot_svg)
        self.assertIn("T_H = 600.0K", carnot_svg)
        self.assertIn("isotherm-hot", carnot_svg)

        # 3. Disease Triangle diagram
        dt_svg = DiagramEngine.generate_disease_triangle_svg(host="Tomato", pathogen="Phytophthora", env="High Humidity")
        self.assertIn("<svg", dt_svg)
        self.assertIn("Tomato", dt_svg)
        self.assertIn("Phytophthora", dt_svg)

    def test_06_automated_dialectic_contradiction_engine(self):
        # Contradiction: numerical divergence in temperature thresholds
        passages = [
            {"source": "Study A (Lab)", "text": "The optimum incubation temperature for fungal sporulation is 18.0 °C."},
            {"source": "Study B (Field)", "text": "In open canopies, severe blight outbreaks occur at temperatures above 28.5 °C."}
        ]
        res = AutomatedContradictionEngine.discover_contradictions(passages, "temperature condition")
        self.assertTrue(res["contradiction_detected"])
        self.assertEqual(res["reconciliations"][0]["type"], "NUMERICAL_VARIANCE")
        self.assertIn("microclimate", res["reconciliations"][0]["synthesis"].lower())

    def test_07_end_to_end_orchestrator_cas_and_svg(self):
        orchestrator = TinyExpertOrchestrator(verbose=False)
        
        # Test CAS query through orchestrator
        detailed = orchestrator.process_detailed(query="solve x^2 - 7x + 12 = 0")
        self.assertIn("math", detailed["active_experts"])
        self.assertIsNotNone(detailed["telemetry"]["math"].get("symbolic_cas"))
        self.assertEqual(detailed["telemetry"]["math"]["symbolic_cas"]["solutions"], ["3", "4"])
        self.assertIn("Roots:      3, 4", detailed["rendered_card"])

        # Test Physics Circuit calculation and SVG diagram generation
        elec_query = "Calculate equivalent resistance for resistors 10 and 20 in series with 12V source"
        elec_detailed = orchestrator.process_detailed(query=elec_query)
        self.assertIn("electronics", elec_detailed["active_experts"])
        self.assertIsNotNone(elec_detailed.get("svg_diagram"))
        self.assertIn("<svg", elec_detailed["svg_diagram"])
        self.assertIn("DYNAMIC VECTOR SCHEMATIC", elec_detailed["rendered_card"])

        # Test Topological Order recording
        topological_order = elec_detailed["telemetry"]["orchestration_meta"].get("topological_order")
        self.assertIsNotNone(topological_order)
        self.assertIn("electronics", topological_order)

if __name__ == "__main__":
    unittest.main()
