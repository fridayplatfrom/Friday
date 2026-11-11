"""External pathology evaluation on the publisher's PlantExpertVQA CSV splits.

This dataset contains image-grounded questions. No diagnosis metric is
reported without actual image-conditioned model predictions. Source:
https://huggingface.co/datasets/SyedNazmusSakib/PlantExpertVQA
"""
import argparse
import csv
import json
from pathlib import Path

REQUIRED = {"qa_id","image_id","crop","disease","question_category","question_text"}
TARGET = "specific disease identification"

def scan_splits(root, *, max_rows=None):
    root = Path(root)
    found, membership, qa_ids = {}, {}, set()
    for split, filenames in (("train",["train.csv"]),("validation",["val.csv","validation.csv"]),("test",["test.csv"])):
        path=next((root/"data"/name for name in filenames if (root/"data"/name).is_file()),None)
        if path is None:
            raise FileNotFoundError(f"Official dataset CSV for {split} is missing")
        counts=0; candidates={}; empty=0
        with path.open(encoding="utf-8-sig",newline="") as stream:
            reader=csv.DictReader(stream)
            if reader.fieldnames is None or not REQUIRED.issubset(reader.fieldnames):
                raise ValueError(f"CSV schema mismatch: {split}")
            for entry in reader:
                if max_rows is not None and counts >= max_rows:break
                counts+=1
                qa,image=entry["qa_id"],entry["image_id"]
                if not qa or not image or qa in qa_ids:
                    raise ValueError(f"Duplicate/invalid QA or image ID: {split}/{qa}")
                qa_ids.add(qa)
                earlier=membership.setdefault(image,split)
                if earlier != split:
                    raise ValueError(f"Image ID leaks between {earlier} and {split}: {image}")
                if not entry["question_text"] or not entry.get("answer"):
                    empty+=1;continue
                if entry["question_category"].casefold().strip()==TARGET:
                    candidates[qa]=entry
        found[split]={"all_rows":counts,"eligible_disease_questions":len(candidates),
                      "empty_question_or_answer":empty,"rows":candidates}
    return found

def score_predictions(splits, predictions):
    gold=splits["test"]["rows"];seen=set();attempted=hits=0
    for pred in predictions:
        if not isinstance(pred,dict) or pred.get("qa_id") not in gold:
            raise ValueError("Predictions must reference official eligible test IDs only")
        key=pred["qa_id"]
        if key in seen:raise ValueError("Duplicate QA prediction")
        seen.add(key)
        if pred.get("used_image") is not True:
            raise ValueError("Image-grounded pathology evaluation requires image input")
        if pred.get("abstain") is True:continue
        label=pred.get("disease_prediction")
        if not isinstance(label,str):raise ValueError("Disease prediction string required")
        attempted+=1
        hits+=label.strip().casefold()==gold[key]["disease"].strip().casefold()
    n=len(gold)
    return {"eligible_test_rows":n,"evaluated_predictions":len(seen),
            "coverage":attempted/n if n else None,
            "selective_accuracy":hits/attempted if attempted else None,
            "overall_accuracy_with_abstentions_wrong":hits/n if n else None,
            "review_status":"published_labels_not_independently_rechecked_in_this_run",
            "limitations":"Requires actual images and official held-out labels, not text-only questions."}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset-root",required=True,type=Path)
    p.add_argument("--predictions",type=Path)
    p.add_argument("--max-rows",type=int)
    a=p.parse_args(argv)
    try:
        data=scan_splits(a.dataset_root,max_rows=a.max_rows)
        result={"dataset":"SyedNazmusSakib/PlantExpertVQA",
                "source":"https://huggingface.co/datasets/SyedNazmusSakib/PlantExpertVQA",
                "official_split_summary":{k:{name:value for name,value in v.items() if name!="rows"}
                                         for k,v in data.items()},
                "status":"split_integrity_checked_only","image_model_accuracy":None,
                "warning":"Image-grounded disease diagnosis cannot be evaluated from questions alone."}
        if a.predictions:
            predictions=[json.loads(line) for line in a.predictions.read_text(encoding="utf-8").splitlines() if line.strip()]
            result["predictions"]=score_predictions(data,predictions)
            result["status"]="scored_image_grounded_predictions"
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError) as e:
        print(json.dumps({"status":"blocked","error":str(e)}));return 1
if __name__=="__main__":raise SystemExit(main())
