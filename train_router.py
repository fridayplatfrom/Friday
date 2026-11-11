"""Train a small supervised domain router; legacy examples are unreviewed demos.

This is not a transformer mixture-of-experts model. The router's labels select
application capabilities, and the manifest fixes the vocabulary and dimensions.
"""

from pathlib import Path

TRAINING_SAMPLES = [
    # Botany
    ("What are the sunlight, watering, and soil requirements for this flowering plant?", "botany"),
    ("How do xylem and phloem transport sap throughout vascular plant structures?", "botany"),
    ("Pruning instructions for deciduous shrubs during dormant winter periods.", "botany"),
    ("How does stomatal conductance regulate transpiration rates in mesophyll tissue?", "botany"),
    ("Explain the difference between monocot and dicot root systems.", "botany"),
    
    # Toxicity & Chemical Defense
    ("Is this plant toxic to touch and does it cause acute contact dermatitis?", "toxicity"),
    ("What is the lethal dose and chemical formula of urushiol in poison ivy?", "toxicity"),
    ("What symptoms occur after ingestion of tropane alkaloids from deadly nightshade?", "toxicity"),
    ("Is this wild mushroom poisonous or fatal to humans upon ingestion?", "toxicity"),
    ("What is the emergency first aid protocol for chemical skin burn and resin exposure?", "toxicity"),

    # Genetics & Genomics
    ("How does RNA polymerase initiate transcription upstream of coding gene promoters?", "genetics"),
    ("Explain CRISPR-Cas9 targeted endonuclease cleavage and single guide RNA mechanics.", "genetics"),
    ("How do spliceosomes excise non-coding introns and ligate coding exons in pre-mRNA?", "genetics"),
    ("What are epigenetic histone acetylation and DNA cytosine methylation modifications?", "genetics"),
    ("Explain chromosomal crossing over during meiotic prophase I.", "genetics"),

    # Cell Biology & Bioenergetics
    ("How does the electron transport chain generate a proton motive force across cristae?", "cell_biology"),
    ("Explain ATP synthase rotary motor kinetics in synthesizing adenosine triphosphate.", "cell_biology"),
    ("What occurs during the light-dependent reactions of photosynthesis in thylakoids?", "cell_biology"),
    ("How do lysosomes and proteasomes degrade misfolded cellular proteins?", "cell_biology"),
    ("Explain mitochondrial chemiosmosis and oxidative phosphorylation Complexes I to IV.", "cell_biology"),

    # Marine Biology & Oceanography
    ("What causes thermal coral bleaching in scleractinian biogenic reefs?", "marine"),
    ("How do endosymbiotic zooxanthellae dinoflagellates transfer fixed carbon to coral polyps?", "marine"),
    ("What is the impact of ocean acidification on aragonite calcium carbonate saturation?", "marine"),
    ("How do deep-sea hydrothermal vent tube worms survive without sunlight using chemosynthesis?", "marine"),
    ("Explain the biological carbon pump driven by marine phytoplankton sedimentation.", "marine"),

    # Microbiology & Virology
    ("How does the bacterial nitrogenase metalloenzyme complex reduce atmospheric N2 to ammonia?", "microbiology"),
    ("Explain the lytic cycle versus lysogeny in double-stranded DNA bacteriophages.", "microbiology"),
    ("How do beta-lactamase enzymes confer bacterial antimicrobial resistance against penicillin?", "microbiology"),
    ("What is the role of leghemoglobin in protecting nitrogenase from irreversible O2 denaturation?", "microbiology"),
    ("Explain bacterial quorum sensing and biofilm formation across pathogenic colonies.", "microbiology"),

    # Entomology & Insects
    ("Explain holometabolous complete metamorphosis across egg, larva, pupa, and imago stages.", "entomology"),
    ("How does ecdysone and juvenile hormone regulate insect cuticle molting and apolysis?", "entomology"),
    ("What is the structural composition of the chitin-protein matrix in insect exoskeletons?", "entomology"),
    ("How do honeybees communicate foraging distance and azimuth using the waggle dance?", "entomology"),
    ("Explain eusocial colony organization and reproductive division of labor in Hymenoptera.", "entomology"),

    # Ornithology & Avian Science
    ("How do birds achieve continuous cross-current oxygenation using anterior and posterior air sacs?", "ornithology"),
    ("Explain avian flight biomechanics, asymmetric remiges wing airfoils, and the pectoral keel.", "ornithology"),
    ("How do trabecular pneumatic hollow bones reduce weight during high-altitude bird flight?", "ornithology"),
    ("What is the function of the supracoracoideus muscle pulley in raising avian wings?", "ornithology"),
    ("How do migratory songbirds navigate using geomagnetic inclination and retinal cryptochromes?", "ornithology"),

    # Mycology & Fungal Biology
    ("How do arbuscular mycorrhizal fungi establish symbiotic nutrient exchange in plant roots?", "mycology"),
    ("How do white-rot fungi secrete oxidative lignin peroxidases to decompose dead wood?", "mycology"),
    ("Explain fungal hyphae apical elongation, septal pores, and underground mycelial networks.", "mycology"),
    ("What is the ecological role of saprotrophic basidiomycete fungi in terrestrial humus formation?", "mycology"),
    ("How do lichens maintain mutualistic equilibria between mycobionts and photobionts?", "mycology"),

    # Pathology & Plant Diseases
    ("How do pattern recognition receptors detect pathogen-associated molecular patterns in plant immunity?", "pathology"),
    ("What triggers the localized hypersensitive response and programmed cell death against fungi?", "pathology"),
    ("Explain systemic acquired resistance (SAR) signaling mediated by salicylic and pipecolic acids.", "pathology"),
    ("How does Phytophthora infestans late blight penetrate potato and tomato leaf cuticles?", "pathology"),
    ("What are the diagnostic symptoms of powdery mildew and necrotic bacterial canker on foliage?", "pathology"),

    # Ecology & Biomes
    ("Explain top-down trophic cascades triggered by the removal of apex keystone predators.", "ecology"),
    ("How do nitrogen, carbon, and phosphorus biogeochemical cycles flow through biomes?", "ecology"),
    ("What is the relationship between functional ecological redundancy and ecosystem resilience?", "ecology"),
    ("Explain secondary ecological succession following wildfire disturbances in temperate forests.", "ecology"),
    ("How does carrying capacity K regulate logistic population growth across natural habitats?", "ecology"),

    # Evolutionary Biology & Paleontology
    ("Explain allopatric speciation initiated by geographic vicariance events and reproductive isolation.", "evolution"),
    ("How do cladistic phylogenetics reconstruct monophyletic clades based on derived synapomorphies?", "evolution"),
    ("What is adaptive radiation and how does divergent selection drive morphological specialization?", "evolution"),
    ("Explain homologous transitional fossil structures in the vertebrate transition from water to land.", "evolution"),
    ("How does natural selection alter allele frequencies in wild populations over evolutionary epochs?", "evolution"),

    # Wildlife Zoology & Ethology
    ("What are the nocturnal foraging adaptations and home ranges of wild red foxes?", "wildlife"),
    ("How do mammals regulate internal circadian rhythms using the suprachiasmatic nucleus?", "wildlife"),
    ("What are the dietary specializations and bamboo digestive anatomy of wild Red Pandas?", "wildlife"),
    ("Explain predator-prey spatial navigation and territory scent marking in carnivores.", "wildlife"),
    ("How do alpine mammals survive sub-zero winter temperatures through physiological torpor?", "wildlife"),

    # Math & Geometry
    ("Calculate total planting capacity for a garden plot of 200 square meters with spacing 0.5 meters.", "math"),
    ("How many plants fit in 50 square meters with hexagonal row spacing of 0.4 meters?", "math"),
    ("Calculate the total volume of topsoil needed for raised beds measuring 4 by 2 by 0.5 meters.", "math"),
    ("What is the optimal spacing density to plant 100 seedlings in a rectangular 15 meter row?", "math"),
    ("Convert 1500 square feet into square meters and calculate plant capacity at 1 foot spacing.", "math")
]

def legacy_records():
    return [{
        "id": f"router-legacy-query-{index:04d}",
        "case_id": f"router-legacy-query-{index:04d}",
        "source_id": "legacy_inline_router_demo", "text": text,
        "labels": {"expert": expert}, "reviewed": False,
        "provenance_note": "Unreviewed hand-authored routing fixture, not an independent benchmark.",
    } for index, (text, expert) in enumerate(TRAINING_SAMPLES, 1)]


def main(argv=None):
    from tiny_experts.neural.subject_training import subject_main
    return subject_main(
        "router", Path(__file__).resolve().parent / "training" / "configs" / "router.json",
        legacy_records, argv,
    )


def train_moe_router(epochs=40, lr=0.003, batch_size=16):
    """Compatibility entry; trains an experimental domain classifier only."""
    return main(["--demo", "--epochs", str(epochs), "--learning-rate", str(lr), "--batch-size", str(batch_size)])


if __name__ == "__main__":
    main()
