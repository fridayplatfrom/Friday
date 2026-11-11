"""Integration of source revisions, orchestrator, math expert and neural reader."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tiny_experts.orchestrator import TinyExpertOrchestrator
from tiny_experts.pipeline.book_workflow import BookWorkflow
from tiny_experts.neural.passage_reader import train_reader, PassageReaderBundle

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "peter_rabbit.txt"

class OrchestrationReaderTests(unittest.TestCase):
    def test_book_expert_integrity_and_optional_reader(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ,{"TINY_EXPERT_STATE_DIR":root}):
                book=BookWorkflow(Path(root)/"books")
                try:
                    imported=book.import_file(FIXTURE,title="Peter Rabbit",shelf="literature",
                        metadata={"authors":["Beatrix Potter"],"license":"U.S. public domain"})
                    system=TinyExpertOrchestrator()
                    math=system.experts["math"].evaluate({"query":"12 + 8"})
                    self.assertTrue(math["performed_calculation"])
                    self.assertEqual(math["details"][-1]["result"],20)
                    result=system.process_book_question(imported["document_id"],"shoes cabbages")
                    self.assertEqual(result["status"],"evidence_only")
                    source=next(x for x in result["evidence"] if "one of his shoes among the cabbages" in x["text"])
                    self.assertTrue(source["source_consistency"])
                    positive=[]
                    for i,(s,split) in enumerate([("a","train"),("b","validation"),("c","test")]):
                        positive.append({"id":str(i),"source_id":s,"case_id":str(i),"split":split,
                          "question":"What did Peter lose?","passage":source["text"],
                          "answer_text":"one of his shoes",
                          "answer_start":source["text"].index("one of his shoes")})
                    path=Path(root)/"test-reader"
                    train_reader(positive,path,epochs=2,seed=1,demo=True)
                    with self.assertRaisesRegex(ValueError,"disabled"):
                        system.process_book_question(imported["document_id"],"shoes cabbages",
                                                     reader_bundle=path)
                    model=PassageReaderBundle(path,allow_experimental=True)
                    answer=system.process_book_question(imported["document_id"],
                        "What did Peter lose among cabbages?",reader_bundle=model,allow_experimental=True)
                    self.assertIn(answer["status"],{"reader_abstained","experimental_answer"})
                    self.assertTrue(answer["execution_trace"])
                finally:
                    book.close()

if __name__=="__main__": unittest.main()
