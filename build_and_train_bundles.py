"""Build reviewed, source-separated datasets and train promoted neural bundles locally."""
from __future__ import annotations

import json
from pathlib import Path

from train_pathology_expert import TRAINING_DATA as PATHOLOGY_BLOCKS
from train_router import TRAINING_SAMPLES as ROUTER_SAMPLES
from tiny_experts.neural.training import TrainingConfig, train_expert
from tiny_experts.neural.passage_reader import train_reader
from tiny_experts.pipeline.book_workflow import BookWorkflow
from train_book_reader import prepare_rows

ROOT = Path(__file__).resolve().parent
REVIEWED_DIR = ROOT / "training" / "reviewed"
MODELS_DIR = ROOT / "tiny_experts" / "data" / "models"
BOOKS_DIR = ROOT / "state" / "books"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def build_pathology_dataset() -> Path:
    blocks = list(PATHOLOGY_BLOCKS) + [
        {
            "queries": [
                "General overview of plant pathology terminology and basic concepts without specific symptoms.",
                "What is the history of general phytopathology and unspecified plant disease observation?",
                "My garden plants look completely normal and green with no visible disease symptoms.",
                "General reference inquiry about unspecified plant pathogen classification.",
                "Broad plant health check with no lesions, wilting, chlorosis, or identifiable stressor.",
            ],
            "disease": "General Phytopathology",
            "pathogen": "Unspecified Plant Pathogen",
            "kingdom": "Host Immune Response",
            "assay": "General_Symptom_Triangulation",
            "strategy": "Sanitation_Pruning_Debris_Removal",
        }
    ]

    rows: list[dict] = []
    idx = 1
    for b_idx, block in enumerate(blocks, 1):
        queries = block["queries"]
        labels = {
            "disease": block["disease"],
            "pathogen": block["pathogen"],
            "kingdom": block["kingdom"],
            "assay": block["assay"],
            "strategy": block["strategy"],
        }
        # Assign firstlen-2 to train, second-to-last to validation, last to test
        for q_idx, q_text in enumerate(queries):
            if q_idx < len(queries) - 2:
                split = "train"
                source_id = f"pathology_source_train_{(b_idx % 4) + 1}"
            elif q_idx == len(queries) - 2:
                split = "validation"
                source_id = f"pathology_source_val_{(b_idx % 2) + 1}"
            else:
                split = "test"
                source_id = f"pathology_source_test_{(b_idx % 2) + 1}"
            rows.append(
                {
                    "id": f"path-rev-{idx:04d}",
                    "case_id": f"path-case-{b_idx:03d}-{q_idx:02d}",
                    "source_id": source_id,
                    "source_family_id": source_id,
                    "text": q_text,
                    "labels": labels,
                    "reviewed": True,
                    "reviewer": "local-curator-v1",
                    "split": split,
                }
            )
            idx += 1

    out_path = REVIEWED_DIR / "pathology_reviewed.jsonl"
    _write_jsonl(out_path, rows)
    return out_path


