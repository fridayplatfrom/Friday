import unittest
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tiny_experts.orchestrator import TinyExpertOrchestrator

PATHOLOGY_CLINICAL_CASES = [
    {
        "id": "case_1",
        "title": "Early Blight vs Late Blight Differentiation",
        "query": "My tomato plant has dark brown concentric target rings on lower leaves with yellow halos. Is this early blight or late blight?",
        "expected_disease": "Early Blight",
        "expected_pathogen": "Alternaria solani",
        "expected_kingdom": "Fungus"
    },
    {
        "id": "case_2",
        "title": "Late Blight Oomycete Emergency",
        "query": "Tomato foliage shows large water-soaked olive lesions with white fuzzy sporulation on leaf undersides after heavy rain. What pathogen is this?",
        "expected_disease": "Late Blight",
        "expected_pathogen": "Phytophthora infestans",
        "expected_kingdom": "Oomycete"
    },
    {
        "id": "case_3",
        "title": "Powdery Mildew vs Downy Mildew",
        "query": "Squash leaves have white talcum-powder patches across the upper leaf surface in dry warm weather. What is the diagnosis?",
        "expected_disease": "Powdery Mildew",
        "expected_pathogen": "Podosphaera xanthii",
        "expected_kingdom": "Fungus"
    },
    {
        "id": "case_4",
        "title": "Downy Mildew Oomycete Infection",
        "query": "Cucumber leaves show angular yellow patches strictly bounded by leaf veins with purplish-grey spore fuzz on the bottom. What disease is this?",
        "expected_disease": "Downy Mildew",
        "expected_pathogen": "Pseudoperonospora cubensis",
        "expected_kingdom": "Oomycete"
    },
    {
        "id": "case_5",
        "title": "Fusarium Vascular Wilt",
        "query": "One side of my tomato branch is severely wilting and cutting the lower stem reveals a dark brown ring in the vascular xylem bundle.",
        "expected_disease": "Fusarium Wilt",
        "expected_pathogen": "Fusarium oxysporum",
        "expected_kingdom": "Fungus"
    },
    {
        "id": "case_6",
        "title": "Bacterial Spot Infection",
        "query": "Pepper leaves exhibit small water-soaked greasy spots that turn black with a pronounced yellow halo during hot humid thunderstorms.",
        "expected_disease": "Bacterial Spot",
        "expected_pathogen": "Xanthomonas campestris",
        "expected_kingdom": "Bacterium"
    },
    {
        "id": "case_7",
        "title": "Grey Mold Necrotrophic Decay",
        "query": "Ripening strawberries are rotting with a dense fuzzy velvety grey spore blanket covering the soft collapsed fruit.",
        "expected_disease": "Grey Mold",
        "expected_pathogen": "Botrytis cinerea",
        "expected_kingdom": "Fungus"
    },
    {
        "id": "case_8",
        "title": "Rose Black Spot",
        "query": "Rose bush leaves develop distinct circular black spots with fringed feathery margins followed by extensive leaf yellowing and defoliation.",
        "expected_disease": "Black Spot",
        "expected_pathogen": "Diplocarpon rosae",
        "expected_kingdom": "Fungus"
    },
    {
        "id": "case_9",
        "title": "Apple Scab Infection",
        "query": "Apple tree leaves and young developing fruit show olive-green velvety spots that turn corky, dark brown, and scabby.",
        "expected_disease": "Apple Scab",
        "expected_pathogen": "Venturia inaequalis",
        "expected_kingdom": "Fungus"
    },
    {
        "id": "case_10",
        "title": "Systemic Acquired Resistance Signaling",
        "query": "How does salicylic acid signaling induce systemic acquired resistance and PR pathogenesis-related proteins in plants?",
        "expected_concept": "Systemic Acquired Resistance",
        "expected_signaling": "Salicylic acid"
    }
]

def evaluate_baseline():
    orchestrator = TinyExpertOrchestrator(verbose=False)
    passed = 0
    total = len(PATHOLOGY_CLINICAL_CASES)

    print("\n========================================================")
    print("  [PHASE 1: BEFORE-TRAINING CLINICAL PATHOLOGY BASELINE]")
    print("========================================================")

    for idx, case in enumerate(PATHOLOGY_CLINICAL_CASES, 1):
        start = time.perf_counter()
        detailed = orchestrator.process_detailed(query=case["query"])
        latency = (time.perf_counter() - start) * 1000

        text_out = detailed["final_output"].lower()
        tele = detailed.get("telemetry", {}).get("pathology", {})

        is_passed = False
        if "expected_disease" in case:
            if case["expected_disease"].lower() in text_out or case["expected_pathogen"].lower() in text_out:
                is_passed = True
        elif "expected_concept" in case:
            if case["expected_concept"].lower() in text_out or case["expected_signaling"].lower() in text_out:
                is_passed = True

        if is_passed:
            passed += 1
            status = "[PASS]"
        else:
            status = "[FAIL: Gaps in Pathogen Taxonomy]"

        print(f"  [{idx:02d}/{total:02d}] {status:<35} | {case['title']} ({latency:.2f} ms)")

    accuracy = (passed / total) * 100
    print("\n" + "=" * 64)
    print(f"  BASELINE PRE-TRAINING ACCURACY: {passed}/{total} ({accuracy:.1f}%)")
    print("=" * 64 + "\n")
    return passed, total

if __name__ == "__main__":
    evaluate_baseline()
