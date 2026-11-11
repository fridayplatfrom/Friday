import unittest
import time
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tiny_experts.orchestrator import TinyExpertOrchestrator

FULL_CLINICAL_CASES = [
    # ----------------------------------------------------
    # DIVISION 1: FUNGI & OOMYCETES
    # ----------------------------------------------------
    {
        "id": "div1_01",
        "title": "Early Blight Concentric Rings",
        "query": "My tomato plant has dark brown concentric target rings on lower leaves with yellow halos. Is this early blight?",
        "expected": ["Early Blight", "Alternaria solani"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div1_02",
        "title": "Late Blight Oomycete Emergency",
        "query": "Tomato foliage shows large water-soaked olive lesions with white fuzzy sporulation on leaf undersides after heavy rain. What pathogen is this?",
        "expected": ["Late Blight", "Phytophthora infestans"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div1_03",
        "title": "Powdery Mildew Surface Epiphyte",
        "query": "Squash leaves have white talcum-powder patches across the upper leaf surface in dry warm weather. What is the diagnosis?",
        "expected": ["Powdery Mildew", "Podosphaera xanthii"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div1_04",
        "title": "Cucurbit Downy Mildew Oomycete",
        "query": "Cucumber leaves show angular yellow patches strictly bounded by leaf veins with purplish-grey spore fuzz on the bottom. What disease is this?",
        "expected": ["Downy Mildew", "Pseudoperonospora cubensis"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div1_05",
        "title": "Fusarium Vascular Wilt",
        "query": "One side of my tomato branch is severely wilting and cutting the lower stem reveals a dark brown ring in the vascular xylem bundle.",
        "expected": ["Fusarium Wilt", "Fusarium oxysporum"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div1_06",
        "title": "Wheat Stem Rust Basidiomycete",
        "query": "Wheat stems show elongated reddish-brown rust pustules bursting through leaf sheaths causing lodging. What is the fungus?",
        "expected": ["Wheat Stem Rust", "Puccinia graminis"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div1_07",
        "title": "Rice Blast Spindle Lesions",
        "query": "Rice leaves exhibit spindle-shaped diamond lesions with gray centers and dark brown margins, with bleached white panicles.",
        "expected": ["Rice Blast", "Magnaporthe oryzae"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div1_08",
        "title": "Fusarium Head Blight DON Mycotoxin",
        "query": "Wheat flowering heads have prematurely bleached spikelets with salmon-pink orange mold and shriveled grains producing vomitoxin.",
        "expected": ["Fusarium Head Blight", "Fusarium graminearum"],
        "division": "Division 1: Fungi & Oomycetes"
    },

    # ----------------------------------------------------
    # DIVISION 2: ADVANCED AGRICULTURAL BACTERIOLOGY
    # ----------------------------------------------------
    {
        "id": "div2_09",
        "title": "Fire Blight Shepherd's Crook",
        "query": "Apple and pear branch tips are hooked 180 degrees like a shepherd's crook with black scorched leaves and milky bacterial ooze.",
        "expected": ["Fire Blight", "Erwinia amylovora"],
        "division": "Division 2: Agricultural Bacteriology"
    },
    {
        "id": "div2_10",
        "title": "Bacterial Speck & Coronatine Toxin",
        "query": "Tiny pinpoint black specks with yellow halos on tomato leaves and raised black ground-pepper specks on green fruit.",
        "expected": ["Bacterial Speck", "Pseudomonas syringae"],
        "division": "Division 2: Agricultural Bacteriology"
    },
    {
        "id": "div2_11",
        "title": "Bacterial Soft Rot Pectate Lyase",
        "query": "Harvested potato tubers and cabbage heads turning into a foul-smelling, water-soaked, slimy liquid mush.",
        "expected": ["Bacterial Soft Rot", "Pectobacterium carotovorum"],
        "division": "Division 2: Agricultural Bacteriology"
    },
    {
        "id": "div2_12",
        "title": "Crown Gall Ti-Plasmid Tumors",
        "query": "Woody rough swollen tumors and galls forming at the soil crown and root junctions of rose and fruit trees.",
        "expected": ["Crown Gall", "Agrobacterium tumefaciens"],
        "division": "Division 2: Agricultural Bacteriology"
    },

    # ----------------------------------------------------
    # DIVISION 3: PLANT VIROLOGY & INSECT VECTORS
    # ----------------------------------------------------
    {
        "id": "div3_13",
        "title": "Tomato Brown Rugose Fruit Virus (ToBRFV)",
        "query": "Tomato fruits develop brown rugose wrinkled patches, yellow marbling, and leaves show narrow mosaic fern-leaf bubbling breaking resistance.",
        "expected": ["Tomato Brown Rugose Fruit Virus", "ToBRFV"],
        "division": "Division 3: Plant Virology & Vectors"
    },
    {
        "id": "div3_14",
        "title": "Tobacco Mosaic Virus (TMV)",
        "query": "Tomato and tobacco leaves show light and dark green mosaic mottling, distorted blistering, and stunted shoe-string leaves transmitted on hands.",
        "expected": ["Tobacco Mosaic Virus", "TMV"],
        "division": "Division 3: Plant Virology & Vectors"
    },
    {
        "id": "div3_15",
        "title": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "query": "Tomato plants are severely stunted and bushy with leaves curled tightly upward and yellow margins; clouds of silverleaf whiteflies present.",
        "expected": ["Tomato Yellow Leaf Curl Virus", "TYLCV"],
        "division": "Division 3: Plant Virology & Vectors"
    },
    {
        "id": "div3_16",
        "title": "Tomato Spotted Wilt Virus (TSWV)",
        "query": "Tomato foliage displays bronze spotting, terminal stem blighting, and ripening fruit has concentric yellow and necrotic ring spots from thrips.",
        "expected": ["Tomato Spotted Wilt Virus", "TSWV"],
        "division": "Division 3: Plant Virology & Vectors"
    },

    # ----------------------------------------------------
    # DIVISION 4: NEMATOLOGY & SOIL DISEASE COMPLEXES
    # ----------------------------------------------------
    {
        "id": "div4_17",
        "title": "Root Knot Nematode Galls",
        "query": "Tomato plants are stunted and wilting at midday; digging up roots reveals numerous swollen bumpy knots and galls.",
        "expected": ["Root Knot Nematode", "Meloidogyne incognita"],
        "division": "Division 4: Nematology & Soil Complexes"
    },
    {
        "id": "div4_18",
        "title": "Nematode-Fusarium Synergistic Complex",
        "query": "Tomato plants collapse rapidly with severe root galls and brown vascular xylem ring, breaking Fusarium resistance genes.",
        "expected": ["Nematode", "Fusarium"],
        "division": "Division 4: Nematology & Soil Complexes"
    },

    # ----------------------------------------------------
    # DIVISION 5: ABIOTIC & DIFFERENTIAL DIAGNOSIS
    # ----------------------------------------------------
    {
        "id": "div5_19",
        "title": "Blossom End Rot (Calcium Deficiency)",
        "query": "Tomatoes have dark, sunken, circular leathery black rot on the bottom of green fruits opposite the stem. What fungus is this and what spray should I use?",
        "expected": ["Blossom End Rot", "Calcium", "DO NOT APPLY FUNGICIDES"],
        "division": "Division 5: Abiotic & Differential Diagnosis"
    },
    {
        "id": "div5_20",
        "title": "2,4-D Herbicide Drift Fan Epinasty",
        "query": "Tomato leaves are suddenly twisting, cupping upward, narrowing like straps, and veins resemble a fan after neighbors sprayed lawn.",
        "expected": ["Herbicide Drift", "2,4-D"],
        "division": "Division 5: Abiotic & Differential Diagnosis"
    },
    {
        "id": "div5_21",
        "title": "Iron Deficiency Interveinal Chlorosis",
        "query": "Youngest uppermost tomato leaves show bright sharp interveinal yellowing while veins stay dark green in high pH alkaline soil.",
        "expected": ["Iron Deficiency", "Chlorosis"],
        "division": "Division 5: Abiotic & Differential Diagnosis"
    },

    # ----------------------------------------------------
    # DIVISION 6: CLINICAL LABORATORY ASSAYS
    # ----------------------------------------------------
    {
        "id": "div6_22",
        "title": "Rapid 3% KOH String Test",
        "query": "How to perform the rapid 3% KOH string test on a microscope slide to determine if bacteria is Gram negative?",
        "expected": ["KOH", "String Test", "Gram"],
        "division": "Division 6: Clinical Laboratory Assays"
    },
    {
        "id": "div6_23",
        "title": "Systemic Acquired Resistance (SAR)",
        "query": "How does salicylic acid signaling induce systemic acquired resistance and PR pathogenesis-related proteins in plants?",
        "expected": ["Systemic Acquired Resistance", "Salicylic"],
        "division": "Division 6: Clinical Laboratory Assays"
    },

    # ----------------------------------------------------
    # DIVISION 7: INDIAN AGRICULTURAL & TROPICAL STAPLE CROPS (ICAR / TNAU)
    # ----------------------------------------------------
    {
        "id": "div7_24",
        "title": "Rice Bacterial Leaf Blight Kresek",
        "query": "Rice seedlings roll inward, wilt, and die during early transplanting kresek phase with milky ooze.",
        "expected": ["Bacterial Leaf Blight", "Xanthomonas oryzae"],
        "division": "Division 2: Agricultural Bacteriology"
    },
    {
        "id": "div7_25",
        "title": "Rice Sheath Blight Snake-Skin Lesions",
        "query": "Rice leaf sheaths above water line develop snake-skin lesions with dark brown borders and black sclerotia.",
        "expected": ["Sheath Blight", "Rhizoctonia solani"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div7_26",
        "title": "Cotton Leaf Curl Virus Enations",
        "query": "Cotton leaves curling upward with swollen thickened veins and diagnostic cup-shaped enation leaf outgrowths underneath.",
        "expected": ["Cotton Leaf Curl Virus", "CLCuV"],
        "division": "Division 3: Plant Virology & Vectors"
    },
    {
        "id": "div7_27",
        "title": "Cotton Bacterial Blight Black Arm",
        "query": "Cotton leaves show water-soaked angular spots bounded by veins spreading into jet-black girdling cankers called black arm.",
        "expected": ["Bacterial Blight", "Xanthomonas citri"],
        "division": "Division 2: Agricultural Bacteriology"
    },
    {
        "id": "div7_28",
        "title": "Chickpea Fusarium Drooping Wilt",
        "query": "Chickpea seedlings exhibit sudden drooping of petioles and splitting taproot reveals dark brown internal xylem ring.",
        "expected": ["Fusarium", "ciceri"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div7_29",
        "title": "Pigeonpea Sterility Mosaic Disease",
        "query": "Pigeonpea arhar plants are bushy, stunted, with mosaic leaves and complete failure to produce flowers or pods.",
        "expected": ["Sterility Mosaic", "PSMV"],
        "division": "Division 3: Plant Virology & Vectors"
    },
    {
        "id": "div7_30",
        "title": "Sugarcane Red Rot Alcoholic Fermentation",
        "query": "Sugarcane top leaves wither and splitting the stalk longitudinally reveals blood-red pith with white transverse patches and sour alcoholic fermentation odor.",
        "expected": ["Red Rot", "Colletotrichum falcatum"],
        "division": "Division 1: Fungi & Oomycetes"
    },
    {
        "id": "div7_31",
        "title": "Citrus Greening Huanglongbing Psyllid",
        "query": "Nagpur mandarin and sweet orange trees show asymmetric blotchy mottle leaves and small lopsided bitter green fruit.",
        "expected": ["Citrus Greening", "Huanglongbing", "Liberibacter"],
        "division": "Division 2: Agricultural Bacteriology"
    },
    {
        "id": "div7_32",
        "title": "Mango Cauliflower Floral Malformation",
        "query": "Mango panicles turn into hypertrophied, hyper-branched, compact fleshy cauliflower-like male clusters with zero fruit set.",
        "expected": ["Mango Malformation", "Fusarium mangiferae"],
        "division": "Division 1: Fungi & Oomycetes"
    }
]

def run_world_class_evaluation():
    orchestrator = TinyExpertOrchestrator(verbose=False)
    
    print("\n" + "=" * 80)
    print("  [RESEARCH EVALUATION] FULL 6-DIVISION PLANT PATHOLOGY CLINICAL EXAMINATION")
    print("=" * 80)
    print(f"{'#':<3} | {'Clinical Case Title':<34} | {'Division':<23} | {'Status':<7} | {'Latency':<8}")
    print("-" * 80)

    passed = 0
    total = len(FULL_CLINICAL_CASES)
    latencies = []

    for idx, case in enumerate(FULL_CLINICAL_CASES, 1):
        start = time.perf_counter()
        detailed = orchestrator.process_detailed(query=case["query"])
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

        text_out = detailed["final_output"].lower()

        is_passed = any(exp.lower() in text_out for exp in case["expected"])

        if is_passed:
            passed += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"

        print(f"{idx:02d} | {case['title']:<34} | {case['division'][:22]:<23} | {status:<7} | {latency:.2f} ms")

    acc = (passed / total) * 100
    avg_lat = sum(latencies) / len(latencies)

    print("=" * 80)
    print(f"  CLINICAL EXAMINATION SCORE: {passed}/{total} ({acc:.1f}%)")
    print(f"  AVERAGE CPU RESPONSE SPEED: {avg_lat:.2f} ms")
    print(f"  DIVISIONS TESTED:           All 6 Specialized Clinical Divisions")
    print("=" * 80 + "\n")

    return passed, total

if __name__ == "__main__":
    run_world_class_evaluation()