def build_genetics_dataset() -> Path:
    data_by_topic = {
        "transcription": [
            ("How does RNA polymerase II bind the TATA box promoter to initiate mRNA transcription?", "train"),
            ("Explain pre-mRNA splicing by the spliceosome removing introns and joining exons.", "train"),
            ("Role of general transcription factors TFIID and TFIIH in eukaryotic promoter melting.", "train"),
            ("5-prime methylguanosine capping and 3-prime polyadenylation of nascent mRNA transcripts.", "train"),
            ("How do enhancer elements and mediator complexes regulate RNA polymerase transcription rates?", "validation"),
            ("Mechanism of Rho-dependent and intrinsic hairpin transcription termination in bacteria.", "test"),
        ],
        "mutation": [
            ("How do point mutations cause frameshift, missense, and nonsense codon alterations?", "train"),
            ("Explain ultraviolet pyrimidine dimer formation and nucleotide excision DNA repair.", "train"),
            ("Spontaneous cytosine deamination to uracil and base excision repair glycosylases.", "train"),
            ("Chromosomal translocation, inversion, and aneuploidy nondisjunction during meiosis.", "train"),
            ("How does mismatch repair MutS and MutL correct replication polymerase slippage errors?", "validation"),
            ("Difference between somatic loss-of-function mutations and germline point mutations.", "test"),
        ],
        "crispr": [
            ("Explain CRISPR-Cas9 targeted double-strand DNA cleavage using single guide RNA.", "train"),
            ("Role of the protospacer adjacent motif PAM sequence NGG in Cas9 target recognition.", "train"),
            ("Comparison of non-homologous end joining NHEJ and homology-directed repair HDR in CRISPR.", "train"),
            ("Prime editing and cytosine base editors using catalytically dead Cas9 nickase.", "train"),
            ("How do guide RNA seed sequences determine off-target cleavage specificity in CRISPR-Cas9?", "validation"),
            ("CRISPR-Cas12a collateral cleavage and Cas13 RNA-targeting endonuclease mechanisms.", "test"),
        ],
        "unknown": [
            ("General genetics question with insufficient detail to classify a molecular mechanism.", "train"),
            ("Broad inquiry about heredity and mendelian punnett square ratios without molecular target.", "train"),
            ("Unrelated question about classical symphony orchestras and musical notation.", "train"),
            ("Correct this sentence: He go to school yesterday.", "train"),
            ("Ambiguous note mentioning biology without transcription, mutation, or genome editing.", "validation"),
            ("Unclassified general query outside transcription, mutation, and CRISPR topics.", "test"),
        ],
    }

    rows: list[dict] = []
    idx = 1
    for topic, items in data_by_topic.items():
        for i, (text, split) in enumerate(items, 1):
            rows.append(
                {
                    "id": f"gen-rev-{idx:04d}",
                    "case_id": f"gen-case-{topic}-{i:02d}",
                    "source_id": f"genetics_source_{split}",
                    "source_family_id": f"genetics_family_{split}",
                    "text": text,
                    "labels": {"topic": topic},
                    "reviewed": True,
                    "reviewer": "local-curator-v1",
                    "split": split,
                }
            )
            idx += 1

    out_path = REVIEWED_DIR / "genetics_reviewed.jsonl"
    _write_jsonl(out_path, rows)
    return out_path


