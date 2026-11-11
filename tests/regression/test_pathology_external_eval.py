import csv
import tempfile
import unittest
from pathlib import Path
from pathology_external_eval import scan_splits, score_predictions

FIELDS=["qa_id","image_id","crop","disease","question_category","question_text","answer"]
class PublicPathologyEvaluationTests(unittest.TestCase):
    def test_dataset_splits_and_requires_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"data").mkdir()
            for file,label in (("train.csv","a"),("val.csv","b"),("test.csv","c")):
                with (root/"data"/file).open("w",newline="",encoding="utf-8") as f:
                    writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
                    writer.writerow(dict(zip(FIELDS,[label,label,"tomato","late blight",
                         "Specific Disease Identification","What is in the image?","late blight"])))
            result=scan_splits(root)
            self.assertEqual(result["test"]["eligible_disease_questions"],1)
            with self.assertRaisesRegex(ValueError,"requires image"):
                score_predictions(result,[{"qa_id":"c","disease_prediction":"late blight","used_image":False}])
            scored=score_predictions(result,[{"qa_id":"c","disease_prediction":"late blight","used_image":True}])
            self.assertEqual(scored["selective_accuracy"],1)
            with (root/"data"/"val.csv").open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
                writer.writerow(dict(zip(FIELDS,["b","a","tomato","late blight",
                    "Specific Disease Identification","Question","late blight"])))
            with self.assertRaisesRegex(ValueError,"leaks"):
                scan_splits(root)
if __name__=="__main__":unittest.main()
