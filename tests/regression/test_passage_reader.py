"""Offline neural reader tests: saved weights, leakage checks and abstention."""
import tempfile
import unittest
from pathlib import Path

from tiny_experts.neural.passage_reader import (
    train_reader, validate_splits, verify_example, PassageReaderBundle)

def row(i,source,split,passage="Peter lost his blue jacket in the garden.",answer="blue jacket"):
    return {"id":str(i),"source_id":source,"case_id":str(i),"split":split,
            "question":"What did Peter lose?","passage":passage,
            "answer_text":answer,"answer_start":passage.index(answer) if answer is not None else None}

class PassageReaderTests(unittest.TestCase):
    def test_exact_offset_and_no_answer(self):
        self.assertEqual(verify_example(row(0,"a","train")),(4,5))
        x=row(0,"a","train");x["answer_start"]+=1
        with self.assertRaises(ValueError):verify_example(x)
        self.assertEqual(verify_example(row(0,"a","train",answer=None)),(0,0))
    def test_source_and_case_leakage(self):
        data=[row(0,"a","train"),row(1,"a","validation"),row(2,"b","test")]
        with self.assertRaises(ValueError):validate_splits(data)
        self.assertEqual(len(validate_splits(data,demo=True)["train"]),1)
        data[1]["case_id"]=data[0]["case_id"]
        with self.assertRaises(ValueError):validate_splits(data,demo=True)
    def test_source_family_leakage(self):
        data=[row(0,"a","train"),row(1,"b","validation"),row(2,"c","test")]
        data[0]["source_family_id"]="same_book"
        data[1]["source_family_id"]="same_book"
        with self.assertRaises(ValueError):validate_splits(data)
    def test_source_revision_leakage_with_distinct_source_ids(self):
        data=[row(0,"a","train"),
              row(1,"b","validation","Peter entered the garden.","garden"),
              row(2,"c","test","The mouse carried peas.","peas")]
        data[0]["source_revision"]="same_file_hash"
        data[1]["source_revision"]="same_file_hash"
        with self.assertRaisesRegex(ValueError,"revision"):
            validate_splits(data)

    def test_renamed_duplicate_qa_pairs_rejected(self):
        data=[row(0,"a","train"),row(1,"b","validation"),
              row(2,"c","test","The mouse carried peas.","peas")]
        with self.assertRaisesRegex(ValueError,"duplicated"):
            validate_splits(data)

    def test_train_load_and_corruption(self):
        data=[row(0,"a","train"),row(1,"a","train","Flopsy ate blackberries.","blackberries"),
              row(2,"b","validation","Peter entered the garden.","garden"),
              row(3,"c","test","The mouse carried peas.","peas")]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"reader"
            report=train_reader(data,path,epochs=2,seed=1)
            self.assertEqual(report["metrics"]["test"]["count"],1)
            with self.assertRaisesRegex(ValueError,"disabled"):
                PassageReaderBundle(path)
            model=PassageReaderBundle(path,allow_experimental=True)
            self.assertIn(model.predict(data[0]["question"],data[0]["passage"])["status"],
                          {"no_answer","experimental_answer"})
            artifact=path/"vocab.json";artifact.write_text(artifact.read_text()+"\n")
            with self.assertRaisesRegex(ValueError,"checksum"):
                PassageReaderBundle(path,allow_experimental=True)

if __name__ == "__main__":unittest.main()