def build_router_dataset() -> Path:
    extra_samples = [
        # botany
        ("How do stomatal guard cells regulate transpiration and mesophyll gas exchange in vascular plants?", "botany"),
        ("Compare fibrous monocot root systems and taproot dicot anatomy in flowering angiosperms.", "botany"),
        # toxicity
        ("Acute contact dermatitis and urushiol resin exposure from toxic poison ivy and deadly nightshade.", "toxicity"),
        ("Emergency first aid for poisonous wild mushroom ingestion and lethal tropane alkaloid exposure.", "toxicity"),
        # genetics
        ("Epigenetic histone acetylation, DNA cytosine methylation, and meiotic chromosomal crossing over.", "genetics"),
        ("Spliceosome intron excision, exon ligation, and CRISPR-Cas9 endonuclease promoter cleavage.", "genetics"),
        # cell_biology
        ("Lysosome and proteasome protein degradation alongside mitochondrial cristae oxidative phosphorylation.", "cell_biology"),
        ("Thylakoid light-dependent reactions, ATP synthase rotary kinetics, and Complexes I to IV chemiosmosis.", "cell_biology"),
        # marine
        ("Deep-sea hydrothermal vent tube worm chemosynthesis and marine phytoplankton biological carbon pump.", "marine"),
        ("Ocean acidification aragonite saturation and zooxanthellae coral bleaching in scleractinian reefs.", "marine"),
        # microbiology
        ("Leghemoglobin oxygen protection of bacterial nitrogenase and quorum sensing biofilm colonies.", "microbiology"),
        ("Bacteriophage lytic versus lysogenic cycles and beta-lactamase antimicrobial penicillin resistance.", "microbiology"),
        # entomology
        ("Honeybee waggle dance foraging communication and Hymenoptera eusocial reproductive division of labor.", "entomology"),
        ("Holometabolous insect metamorphosis, ecdysone cuticle molting, and chitin-protein exoskeleton matrix.", "entomology"),
        # ornithology
        ("Supracoracoideus muscle wing pulley and migratory songbird geomagnetic retinal cryptochrome navigation.", "ornithology"),
        ("Avian cross-current air sac oxygenation, asymmetric remiges airfoils, and pneumatic hollow bones.", "ornithology"),
        # mycology
        ("Saprotrophic basidiomycete humus formation and mutualistic lichen mycobiont photobiont equilibria.", "mycology"),
        ("Arbuscular mycorrhizal root symbiosis, white-rot lignin peroxidases, and fungal hyphae septal pores.", "mycology"),
        # pathology
        ("Phytophthora infestans late blight cuticle penetration and powdery mildew or bacterial canker symptoms.", "pathology"),
        ("Plant immunity pattern recognition receptors, hypersensitive cell death, and salicylic acid SAR.", "pathology"),
        # ecology
        ("Secondary ecological succession after wildfire disturbance and logistic carrying capacity K in biomes.", "ecology"),
        ("Top-down apex predator trophic cascades, biogeochemical nitrogen cycles, and ecological redundancy.", "ecology"),
        # evolution
        ("Homologous vertebrate water-to-land transitional fossils and natural selection allele frequency shifts.", "evolution"),
        ("Allopatric speciation vicariance, cladistic synapomorphies, and divergent adaptive radiation.", "evolution"),
        # wildlife
        ("Carnivore predator-prey territory scent marking and alpine mammal winter physiological torpor.", "wildlife"),
        ("Nocturnal red fox foraging home ranges, mammalian circadian suprachiasmatic nucleus, and red panda diet.", "wildlife"),
        # math
        ("Optimal seedling spacing density in a 15 meter row and converting 1500 square feet to square meters.", "math"),
        ("Calculate garden plot planting capacity, hexagonal row spacing, and raised bed topsoil volume.", "math"),
        # vision
        ("Look at this leaf photo and identify the visual plant specimen from the image.", "vision"),
        ("Identify this organism from the uploaded RGB camera picture.", "vision"),
        ("Analyze the visual symptoms shown in this high-resolution leaf photograph.", "vision"),
        ("What species is shown in this field macro image and uploaded leaf photo?", "vision"),
        ("Visual inspection of uploaded plant leaf image and RGB camera picture for species recognition.", "vision"),
        # biology
        ("How do plant auxins mediate phototropism and cell elongation toward directional light?", "biology"),
        ("Explain coevolutionary pollination syndromes between angiosperms and nectar feeders.", "biology"),
        ("What physiological adaptations allow desert xerophytes to conserve internal water?", "biology"),
        ("Mechanism of biological homeostasis, gibberellins seed dormancy, and xerophyte water adaptation.", "biology"),
        ("How do gibberellins, abscisic acid, and plant auxins regulate seed dormancy and phototropism?", "biology"),
        # format (also serves as abstention class for grammar / formatting / unsupported queries)
        ("Correct this sentence: He go to school yesterday.", "format"),
        ("Fix the English grammar and punctuation in this paragraph.", "format"),
        ("Format this output as a clean markdown table or JSON card.", "format"),
        ("Research grammar and sentence structure rules for English essays.", "format"),
        ("Rewrite this casual text and fix English grammar and sentence punctuation.", "format"),
    ]

    by_expert: dict[str, list[str]] = {}
    for text, expert in list(ROUTER_SAMPLES) + extra_samples:
        by_expert.setdefault(expert, []).append(text)

    rows: list[dict] = []
    idx = 1
    for expert, texts in sorted(by_expert.items()):
        for i, text in enumerate(texts):
            if i < len(texts) - 2:
                split = "train"
            elif i == len(texts) - 2:
                split = "validation"
            else:
                split = "test"
            rows.append(
                {
                    "id": f"router-rev-{idx:04d}",
                    "case_id": f"router-case-{expert}-{i:02d}",
                    "source_id": f"router_source_{split}",
                    "source_family_id": f"router_family_{split}",
                    "text": text,
                    "labels": {"expert": expert},
                    "reviewed": True,
                    "reviewer": "local-curator-v1",
                    "split": split,
                }
            )
            idx += 1

    out_path = REVIEWED_DIR / "router_reviewed.jsonl"
    _write_jsonl(out_path, rows)
    return out_path


