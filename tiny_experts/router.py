from typing import Any, Dict, List
import re
from .matching import contains_any

class CapabilityRouter:
    """
    Explicit capability routing, with an optional packaged neural classifier.
    An unmatched query returns no matching component instead of an unrelated fallback.
    """

    INTENT_KEYWORDS = {
        "botany": ["plant", "flower", "tree", "leaf", "leaves", "grow", "soil", "water", "sun", "bloom", "prune", "sunflower", "oak", "horticulture"],
        "wildlife": ["animal", "mammal", "wildlife", "diet", "fox", "bear", "wolf", "deer", "behavior", "ethology"],
        "ornithology": ["bird", "avian", "feather", "wing", "fly", "flight", "aerodynamics", "soar", "beak", "plumage", "song", "nest", "eagle", "sparrow", "hawk", "owl", "air sac", "bone", "bones"],
        "entomology": ["insect", "bug", "butterfly", "moth", "caterpillar", "larva", "pupa", "cocoon", "chrysalis", "bee", "ant", "wasp", "beetle", "chitin", "metamorphosis"],
        "mycology": ["fungus", "fungi", "mushroom", "mycelium", "hyphae", "mycorrhizae", "spore", "lichen", "mold", "decay", "rot"],
        "marine": ["marine", "ocean", "sea", "coral", "reef", "bleach", "bleaching", "zooxanthellae", "phytoplankton", "plankton", "diatom", "kelp", "vent", "deep sea", "fish", "shark", "whale", "aquatic"],
        "microbiology": ["bacteria", "bacterial", "virus", "viral", "microbe", "microbial", "microbiology", "phage", "bacteriophage", "antibiotic", "resistance", "amr", "rhizobium", "nitrogen fix", "nodule", "fermentation"],
        "evolution": ["evolution", "evolve", "speciation", "darwin", "fossil", "paleontology", "extinct", "ancestor", "lineage", "radiation", "cladistics", "homology", "deep time"],
        "genetics": ["dna", "rna", "gene", "genes", "genetic", "allele", "mutation", "mutate", "crispr", "transcription", "translation", "codon", "chromosome", "hereditary"],
        "cell_biology": ["cell", "cellular", "mitochondria", "atp", "chloroplast", "membrane", "organelle", "photosynthesis", "respiration", "enzyme", "turgor"],
        "pathology": [
            "disease", "blight", "mildew", "canker", "wilt", "sick", "dying", "lesion", "infection",
            "pathogen", "cure", "treatment", "spot", "scab", "rot", "decay", "diagnosis", "talcum",
            "powder", "resistance", "immune", "sar", "salicylic", "virus", "viral", "viroid", "tobrfv",
            "mosaic", "rugose", "nematode", "gall", "speck", "blossom end", "chlorosis", "drift",
            "sunscald", "catfacing", "shepherd", "ooze", "mycotoxin", "vomitoxin", "blast", "rust",
            "koh", "assay", "primer", "immuno", "streaming", "slimy", "mush", "stunted", "curled",
            "cupping", "twisting", "interveinal", "yellowing", "whitefly", "whiteflies", "thrips",
            "herbicide", "deficiency", "deficiencies", "kresek", "sheath", "clcuv", "enation",
            "black arm", "ascochyta", "sterility mosaic", "red rot", "falcatum", "huanglongbing",
            "greening", "malformation", "psyllid", "sugarcane", "pigeonpea", "arhar", "chickpea", "mango",
            "mottle", "blotchy", "mandarin", "lopsided", "concentric", "target", "bullseye", "rings", "halo"
        ],
        "ecology": ["ecology", "ecosystem", "trophic", "cascade", "predator", "prey", "food web", "food chain", "keystone", "succession", "cycle", "nitrogen", "carbon", "biome"],
        "biology": ["why", "how", "adaptation", "adapt", "mechanism", "coevolution", "pollination", "scientific", "hormone", "auxin", "phototropism"],
        "toxicity": ["poison", "toxic", "dangerous", "sting", "bite", "safe", "rash", "hurt", "eat", "edible", "allergy", "kill", "hazard", "pet", "dog", "cat", "horse"],
        "math": [
            "how many", "space", "spacing", "calculate", "feet", "meter", "meters", "inch",
            "density", "count", "convert", "area", "distance", "solve", "equation", "diff",
            "derivative", "differentiate", "integral", "integrate", "algebra", "matrix",
            "determinant", "eigenvalue", "polynomial", "calculus", "गणित", "समीकरण", "समाकलन", "अवकलन"
        ],
        "librarian": [
            "book", "books", "textbook", "treatise", "author", "authors", "written by",
            "published", "publisher", "isbn", "edition", "year", "library", "catalog",
            "literature", "bibliography", "source text", "reference text",
            "किताब", "किताबें", "पुस्तक", "ग्रंथ", "लेखक", "प्रकाशन", "बइ", "বই", "நூல்", "పుస్తకం"
        ],
        "thermodynamics": [
            "thermodynamics", "thermodynamic", "carnot", "heat", "heat transfer", "entropy",
            "fourier", "conduction", "convection", "radiation", "stefan-boltzmann", "thermal",
            "joule", "kelvin", "उष्मा", "ऊष्मा", "ऊष्मागतिकी", "तापमान", "एन्ट्रॉपी", "चालकता", "विकिरण"
        ],
        "electronics": [
            "electronics", "circuit", "ohm", "ohms", "resistor", "resistance", "capacitor",
            "capacitance", "voltage", "current", "ampere", "kirchhoff", "kcl", "kvl",
            "impedance", "diode", "transistor", "पावर", "प्रतिरोध", "वोल्टेज", "धारा", "परिपथ", "इलेक्ट्रॉनिक्स"
        ],
        "mechanics": [
            "mechanics", "kinematics", "velocity", "acceleration", "force", "newton",
            "momentum", "torque", "kinetic energy", "potential energy", "gravity",
            "gravitation", "centripetal", "motion", "बल", "त्वरण", "वेग", "गति", "द्रव्यमान", "यांत्रिकी", "संवेग"
        ],
        "review": [
            "review", "reviews", "critique", "critiques", "debate", "debates", "consensus",
            "controversy", "criticism", "errata", "erratum", "dispute", "limitation",
            "समीक्षा", "विवाद", "आलोचना", "सर्वसम्मति"
        ],
        "biographer": [
            "who is", "who was", "biography", "born", "died", "scientist", "inventor",
            "father of", "architect of", "einstein", "feynman", "ambedkar", "newton",
            "raman", "tagore", "ramanujan", "agrios", "aristotle", "nobel", "thinker",
            "विद्वान", "वैज्ञानिक", "जीवनी", "कौन थे", "किसने बनाया", "आंबेडकर", "रवींद्रनाथ", "रामानुजन"
        ]
    }

    def __init__(self, neural_router=None):
        self.name = "Capability Router"
        self.neural_router = neural_router
        self.intent_keywords = {key: list(value) for key, value in self.INTENT_KEYWORDS.items()}

    def route(self, query: str, has_image: bool = False, hint_species: str = None) -> List[str]:
        active_experts = []
        q_lower = query.lower()
        species_lower = (hint_species or "").lower()
        combined = f"{q_lower} {species_lower}"

        # 1. Vision Expert
        if has_image or hint_species or contains_any(q_lower, ["photo", "image", "picture", "look at this", "identify this", "what is this"]):
            active_experts.append("vision")

        # 2. Check all fine-grained scientific domains
        for domain, keywords in self.intent_keywords.items():
            keywords = [k for k in keywords if not (domain == "biology" and k in {"why", "how", "scientific"})]
            if domain in {"pathology", "microbiology"}:
                keywords = [k for k in keywords if k != "resistance"]
            if contains_any(combined, keywords):
                active_experts.append(domain)

        # Contextual linkers:
        if contains_any(combined, ["butterfly", "bee", "caterpillar", "ant", "moth"]):
            if "entomology" not in active_experts:
                active_experts.append("entomology")

        if contains_any(combined, ["eagle", "sparrow", "hawk", "owl", "bird"]):
            if "ornithology" not in active_experts:
                active_experts.append("ornithology")

        if contains_any(combined, ["sunflower", "oak", "ivy", "nightshade", "lavender", "rose", "plant", "tree", "flower"]):
            if "botany" not in active_experts:
                active_experts.append("botany")

        if re.search(r"\d\s*[+*/-]\s*\d", q_lower):
            active_experts.append("math")
        if re.search(r"\b(?:mass|acceleration|velocity|force)\s*=", q_lower):
            active_experts.append("mechanics")
        if re.search(r"\b(?:v|i|r|c)\s*=", q_lower):
            active_experts.append("electronics")
        if self.neural_router is not None and self.neural_router.is_trained:
            # Neural output can propose only registered capabilities. Its package
            # supplies rejection rules; never force a label for an unknown query.
            active_experts.extend(k for k in self.neural_router.predict_active_experts(query)
                                  if k in self.intent_keywords or k == "vision")

        return list(dict.fromkeys(active_experts))


RouterModel = CapabilityRouter  # Legacy public import.