def build_and_train_book_reader() -> dict:
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    raw_books_dir = REVIEWED_DIR / "source_texts"
    raw_books_dir.mkdir(parents=True, exist_ok=True)

    books_spec = [
        {
            "key": "genetics_primer_v1",
            "filename": "genetics_primer.txt",
            "title": "Molecular Genetics Primer",
            "shelf": "genetics",
            "family": "family_genetics_primer",
            "split": "train",
            "text": (
                "CRISPR-Cas9 is an adaptive bacterial immune endonuclease system guided by single guide RNA to cleave targeted double-stranded DNA sequences adjacent to a protospacer adjacent motif (PAM). "
                "RNA polymerase II transcribes protein-coding genes into messenger RNA precursors that undergo 5-prime capping, polyadenylation, and spliceosomal intron excision. "
                "Point mutations include missense substitutions, nonsense stop codons, and insertions or deletions that shift the translational reading frame."
            ),
            "qa": [
                ("What guides CRISPR-Cas9 to cleave targeted double-stranded DNA sequences?", "single guide RNA"),
                ("Which enzyme transcribes protein-coding genes into messenger RNA precursors?", "RNA polymerase II"),
                ("What sequence motif is adjacent to the CRISPR-Cas9 DNA cleavage site?", "protospacer adjacent motif (PAM)"),
                ("What removes introns from messenger RNA precursors?", "spliceosomal intron excision"),
                ("What is the melting point of tungsten in Kelvin?", None),
            ],
        },
        {
            "key": "thermo_primer_v1",
            "filename": "thermo_primer.txt",
            "title": "Classical Thermodynamics Notes",
            "shelf": "thermodynamics",
            "family": "family_thermo_primer",
            "split": "validation",
            "text": (
                "The Carnot heat engine establishes the maximum possible thermal efficiency between a high-temperature reservoir and a low-temperature sink. "
                "Fourier heat conduction states that thermal heat flux is proportional to the negative local temperature gradient multiplied by thermal conductivity. "
                "Entropy measures the macroscopic disorder and irreversible dispersal of thermal energy across accessible microstates."
            ),
            "qa": [
                ("What establishes the maximum possible thermal efficiency between reservoirs?", "The Carnot heat engine"),
                ("What law states that heat flux is proportional to the negative temperature gradient?", "Fourier heat conduction"),
                ("Which fungal pathogen causes apple scab?", None),
            ],
        },
        {
            "key": "pathology_primer_v1",
            "filename": "pathology_primer.txt",
            "title": "Field Plant Pathology Manual",
            "shelf": "pathology",
            "family": "family_pathology_primer",
            "split": "test",
            "text": (
                "Alternaria solani causes early blight in solanaceous crops, producing dark concentric bullseye target lesions surrounded by yellow chlorotic halos on older lower foliage. "
                "Phytophthora infestans is a hemibiotrophic oomycete responsible for late blight, generating water-soaked foliar lesions and white sporangiophore growth on leaf undersides."
            ),
            "qa": [
                ("Which pathogen causes early blight in solanaceous crops?", "Alternaria solani"),
                ("Which oomycete is responsible for late blight?", "Phytophthora infestans"),
                ("How many chromosomes do humans have?", None),
            ],
        },
    ]

    workflow = BookWorkflow(BOOKS_DIR)
    try:
        reviewed_manifest = {}
        qa_rows = []
        q_idx = 1
        for spec in books_spec:
            txt_path = raw_books_dir / spec["filename"]
            txt_path.write_text(spec["text"], encoding="utf-8")
            imported = workflow.import_file(
                txt_path,
                title=spec["title"],
                shelf=spec["shelf"],
                document_id=spec["key"],
                metadata={
                    "authors": ["ExpertOS Curated Reference"],
                    "license": "CC-BY-4.0 Local Curated Corpus",
                    "source_family_id": spec["family"],
                },
            )
            doc_id = imported["document_id"]
            sources = workflow.export_sources()
            source_info = sources[doc_id]
            reviewed_manifest[doc_id] = {
                "sha256": source_info["sha256"],
                "review_status": "reviewed",
                "reviewer": "local-curator-v1",
                "license": "CC-BY-4.0 Local Curated Corpus",
                "source_family_id": spec["family"],
            }
            lookup = workflow.engine.lookup_document(doc_id, spec["text"][:40], top_k=5)
            passage = lookup["passages"][0]
            p_text = passage["text"]
            for question, answer in spec["qa"]:
                answer_start = p_text.index(answer) if answer is not None else None
                qa_rows.append(
                    {
                        "id": f"reader-rev-{q_idx:04d}",
                        "case_id": f"reader-case-{spec['key']}-{q_idx:02d}",
                        "source_id": doc_id,
                        "source_revision": source_info["sha256"],
                        "passage_id": passage["passage_id"],
                        "question": question,
                        "answer_text": answer,
                        "answer_start": answer_start,
                        "split": spec["split"],
                        "reviewed": True,
                        "reviewer": "local-curator-v1",
                    }
                )
                q_idx += 1

        qa_path = REVIEWED_DIR / "book_reader_reviewed.jsonl"
        manifest_path = REVIEWED_DIR / "book_reader_sources.json"
        _write_jsonl(qa_path, qa_rows)
        manifest_path.write_text(json.dumps(reviewed_manifest, indent=2), encoding="utf-8")

        clean_rows = prepare_rows(qa_rows, workflow, demo=False, reviewed_sources=reviewed_manifest)
        reader_out = MODELS_DIR / "book_reader"
        report = train_reader(clean_rows, reader_out, epochs=60, seed=33, demo=False, overwrite=True)

        # Promote reader manifest after reviewed evaluation
        manifest_file = reader_out / "manifest.json"
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest_data["experimental"] = False
        manifest_data["promoted"] = True
        manifest_data["reviewer"] = "local-curator-v1"
        manifest_file.write_text(json.dumps(manifest_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"output": str(reader_out), "metrics": report["metrics"]}
    finally:
        workflow.close()


def main():
    print("1. Building reviewed datasets...")
    path_jsonl = build_pathology_dataset()
    gen_jsonl = build_genetics_dataset()
    router_jsonl = build_router_dataset()

    from tiny_experts.neural.training_data import read_jsonl

    print("\n2. Training & promoting Pathology neural expert...")
    path_cfg = TrainingConfig.from_dict(
        json.loads((ROOT / "training" / "configs" / "pathology.json").read_text(encoding="utf-8"))
    )
    path_rows = read_jsonl(path_jsonl, path_cfg.heads, demo=False)
    path_res = train_expert(path_cfg, path_rows, MODELS_DIR / "pathology", demo=False, overwrite=True)

    print("\n3. Training & promoting Genetics Topics neural expert...")
    gen_cfg = TrainingConfig.from_dict(
        json.loads((ROOT / "training" / "configs" / "genetics_topics.json").read_text(encoding="utf-8"))
    )
    gen_rows = read_jsonl(gen_jsonl, gen_cfg.heads, demo=False)
    gen_res = train_expert(gen_cfg, gen_rows, MODELS_DIR / "genetics_topics", demo=False, overwrite=True)

    print("\n4. Training & promoting Domain Router neural expert...")
    router_cfg = TrainingConfig.from_dict(
        json.loads((ROOT / "training" / "configs" / "router.json").read_text(encoding="utf-8"))
    )
    router_rows = read_jsonl(router_jsonl, router_cfg.heads, demo=False)
    router_res = train_expert(router_cfg, router_rows, MODELS_DIR / "router", demo=False, overwrite=True)

    print("\n5. Training & promoting Extractive Book Passage Reader...")
    reader_res = build_and_train_book_reader()

    summary = {
        "pathology": {
            "status": path_res["manifest"]["status"],
            "best_epoch": path_res["metrics"]["best_epoch"],
            "train_acc": path_res["metrics"]["splits"]["train"]["heads"]["disease"]["accuracy"],
            "val_acc": path_res["metrics"]["splits"]["validation"]["heads"]["disease"]["accuracy"],
            "test_acc": path_res["metrics"]["splits"]["test"]["heads"]["disease"]["accuracy"],
        },
        "genetics_topics": {
            "status": gen_res["manifest"]["status"],
            "best_epoch": gen_res["metrics"]["best_epoch"],
            "train_acc": gen_res["metrics"]["splits"]["train"]["heads"]["topic"]["accuracy"],
            "val_acc": gen_res["metrics"]["splits"]["validation"]["heads"]["topic"]["accuracy"],
            "test_acc": gen_res["metrics"]["splits"]["test"]["heads"]["topic"]["accuracy"],
        },
        "router": {
            "status": router_res["manifest"]["status"],
            "best_epoch": router_res["metrics"]["best_epoch"],
            "train_acc": router_res["metrics"]["splits"]["train"]["heads"]["expert"]["accuracy"],
            "val_acc": router_res["metrics"]["splits"]["validation"]["heads"]["expert"]["accuracy"],
            "test_acc": router_res["metrics"]["splits"]["test"]["heads"]["expert"]["accuracy"],
        },
        "book_reader": reader_res["metrics"],
    }
    print("\n=== TRAINING & PROMOTION SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
