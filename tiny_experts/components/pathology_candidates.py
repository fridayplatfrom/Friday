from ..matching import contains_any, contains_term
from typing import Any, Dict, Optional
import os
import re

from .base_component import BaseComponent
from ..pipeline.book_engine import BookEngine
from ..neural.pathology_net import NeuralPathologyClassifier
from ..pipeline.visual_reference_atlas import VisualReferenceAtlas
from ..pipeline.chemical_regulatory_registry import ChemicalRegulatoryRegistry
from ..pipeline.disease_triangle_engine import DiseaseTriangleEngine

class PathologyCandidateAdapter(BaseComponent):
    """Combines an optional neural classifier, condition-reference rules and retrieval; candidates are not confirmed diagnoses."""
    name = 'Plant Pathology Candidate Adapter'
    description = 'Combines an optional neural classifier, condition-reference rules and retrieval; candidates are not confirmed diagnoses.'
    component_kind = 'hybrid_adapter'
    uses_neural_model = True
    updates_parameters_at_inference = False

    CLINICAL_PROFILES = {
        # ====================================================
        # DIVISION 1: FUNGI & OOMYCETES
        # ====================================================
        "Early Blight": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Early Blight",
            "pathogen": "Alternaria solani",
            "kingdom": "Fungus (Ascomycota)",
            "symptoms": "Dark brown circular necrotic lesions with diagnostic concentric rings ('bullseye' or 'target board' pattern) surrounded by chlorotic yellow halos on lower foliage; collar rot on stems.",
            "etiology": "Pathogen secretes necrotrophic host-selective alternariol and macrosporin toxins alongside pectinases, destroying epidermal and mesophyll cell membranes.",
            "treatment": "Remove infected lower foliage up to 30 cm; apply preventive copper octanoate (FRAC M01) or biofungicide containing Bacillus amyloliquefaciens strain D747; switch to low-pressure drip irrigation.",
            "ipm_action": "FRAC M01 Copper rotation; enforce 3-year crop rotation out of Solanaceae.",
            "lab_test": "Universal Fungal ITS PCR: Forward ITS1 (5'-TCCGTAGGTGAACCTGCGG-3') and Reverse ITS4 (5'-TCCTCCGCTTATTGATATGC-3')."
        },
        "Late Blight": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Late Blight",
            "pathogen": "Phytophthora infestans",
            "kingdom": "Oomycete (Stramenopila - water mold with cellulose/beta-glucan cell walls)",
            "symptoms": "Large water-soaked olive to dark brown lesions rapidly expanding across foliage; profuse white fuzzy cottony sporulation on leaf undersides in humid or rainy conditions; foul-smelling collapse.",
            "etiology": "Destructive hemibiotrophic oomycete discharging motile biflagellate zoospores that penetrate stomata and cuticles, causing catastrophic systemic tissue lysis within 5-7 days.",
            "treatment": "Emergency quarantine protocol: Immediately remove and safely destroy severely infected plants; apply translaminar oomycete-specific fungicides (mandipropamid FRAC 40 / fluopicolide FRAC 43) or preventive copper hydroxide (FRAC M01); keep foliage strictly dry.",
            "ipm_action": "Plant certified resistant cultivars carrying Ph-2 and Ph-3 resistance genes; rotate FRAC 40/43 with multi-site copper protectants.",
            "lab_test": "PARP / PARPH Selective Agar isolation; CoxI / CoxII mitochondrial DNA barcoding."
        },
        "Powdery Mildew": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Powdery Mildew",
            "pathogen": "Podosphaera xanthii (syn. Sphaerotheca fuliginea / Erysiphe)",
            "kingdom": "Fungus (Ascomycota, Erysiphales)",
            "symptoms": "Superficial white to light-grey talcum-powder-like patches across upper (adaxial) leaf surfaces, petioles, and young stems; leaf chlorosis, upward curling, and premature senescence.",
            "etiology": "Obligate biotrophic epiphyte that produces lobed haustoria penetrating epidermal cells to siphon hexoses and amino acids without killing host cells immediately.",
            "treatment": "Foliar spray of potassium bicarbonate (3-5 g/L) for rapid osmotic lysis; apply micronized wettable sulfur (FRAC M02) at temperatures below 30°C; increase plant spacing for airflow.",
            "ipm_action": "Rotate potassium bicarbonate osmotic disruptors with Bacillus subtilis biofungicides and FRAC M02 sulfur.",
            "lab_test": "Microscopic examination of superficial conidiophores and fibrosin bodies under 400x magnification."
        },
        "Downy Mildew": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Downy Mildew",
            "pathogen": "Pseudoperonospora cubensis",
            "kingdom": "Oomycete (Stramenopila, Peronosporales)",
            "symptoms": "Distinct bright angular yellow patches strictly delimited by leaf veins ('geometric mosaic' pattern) on upper leaf surface; purplish-grey to dark brown downy felt-like sporulation on corresponding leaf undersides.",
            "etiology": "Obligate biotrophic oomycete whose branched sporangiophores emerge through open stomata during damp, high-humidity mornings; motile zoospores require free water film to infect.",
            "treatment": "Strict drip irrigation at soil level (zero overhead watering); preventive copper octanoate (FRAC M01); apply targeted oomycete fungicides (mandipropamid FRAC 40).",
            "ipm_action": "Oomycete-specific FRAC 40/43 rotation; cultivate downy mildew resistant hybrids.",
            "lab_test": "Microscopic observation of branched, tree-like sporangiophores with lemon-shaped terminal sporangia."
        },
        "Fusarium Wilt": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Fusarium Wilt",
            "pathogen": "Fusarium oxysporum f. sp. lycopersici",
            "kingdom": "Fungus (Ascomycota, Sordariomycetes)",
            "symptoms": "Unilateral wilting and foliar yellowing ('yellow flag' symptom affecting one side of branch or leaf); dark chocolate-brown discoloration of xylem vascular ring inside sliced lower stem.",
            "etiology": "Soil-borne pathogen penetrating root tips; produces microconidia, macroconidia, and resting chlamydospores that plug water-conducting xylem vessels, compounded by fusaric acid toxin and host tyloses.",
            "treatment": "Foliar chemical sprays are ineffective; solarize infected soil beds; inoculate root rhizosphere with antagonistic Trichoderma harzianum (strain T-22) or Streptomyces lydicus; plant certified resistant cultivars.",
            "ipm_action": "Plant cultivars with I, I-2, I-3 resistance genes; rotate out of host crops for 5+ years.",
            "lab_test": "Plating stem vascular shavings onto Komada's selective medium; ITS1/ITS4 fungal PCR."
        },
        "Grey Mold": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Grey Mold",
            "pathogen": "Botrytis cinerea",
            "kingdom": "Fungus (Ascomycota, Leotiomycetes)",
            "symptoms": "Watery softening and rot of ripening fruit (strawberries, grapes) and senescent petals, quickly engulfed by a dense, velvety, mouse-grey blanket of branched conidiophores and conidia.",
            "etiology": "Aggressive necrotrophic generalist secreting pectinases, cellulases, and botrydial phytotoxin, triggering host cell death and saprophytic consumption under cool damp conditions (>90% RH).",
            "treatment": "Aggressively prune and dispose of infected fruits and senescent petals; enhance canopy ventilation; apply bio-antagonist Bacillus amyloliquefaciens (strain D747) or rotate fenhexamid (FRAC 17).",
            "ipm_action": "Rotate biofungicide lipopeptides with FRAC 12/17; lower greenhouse relative humidity below 80%.",
            "lab_test": "Microscopic confirmation of grape-like clusters of conidia on tall branched brown conidiophores."
        },
        "Black Spot": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Black Spot",
            "pathogen": "Diplocarpon rosae",
            "kingdom": "Fungus (Ascomycota, Leotiomycetes)",
            "symptoms": "Circular to subcircular jet-black spots (2-12 mm) with distinctive fringed, feathery, fibrillose margins on upper rose leaf surfaces; surrounded by chlorotic yellow halos followed by rapid defoliation.",
            "etiology": "Subcuticular acervuli produce bicellular conidia dispersed by splashing rain; conidia require 7+ hours of continuous leaf wetness to germinate and penetrate rose cuticles.",
            "treatment": "Prune infected canes; collect and destroy fallen leaves; water strictly at root base; apply preventive potassium bicarbonate, cold-pressed neem oil, or triazole fungicide (myclobutanil FRAC 3).",
            "ipm_action": "Sanitation and debris removal; rotate multi-site copper/sulfur protectants with FRAC 3 DMIs.",
            "lab_test": "Microscopic examination of 2-celled hyaline Marssonina conidia with diagnostic median constriction."
        },
        "Apple Scab": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Apple Scab",
            "pathogen": "Venturia inaequalis",
            "kingdom": "Fungus (Ascomycota, Dothideomycetes)",
            "symptoms": "Olive-green velvety circular spots with feathery borders on young leaves; on fruit, lesions expand into dark brown, corky, rough scabs that cause deep star-shaped cracking and fruit deformation.",
            "etiology": "Hemibiotroph overwintering as pseudothecia in fallen leaf litter; discharges sexual ascospores during spring rains (Mill's infection criteria dictates required leaf wetness hours).",
            "treatment": "Apply 5% urea spray to fallen autumn leaf litter to accelerate pseudothecia decomposition; apply preventive micronized wettable sulfur (FRAC M02) or captan from green tip through petal fall.",
            "ipm_action": "Cultivate resistant apple varieties carrying Vf/Rvi6 genes (Liberty, Enterprise); rotate protectant FRAC M02/M04.",
            "lab_test": "Spore trapping of 2-celled asymmetric ascospores; ITS1/ITS4 ribosomal sequence analysis."
        },
        "Wheat Stem Rust": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Wheat Stem Rust",
            "pathogen": "Puccinia graminis f. sp. tritici",
            "kingdom": "Fungus (Basidiomycota, Pucciniales)",
            "symptoms": "Elongated, reddish-brown powdery pustules (uredinia) rupturing through leaf sheaths and stems; severe lodging and total grain shriveling.",
            "etiology": "Macrocyclic, heteroecious rust with 5 spore stages requiring Common Barberry (Berberis vulgaris) for sexual pycnia/aecia; wind-blown asexual urediniospores spread over continental distances.",
            "treatment": "Eradicate alternate barberry hosts; apply preventative DMI triazoles (tebuconazole FRAC 3) or SDHIs (FRAC 7) at flag leaf emergence; plant resistant cultivars with multi-gene APR (Sr2, Sr25).",
            "ipm_action": "Monitor global Ug99 rust spread; deploy adult plant resistance (APR) gene complexes.",
            "lab_test": "Microscopic identification of oval, echinulate dikaryotic urediniospores; race-typing bioassays."
        },
        "Rice Blast": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Rice Blast",
            "pathogen": "Magnaporthe oryzae (Pyricularia oryzae)",
            "kingdom": "Fungus (Ascomycota, Magnaporthales)",
            "symptoms": "Spindle-shaped or diamond-shaped lesions with gray centers and dark brown margins on leaves; neck/collar blast choking panicle stems, causing bleached white sterile panicles ('white heads').",
            "etiology": "Melanized appressoria generate 5 to 8 MPa hydrostatic turgor pressure, mechanically punching rigid penetration pegs through silica-rich cuticles.",
            "treatment": "Treat seed with tricyclazole (melanin biosynthesis inhibitor FRAC 16.1); avoid excessive nitrogen fertilizer; apply preventive strobilurins (FRAC 11) or isoprothiolane (FRAC 6).",
            "ipm_action": "Balance silicon and nitrogen nutrition; rotate FRAC 16.1 with FRAC 11 and FRAC 07.",
            "lab_test": "PCR detection using Pot2 transposon-specific primers; microscopic inspection of 3-celled pyriform conidia."
        },
        "Fusarium Head Blight": {
            "division": "Division 1: Fungi & Oomycetes",
            "disease": "Fusarium Head Blight",
            "pathogen": "Fusarium graminearum (Gibberella zeae)",
            "kingdom": "Fungus (Ascomycota, Hypocreales)",
            "symptoms": "Premature bleaching of individual spikelets or whole wheat heads at flowering; diagnostic salmon-pink to orange sporulation on glumes; grains are shriveled, lightweight, and chalky pink ('tombstones').",
            "etiology": "Produces hazardous trichothecene mycotoxins: Deoxynivalenol (DON / Vomitoxin - 60S ribosome inhibitor) and Zearalenone (estrogenic mycotoxin). Strictly limited to <1.0 ppm for food safety.",
            "treatment": "Apply targeted triazoles (prothioconazole / metconazole FRAC 3) precisely at anthesis (flowering Feekes 10.5.1). CRITICAL WARNING: NEVER apply strobilurins (FRAC 11) as they induce a spike in DON mycotoxin synthesis!",
            "ipm_action": "Rotate out of maize; harvest and clean lightweight chalky tombstone grains to lower mycotoxin loads.",
            "lab_test": "ELISA or HPLC-MS quantitation for Deoxynivalenol (DON) vomitoxin; Tri5 gene PCR assay."
        },

        # ====================================================
        # DIVISION 2: ADVANCED AGRICULTURAL BACTERIOLOGY
        # ====================================================
        "Bacterial Spot": {
            "division": "Division 2: Agricultural Bacteriology",
            "disease": "Bacterial Spot",
            "pathogen": "Xanthomonas campestris pv. vesicatoria",
            "kingdom": "Bacterium (Pseudomonadota, Gammaproteobacteria)",
            "symptoms": "Small (1-3 mm) water-soaked greasy dark spots turning black with prominent bright yellow chlorotic halos; spots coalesce causing foliar scorch and leaf drop; raised brown scabs on fruit.",
            "etiology": "Bacterial pathogen entering through stomata and micro-wounds during thunderstorm rain-splash; deploys Type III secretion system effectors (TALEs) to suppress host defense.",
            "treatment": "True antifungal agents are ineffective; apply fixed copper bactericides (copper octanoate FRAC M01) tank-mixed with mancozeb; use hot-water-treated certified disease-free seeds (50°C for 25 min).",
            "ipm_action": "FRAC M01 copper bactericide; eliminate solanaceous weed hosts and avoid field work when foliage is wet.",
            "lab_test": "The 10-Second 3% KOH String Test (Gram-negative slime thread); 16S rDNA universal PCR (27F/1492R)."
        },
        "Bacterial Wilt": {
            "division": "Division 2: Agricultural Bacteriology",
            "disease": "Bacterial Wilt",
            "pathogen": "Ralstonia solanacearum",
            "kingdom": "Bacterium (Pseudomonadota, Betaproteobacteria)",
            "symptoms": "Rapid daytime wilting and collapse of green foliage without initial yellowing or leaf spotting; stems remain green while foliage wilts; positive milky streaming threads from cut stem in water.",
            "etiology": "Systemic vascular bacterium colonizing and clogging xylem vessels with extracellular polysaccharides (EPS), causing sudden irreversible water transport failure in hot soils (30-35°C).",
            "treatment": "Graft susceptible scions onto resistant wild rootstocks (e.g. Maxifort); rotate fields with non-solanaceous Poaceae/Fabaceae for 4 years; strictly sterilize cutting blades in 70% alcohol.",
            "ipm_action": "Cultural drip irrigation, strict tool sanitation, and grafting on certified resistant rootstocks.",
            "lab_test": "The Vascular Stem Streaming Assay in water beaker; Agdia ImmunoStrip for Ralstonia."
        },
        "Fire Blight": {
            "division": "Division 2: Agricultural Bacteriology",
            "disease": "Fire Blight",
            "pathogen": "Erwinia amylovora",
            "kingdom": "Bacterium (Pseudomonadota, Enterobacterales)",
            "symptoms": "Blossom blight followed by sudden 180-degree bending of succulent shoot tips forming the diagnostic 'shepherd's crook'; leaves turn scorched black and stay attached; milky white to amber droplets of bacterial ooze.",
            "etiology": "Enters via floral nectaries and lenticels; deploys Type III secretion system harpin (HrpN) triggering membrane depolarization and vascular xylem blockage with amylovoran exopolysaccharide.",
            "treatment": "Prune cankered branches 30 cm below visible lesion margin during dry weather, sterilizing shears with 70% alcohol between cuts; spray bloom antibiotics (streptomycin 100 ppm / oxytetracycline 200 ppm) timed by Maryblyt.",
            "ipm_action": "Rotate biological antagonists (Bacillus amyloliquefaciens D747) during bloom; eradicate wild hawthorn/crabapple reservoirs.",
            "lab_test": "Erwinia amylovora specific ams-gene PCR; 3% KOH String Test (Gram-negative mucoid string)."
        },
        "Bacterial Speck": {
            "division": "Division 2: Agricultural Bacteriology",
            "disease": "Bacterial Speck",
            "pathogen": "Pseudomonas syringae pv. tomato",
            "kingdom": "Bacterium (Pseudomonadota, Gammaproteobacteria)",
            "symptoms": "Tiny (1-2 mm) superficial jet-black pinpoint spots with bright yellow halos on leaves; raised, superficial tiny black specks resembling ground black pepper on green fruit surfaces.",
            "etiology": "Secretes coronatine (COR) phytotoxin, mimicking jasmonic acid to suppress salicylic acid defense and force stomata open; expresses Ice Nucleation Active (INA) proteins inducing frost injury at -2°C.",
            "treatment": "Fixed copper bactericides (FRAC M01) tank-mixed with mancozeb; spray acibenzolar-S-methyl (ASM) to elicit plant SAR immunity; avoid overhead irrigation.",
            "ipm_action": "Rotate copper protectants with SAR inducers; plant resistant cultivars carrying Pto gene.",
            "lab_test": "King's B medium culture showing brilliant blue-green pyoverdine fluorescence under 365 nm UV light."
        },
        "Bacterial Soft Rot": {
            "division": "Division 2: Agricultural Bacteriology",
            "disease": "Bacterial Soft Rot",
            "pathogen": "Pectobacterium carotovorum (Dickeya dadantii)",
            "kingdom": "Bacterium (Pseudomonadota, Enterobacterales)",
            "symptoms": "Foul-smelling, water-soaked, slimy liquefaction of potato tubers, carrots, onions, and cabbage heads; internal storage tissues turn into a creamy, decomposed liquid mush.",
            "etiology": "Secretes massive amounts of pectate lyases (Pel) and polygalacturonases via Type II secretion system, dissolving the middle lamella cementing plant cell walls.",
            "treatment": "Avoid harvesting during wet weather or when tuber pulp temperature >20°C; cure harvested tubers at 10-15°C with forced air to build suberin wound barriers; chlorinate flume wash water at 100-150 ppm free Cl.",
            "ipm_action": "Strict sanitation of potato storage bins, postharvest drying, and avoiding mechanical bruising.",
            "lab_test": "Pectate degradation pit assay on crystal violet pectate (CVP) medium; 3% KOH test (Gram-negative)."
        },
        "Crown Gall": {
            "division": "Division 2: Agricultural Bacteriology",
            "disease": "Crown Gall",
            "pathogen": "Agrobacterium tumefaciens (Rhizobium radiobacter)",
            "kingdom": "Bacterium (Pseudomonadota, Alphaproteobacteria)",
            "symptoms": "Rough, spongy-to-hard woody neoplastic galls and tumors on root crowns, grafting junctions, and stems of fruit trees, roses, and grapevines.",
            "etiology": "Transfers T-DNA from its Tumor-Inducing (Ti) plasmid into the plant genome, forcing plant cells to overproduce auxins and cytokinins (causing gall tumors) and opines (bacterial food).",
            "treatment": "Dip bare-root nursery stock in biocontrol suspension of antagonistic Agrobacterium radiobacter strain K84 (or K1026); sterilize grafting knives; inspect nursery plants before planting.",
            "ipm_action": "Biological protection using strain K84 producing agrocin 84; solarize contaminated planting holes.",
            "lab_test": "Ti-plasmid virD2 / ipt gene specific PCR assay; selective 1A medium isolation."
        },

        # ====================================================
        # DIVISION 3: PLANT VIROLOGY & INSECT VECTORS
        # ====================================================
        "Tomato Brown Rugose Fruit Virus": {
            "division": "Division 3: Plant Virology & Vectors",
            "disease": "Tomato Brown Rugose Fruit Virus (ToBRFV)",
            "pathogen": "Tomato Brown Rugose Fruit Virus (ToBRFV)",
            "kingdom": "Virus (+ssRNA Tobamovirus)",
            "symptoms": "Foliar mosaic bubbling and fern-leaf narrowing; fruit displays yellow blotches, brown necrotic rugose wrinkling, marbling, and unmarketable deformation. Breaks Tm-2 and Tm-2^2 resistance.",
            "etiology": "Highly infectious, seed-borne, mechanically transmitted Tobamovirus surviving on tools, trellising twine, and greenhouse glass for months without vector.",
            "treatment": "Strict quarantine pathogen: Safely bag and destroy infected plants; disinfect shears and hands with 20% non-fat dry skim milk or 10% trisodium phosphate (TSP); use certified ToBRFV-free seeds.",
            "ipm_action": "Complete greenhouse hygiene, disposable overalls, hot-water seed sanitation.",
            "lab_test": "Agdia ImmunoStrip for ToBRFV (5-minute field lateral flow); ToBRFV-specific RT-qPCR coat protein primers."
        },
        "Tobacco Mosaic Virus": {
            "division": "Division 3: Plant Virology & Vectors",
            "disease": "Tobacco Mosaic Virus (TMV)",
            "pathogen": "Tobacco Mosaic Virus (TMV)",
            "kingdom": "Virus (+ssRNA Tobamovirus)",
            "symptoms": "Alternating dark and light green mosaic mottling on leaves, foliar distortion, blistering, and stunted shoe-string foliage; fruit shows internal brown rings.",
            "etiology": "Extremely stable rod-shaped helical virions transmitted mechanically via workers' hands, tools, and tobacco smoker residue; survives for years in dried leaf debris.",
            "treatment": "Prohibit smoking or tobacco handling near crops; wash hands and dip tools in 20% reconstituted non-fat dry skim milk; rogue infected plants immediately.",
            "ipm_action": "Plant mosaic-resistant tomato cultivars (carrying Tm-2 or Tm-2^2 genes); steam-sterilize soil.",
            "lab_test": "ImmunoStrip lateral flow assay; electron microscopy of rigid 300x18 nm rod-shaped virions."
        },
        "Tomato Yellow Leaf Curl Virus": {
            "division": "Division 3: Plant Virology & Vectors",
            "disease": "Tomato Yellow Leaf Curl Virus (TYLCV)",
            "pathogen": "Tomato Yellow Leaf Curl Virus (TYLCV)",
            "kingdom": "Virus (ssDNA Begomovirus, Geminiviridae)",
            "symptoms": "Severe plant stunting, bushy erect growth, interveinal leaf chlorosis, and diagnostic upward cupping and curling of leaf margins; complete flower drop and zero fruit yield.",
            "etiology": "Transmitted in a persistent-circulative non-propagative manner exclusively by the silverleaf whitefly (Bemisia tabaci, biotypes B and Q).",
            "treatment": "Install 50-mesh insect exclusion netting on greenhouses; apply systemic diamides or neonicotinoids to suppress whitefly vectors; release parasitic Encarsia formosa wasps.",
            "ipm_action": "Plant TYLCV-resistant hybrid cultivars carrying Ty-1, Ty-2, or Ty-3 resistance genes.",
            "lab_test": "PCR using Begomovirus degenerate primers (SPGD1/SPGD2); TYLCV-specific CP gene PCR."
        },
        "Tomato Spotted Wilt Virus": {
            "division": "Division 3: Plant Virology & Vectors",
            "disease": "Tomato Spotted Wilt Virus (TSWV)",
            "pathogen": "Tomato Spotted Wilt Virus (TSWV)",
            "kingdom": "Virus (Ambisense ssRNA Tospovirus, Peribunyaviridae)",
            "symptoms": "Bronze spotting and purpling of foliage, terminal shoot dieback; developing fruit shows striking concentric yellow and dark brown necrotic ring spots and bumpy deformation.",
            "etiology": "Transmitted exclusively by thrips, primarily Western flower thrips (Frankliniella occidentalis); acquired only by thrips larvae and transmitted persistently by adults for life.",
            "treatment": "Monitor thrips with blue/yellow sticky traps; apply spinosad or insecticidal soaps; eliminate broadleaf weed reservoir hosts (dandelions, chickweed); plant Sw-5 resistant cultivars.",
            "ipm_action": "Thrips vector exclusion, predatory mites (Amblyseius swirskii), and planting Sw-5 tomato varieties.",
            "lab_test": "Agdia ImmunoStrip for TSWV; RT-PCR targeting the nucleocapsid (N) gene."
        },
        "Potato Spindle Tuber Viroid": {
            "division": "Division 3: Plant Virology & Vectors",
            "disease": "Potato Spindle Tuber Viroid (PSTVd)",
            "pathogen": "Potato Spindle Tuber Viroid (PSTVd)",
            "kingdom": "Viroid (Circular single-stranded non-coding RNA, Pospiviroidae)",
            "symptoms": "Potato tubers are abnormally elongated, cylindrical, and spindle-shaped with deep eyes and skin cracking; foliage exhibits stunted, upright, bunched epinasty.",
            "etiology": "Naked circular non-coding RNA (359 nucleotides) lacking a protein capsid; hijacks host RNA polymerase II in the plant nucleolus via rolling-circle replication.",
            "treatment": "Strict international quarantine: Destroy infected seed lots; sanitize cutting knives with 10% bleach; plant only certified viroid-free seed tubers.",
            "ipm_action": "Quarantine seed indexing; complete tool decontamination with quaternary ammonium compounds.",
            "lab_test": "Return Polyacrylamide Gel Electrophoresis (R-PAGE); PSTVd-specific RT-qPCR assay."
        },

        # ====================================================
        # DIVISION 4: NEMATOLOGY & SOIL DISEASE COMPLEXES
        # ====================================================
        "Root Knot Nematode": {
            "division": "Division 4: Nematology & Soil Complexes",
            "disease": "Root Knot Nematode",
            "pathogen": "Meloidogyne incognita (M. hapla / M. javanica)",
            "kingdom": "Nematode (Tylenchida, Meloidogynidae)",
            "symptoms": "Severe plant stunting, foliar chlorosis, and pronounced midday wilting despite moist soil; digging up root system reveals conspicuous swollen galls, knots, and distorted root clusters.",
            "etiology": "Microscopic J2 juveniles penetrate root tips with stylets, establishing feeding sites and inducing vascular cells into multinucleated 'giant cells', disrupting water/nutrient xylem conduction.",
            "treatment": "Soil solarization for 6-8 weeks under clear polyethylene film; incorporate high-glucosinolate mustard bio-fumigant cover crops; apply bionematicides (Purpureocillium lilacinum strain 251).",
            "ipm_action": "Plant nematode-resistant cultivars carrying the Mi-gene (Mi-1.2); rotate with non-host marigolds (Tagetes patula).",
            "lab_test": "Microscopic evaluation of root galling on 0-5 Zeck scale; nematode extraction via Baermann funnel."
        },
        "Nematode Fusarium Wilt Complex": {
            "division": "Division 4: Nematology & Soil Complexes",
            "disease": "Nematode-Fusarium Synergistic Wilt Complex",
            "pathogen": "Meloidogyne incognita + Fusarium oxysporum",
            "kingdom": "Nematode & Fungal Disease Complex",
            "symptoms": "Rapid catastrophic wilting and complete death of tomato plants, exhibiting both swollen root knots and dark brown vascular xylem ring staining; breaks single-gene I-gene resistance.",
            "etiology": "Nematode stylet wounding provides entry for Fusarium chlamydospores, while giant cell physiology suppresses host phytoalexins, accelerating fungal invasion by 10x.",
            "treatment": "Integrated management targeting both organisms: Pre-plant soil bio-fumigation + root rhizosphere inoculation with Trichoderma harzianum T-22 + grafting on double-resistant rootstocks (Maxifort).",
            "ipm_action": "Dual-target nematode-fungal management; 4-year rotation out of host crops.",
            "lab_test": "Simultaneous root gall counting + vascular xylem isolation on Komada's medium."
        },

        # ====================================================
        # DIVISION 5: ABIOTIC LOOKALIKES (DIFFERENTIAL DIAGNOSIS)
        # ====================================================
        "Blossom End Rot": {
            "division": "Division 5: Abiotic & Differential Diagnosis",
            "disease": "Blossom End Rot (BER)",
            "pathogen": "Abiotic Calcium Transport Deficiency",
            "kingdom": "Abiotic / Physiological Stress (Non-Infectious)",
            "differential_alert": "[CRITICAL DIFFERENTIAL ALERT: DO NOT APPLY FUNGICIDES! This is an abiotic physiological condition, NOT a fungal blight.]",
            "symptoms": "Starts as a water-soaked spot at the blossom end (distal bottom tip opposite the stem) of green fruit; expands into a large, circular, sunken, dry, leathery black or dark brown plate.",
            "etiology": "Localized Calcium (Ca2+) deficiency in distal expanding fruit cells caused by fluctuating soil moisture or drought stress. Transpiration drives calcium into leaves rather than fruit, collapsing fruit cell walls.",
            "treatment": "DO NOT APPLY CHEMICAL FUNGICIDES. Stabilize soil moisture with automated drip irrigation; apply 5-10 cm organic straw mulch; avoid excess ammonium (NH4+) fertilizer; maintain soil pH at 6.2 - 6.8.",
            "ipm_action": "Consistent irrigation scheduling; foliar calcium chloride (CaCl2 0.5%) emergency sprays; soil calcium test.",
            "lab_test": "Soil and tissue calcium test; confirmation of sterile necrotic pericarp tissue without fungal hyphae."
        },
        "Herbicide Drift Injury": {
            "division": "Division 5: Abiotic & Differential Diagnosis",
            "disease": "Herbicide Drift Injury (2,4-D / Dicamba)",
            "pathogen": "Synthetic Auxin Herbicide 2,4-D Drift",
            "kingdom": "Abiotic / Chemical Toxin Stress (Non-Infectious)",
            "differential_alert": "[DIFFERENTIAL ALERT: Often misdiagnosed as Mosaic Virus! Appears suddenly across whole fields within 24-48 hours.]",
            "symptoms": "Dramatic twisting and downward curling (epinasty) of leaf stems; leaf blades become strap-like, narrow, and puckered with fan-shaped parallel veins resembling a duck foot.",
            "etiology": "Volatilization and wind drift of synthetic auxin growth-regulator herbicides (2,4-D or dicamba) applied to neighboring lawns or fields, disrupting cellular auxin receptor signaling.",
            "treatment": "DO NOT SPRAY PESTICIDES. Flush plants with water; apply activated charcoal drench if in soil; prune severely distorted growth; maintain plant vigor; wait for new unaffected flush of growth.",
            "ipm_action": "Establish windbreak vegetation buffers; coordinate with neighbors to avoid spraying during thermal inversions.",
            "lab_test": "GC-MS analytical chemistry residue assay for phenoxyalkanoic acid herbicides."
        },
        "Iron Deficiency Chlorosis": {
            "division": "Division 5: Abiotic & Differential Diagnosis",
            "disease": "Iron Deficiency Chlorosis",
            "pathogen": "Alkaline Soil Insoluble Iron Deficiency",
            "kingdom": "Abiotic / Nutritional Stress (Non-Infectious)",
            "differential_alert": "[DIFFERENTIAL RULE: Sharp interveinal yellowing on YOUNGEST terminal leaves with green veins; soil pH > 7.5.]",
            "symptoms": "Sharp, brilliant interveinal chlorosis (leaf blades turn pale yellow to bleached ivory while leaf veins remain distinctly dark green) strictly on the YOUNGEST uppermost terminal foliage.",
            "etiology": "High soil pH (>7.5) or over-liming precipitates ferric iron into insoluble iron hydroxides, preventing root uptake for chloroplast chlorophyll synthesis.",
            "treatment": "DO NOT APPLY FUNGICIDES. Apply chelated iron (Fe-EDDHA, which remains stable up to pH 9.0) as soil drench; apply elemental sulfur to gradually lower soil pH to 6.2 - 6.8.",
            "ipm_action": "Soil pH remediation with elemental sulfur; switch to chelated micro-nutrient fertilizers.",
            "lab_test": "Standard soil pH and electrical conductivity (EC) slurry test; foliar micro-nutrient tissue analysis."
        },
        "Nitrogen Deficiency": {
            "division": "Division 5: Abiotic & Differential Diagnosis",
            "disease": "Nitrogen Deficiency",
            "pathogen": "Soil Available Nitrogen Depletion",
            "kingdom": "Abiotic / Nutritional Stress (Non-Infectious)",
            "differential_alert": "[DIFFERENTIAL RULE: Uniform pale yellowing on OLDEST lower leaves first, unlike fungal spots with necrotic rings.]",
            "symptoms": "General, uniform pale yellow-green chlorosis initiating on the OLDEST lowermost leaves; lower leaves turn yellow and drop while upper growth remains light green.",
            "etiology": "Nitrogen is highly mobile in plant phloem; under deficiency, the plant scavenges and translocates nitrogen from mature lower leaves to support new terminal growth.",
            "treatment": "Apply balanced organic fertilizer (fish hydrolysate, blood meal, or calcium nitrate); side-dress compost.",
            "ipm_action": "Perform pre-sidedress nitrate test (PSNT); incorporate nitrogen-fixing leguminous cover crops.",
            "lab_test": "Soil nitrate (NO3-N) analysis; tissue nitrogen combustion testing."
        },
        "Sunscald Injury": {
            "division": "Division 5: Abiotic & Differential Diagnosis",
            "disease": "Sunscald Injury",
            "pathogen": "Solar Radiation Thermal Shock",
            "kingdom": "Abiotic / Environmental Stress (Non-Infectious)",
            "differential_alert": "[DIFFERENTIAL ALERT: Bleached papery fruit shoulders directly exposed to sun; zero fungal conidia present.]",
            "symptoms": "Large bleached, white, papery, sunken patches on green fruit shoulders directly facing intense afternoon sunlight; lesion is dry and parchment-like.",
            "etiology": "Sudden exposure of shade-adapted fruit to intense solar thermal radiation (fruit skin temperatures exceeding 45°C), destroying chlorophyll and collapsing epidermal cells.",
            "treatment": "Maintain dense foliage canopy to shade fruit; avoid excessive defoliation during pruning; erect 30% shade cloth over sensitive summer crops.",
            "ipm_action": "Control foliar defoliating diseases (black spot, early blight) to preserve protective leaf canopies.",
            "lab_test": "Visual verification of sun-angle orientation and absence of sporulating pathogen structures."
        },
        "Catfacing Malformation": {
            "division": "Division 5: Abiotic & Differential Diagnosis",
            "disease": "Catfacing Fruit Malformation",
            "pathogen": "Cold Temperature Flower Bud Shock",
            "kingdom": "Abiotic / Environmental Stress (Non-Infectious)",
            "differential_alert": "[DIFFERENTIAL ALERT: Severe scarring and puckering on blossom end caused by cold weather during bloom.]",
            "symptoms": "Extreme malformation, puckering, scarring, and deep corky cavities at the blossom end of heirloom tomato fruit; fruit remains edible despite bizarre shape.",
            "etiology": "Prolonged cold night temperatures (<12°C / 54°F) during floral bud differentiation, disrupting normal carpel cell division and pistil fusion.",
            "treatment": "Delay transplanting until nighttime temperatures consistently exceed 13°C; use row covers during spring cold snaps; choose catfacing-tolerant varieties.",
            "ipm_action": "Use floating row covers in early spring; cultivate resistant hybrids with small blossom scars.",
            "lab_test": "Inspection of floral stage temperature records; morphological confirmation of corky fused cavities."
        },

        # ====================================================
        # DIVISION 6: CLINICAL LAB ASSAYS & SAR
        # ====================================================
        "Clinical Laboratory Diagnostic Protocol": {
            "division": "Division 6: Clinical Laboratory Assays",
            "disease": "Clinical Laboratory Diagnostic Protocol",
            "pathogen": "Diagnostic Assay Protocol",
            "kingdom": "Diagnostic Testing & Microbiology",
            "symptoms": "Scientific validation protocols for differentiating plant pathogens in agricultural testing laboratories.",
            "etiology": "Standardized molecular barcoding, selective culture media, serological lateral flow, and rapid chemical assays.",
            "treatment": "Execute the indicated clinical laboratory assay according to the standardized protocol below.",
            "ipm_action": "Confirm pathogen identity before deploying expensive or restricted chemical crop protection.",
            "lab_test": "10-Second 3% KOH String Test: Mix colony in 1 drop 3% KOH; viscous stringing confirms Gram-Negative bacteria. PCR: Fungal ITS1/ITS4, Bacterial 16S 27F/1492R. Media: King's B, PARP, Komada's."
        },
        "Systemic Acquired Resistance": {
            "division": "Division 6: Clinical Laboratory Assays",
            "disease": "Systemic Acquired Resistance (SAR)",
            "pathogen": "Host Plant Innate Immune System",
            "kingdom": "Host Immune Response (Salicylic Acid / NPR1 Signaling Pathway)",
            "symptoms": "Hypersensitive response (HR) localized micro-burst of programmed cell death at infection site, accompanied by broad-spectrum systemic immunity in distal foliage.",
            "etiology": "PAMP recognition triggers an oxidative burst (RBOHD H2O2 / superoxide). Mobile vascular signals (pipecolic acid / NHP / MeSA) activate salicylic acid accumulation in distal leaves. Salicylic acid binds NPR1, which monomerizes, translocates to nucleus, and recruits TGA transcription factors to transcribe Pathogenesis-Related (PR-1, PR-2 beta-glucanase, PR-3 chitinase, PR-5) defense proteins.",
            "treatment": "Elicit SAR proactively using foliar salicylic acid, biological elicitors (chitosan, soluble silicon), or beneficial PGPR rhizobacteria (Bacillus amyloliquefaciens); maintain balanced nutrition.",
            "ipm_action": "Preventive SAR elicitation combined with root rhizosphere colonization by beneficial microbes.",
            "lab_test": "RT-qPCR gene expression assay for PR-1 molecular biomarker; nitroblue tetrazolium (NBT) superoxide assay."
        },

        # ====================================================
        # DIVISION 7: INDIAN AGRICULTURAL & TROPICAL STAPLE CROPS (ICAR / TNAU)
        # ====================================================
        "Rice Bacterial Leaf Blight": {
            "division": "Division 2: Agricultural Bacteriology (ICAR / TNAU)",
            "disease": "Rice Bacterial Leaf Blight (BLB)",
            "pathogen": "Xanthomonas oryzae pv. oryzae",
            "kingdom": "Bacterium (Pseudomonadota, Gammaproteobacteria)",
            "symptoms": "Biphasic: Early 'kresek' seedling wilt phase with inward leaf rolling and complete wilting; later marginal wavy translucent yellow stripes turning straw-yellow and bleached white with amber bacterial beads.",
            "etiology": "Enters through hydathodes and root wounds during transplanting; colonizes xylem vessels, producing massive extracellular polysaccharide slime (xanthan) and deploying TAL effectors.",
            "treatment": "Seed treatment with streptocycline (100 ppm) + copper oxychloride (0.2%); spray copper hydroxide (FRAC M01) or fresh cow-dung filtrate (20%); drain field standing water.",
            "ipm_action": "Cultivate resistant varieties carrying Xa21, xa13, and xa5 genes (Improved Samba Mahsuri); avoid excess nitrogen; apply balanced potash.",
            "lab_test": "Cut seedling vascular streaming assay in water; Xanthomonas 16S-23S ribosomal PCR."
        },
        "Rice Sheath Blight": {
            "division": "Division 1: Fungi & Oomycetes (ICAR / TNAU)",
            "disease": "Rice Sheath Blight",
            "pathogen": "Rhizoctonia solani (Thanatephorus cucumeris)",
            "kingdom": "Fungus (Basidiomycota, Agaricomycetes)",
            "symptoms": "Oval grayish-green water-soaked lesions just above the water line, expanding into distinctive snake-skin banding patterns with dark brown margins; dark globose sclerotia on leaf sheaths.",
            "etiology": "Floating sclerotia attach to tillers, form lobed infection cushions, and penetrate epidermal cells with cutinases and cellulases under high humidity (>95%) and warm temperatures (28-32°C).",
            "treatment": "Spray validamycin (3% L at 2 ml/L) or azoxystrobin (FRAC 11) / Nativo (trifloxystrobin + tebuconazole) at boot leaf emergence; burn post-harvest stubble.",
            "ipm_action": "Incorporate Trichoderma viride or Pseudomonas fluorescens in nursery; optimize plant spacing to reduce canopy humidity.",
            "lab_test": "Microscopic observation of right-angled hyphal branching with diagnostic septal constriction."
        },
        "Cotton Leaf Curl Virus": {
            "division": "Division 3: Plant Virology & Vectors (ICAR)",
            "disease": "Cotton Leaf Curl Virus (CLCuV)",
            "pathogen": "Cotton Leaf Curl Virus (CLCuV)",
            "kingdom": "Virus (ssDNA Begomovirus with DNA-beta satellite)",
            "symptoms": "Upward or downward leaf curling, swollen thickened primary and secondary veins, and diagnostic cup-shaped leaf-like enation outgrowths on abaxial leaf veins; extreme stunting and reduced bolls.",
            "etiology": "Transmitted in a persistent-circulative manner by the silverleaf whitefly (Bemisia tabaci); DNA-beta satellite encodes betaC1 protein that dismantles host transcriptional gene silencing.",
            "treatment": "Manage whitefly vectors with azadirachtin (1500 ppm), diafenthiuron (50% WP), or flonicamid (50% WG); eradicate weed reservoir hosts (Parthenium, Sida cordifolia).",
            "ipm_action": "Plant CLCuV-resistant or tolerant Bt-cotton hybrids; install yellow sticky traps for vector scouting.",
            "lab_test": "PCR amplification using Begomovirus degenerate primers (SPG1/SPG2); DNA-beta satellite PCR."
        },
        "Cotton Bacterial Blight": {
            "division": "Division 2: Agricultural Bacteriology (ICAR)",
            "disease": "Cotton Bacterial Blight (Black Arm Phase)",
            "pathogen": "Xanthomonas citri pv. malvacearum",
            "kingdom": "Bacterium (Pseudomonadota, Gammaproteobacteria)",
            "symptoms": "Water-soaked angular leaf spots bounded by veinlets, spreading into sunken jet-black girdling cankers on branches ('black arm' phase) that snap in wind; oily brown water-soaked boll rot.",
            "etiology": "Seed-borne and rain-splashed bacterium entering stomata and micro-wounds; vascular colonization girdles branch cambium.",
            "treatment": "Acid-delinting of seed with concentrated sulfuric acid (100 ml/kg seed for 2-3 min); foliar spray of copper oxychloride (0.3%) mixed with streptocycline (100 ppm).",
            "ipm_action": "Plant acid-delinted certified disease-free seed; destroy crop residue; avoid overhead irrigation.",
            "lab_test": "10-Second 3% KOH String Test (Gram-negative slime thread); bacterial streaming assay."
        },
        "Chickpea Fusarium Wilt": {
            "division": "Division 1: Fungi & Oomycetes (ICAR)",
            "disease": "Chickpea Fusarium Wilt (Chana Wilt)",
            "pathogen": "Fusarium oxysporum f. sp. ciceri",
            "kingdom": "Fungus (Ascomycota, Sordariomycetes)",
            "symptoms": "Sudden drooping of petioles and rachis ('drooping wilt') in early seedlings; splitting the taproot and collar reveals prominent dark brown to black internal xylem vascular discoloration.",
            "etiology": "Soil-borne chlamydospores invade root vascular bundles, secreting fusaric acid toxin and plugging xylem vessels with microconidia and host tyloses.",
            "treatment": "Seed treatment with carbendazim + thiram (1:1 at 2 g/kg seed) or Trichoderma harzianum (4 g/kg); perform deep summer plowing to expose chlamydospores.",
            "ipm_action": "Plant wilt-resistant chickpea varieties (JG-315, Avrodhi, Pusa-391); enforce 3-4 year crop rotation with non-hosts (sorghum, wheat).",
            "lab_test": "Komada's selective medium vascular isolation; ITS1/ITS4 fungal ribosomal PCR."
        },
        "Pigeonpea Sterility Mosaic": {
            "division": "Division 3: Plant Virology & Vectors (ICAR)",
            "disease": "Pigeonpea Sterility Mosaic Disease (SMD / Arhar)",
            "pathogen": "Pigeonpea Sterility Mosaic Virus (PSMV)",
            "kingdom": "Virus (Multi-segmented -ssRNA Emaravirus)",
            "symptoms": "The 'green plague' of pigeonpea: Extreme bushy stunting, chlorotic mosaic mottling, and complete cessation of flowering ('complete sterility')—plants remain perpetually green and set zero pods.",
            "etiology": "Transmitted semi-persistently by the microscopic wind-borne eriophyid mite Aceria cajani.",
            "treatment": "Spray miticides (fenazaquin 10% EC at 2 ml/L or propargite 57% EC at 2.5 ml/L) during early vegetative flush to eliminate the eriophyid mite vector; rogue early sterile bushes.",
            "ipm_action": "Plant SMD-resistant pigeonpea cultivars (BSMR-736, BSMR-853, Asha / ICPL-87119); barrier crops to block mite drift.",
            "lab_test": "RT-PCR targeting the RNA-dependent RNA polymerase (RdRp) of PSMV; microscopic inspection of Aceria cajani mites."
        },
        "Sugarcane Red Rot": {
            "division": "Division 1: Fungi & Oomycetes (ICAR)",
            "disease": "Sugarcane Red Rot",
            "pathogen": "Colletotrichum falcatum (Glomerella tucumanensis)",
            "kingdom": "Fungus (Ascomycota, Sordariomycetes)",
            "symptoms": "Third or fourth leaf from spindle withers and dries; longitudinal split of cane stalk reveals blood-red pith tissue with diagnostic white transverse cross-patches and an intense sour alcoholic fermentation odor.",
            "etiology": "Fungus hydrolyzes sucrose into ethyl alcohol; secretes falcatins and pectinolytic enzymes, causing systemic vascular reddening, shriveling, and cane collapse.",
            "treatment": "Hot water treatment of seed setts at 52°C for 30 minutes; dip setts in carbendazim (0.1%); avoid ratoon cropping in infected fields; rogue diseased stools.",
            "ipm_action": "Plant certified red-rot resistant varieties (Co 0238, Co 86032); avoid waterlogging in cane fields.",
            "lab_test": "Microscopic identification of sickle-shaped (falcate) unicellular conidia with oil globules; dark acervuli with setae."
        },
        "Citrus Greening Huanglongbing": {
            "division": "Division 2: Agricultural Bacteriology (ICAR)",
            "disease": "Citrus Greening / Huanglongbing (HLB)",
            "pathogen": "Candidatus Liberibacter asiaticus",
            "kingdom": "Bacterium (Fastidious phloem-limited alpha-proteobacterium)",
            "symptoms": "Asymmetrical foliar 'blotchy mottle' chlorosis (unlike symmetrical zinc deficiency); small, lopsided, deformed bitter fruit with inverted greening at stylar end and dark aborted seeds.",
            "etiology": "Phloem-restricted uncultured bacterium clogging sieve tubes and disrupting starch translocation, transmitted by the Asian citrus psyllid (Diaphorina citri).",
            "treatment": "Vector suppression targeting Diaphorina citri with imidacloprid (17.8% SL) or dimethoate; remove severely declining trees; plant certified psyllid-free nursery stock.",
            "ipm_action": "Area-wide psyllid vector management; foliar micronutrient sprays to sustain tree productivity.",
            "lab_test": "Real-time qPCR targeting 16S rDNA or beta-operon of Candidatus Liberibacter asiaticus."
        },
        "Mango Malformation": {
            "division": "Division 1: Fungi & Oomycetes (ICAR)",
            "disease": "Mango Malformation",
            "pathogen": "Fusarium mangiferae",
            "kingdom": "Fungus (Ascomycota, Hypocreales)",
            "symptoms": "Hypertrophied, hyper-branched, compact, cauliflower-like fleshy floral clusters with sterile male flowers setting zero fruit; vegetative 'bunchy top' in seedlings.",
            "etiology": "Fungal infection in floral buds disrupts hormonal balance (hyper-accumulation of malformin toxins and cytokinins); carried by mango bud mite (Aceria mangiferae).",
            "treatment": "Mechanical pruning of malformed panicles with 15-20 cm healthy shoot; spray NAA (200 ppm) in October to delay panicle emergence; spray carbendazim (0.1%) or captan at bud break.",
            "ipm_action": "Spray wettable sulfur (0.2%) to suppress bud mites; sanitize pruning tools.",
            "lab_test": "Microscopic identification of microconidia in false heads and absence of chlamydospores; beta-tubulin gene sequencing."
        }
    }

    def __init__(self, book_engine: Optional[BookEngine] = None, classifier=None):
        super().__init__(name='Plant Pathology Candidate Adapter', description='Combines an optional neural classifier, condition-reference rules and retrieval; candidates are not confirmed diagnoses.')
        self.book_engine = book_engine or BookEngine()
        self.classifier = classifier if classifier is not None else NeuralPathologyClassifier()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = str(context.get("query") or "").strip()
        species = str(context.get("species") or "").strip()
        combined = f"{query} {species}"
        pred = self.classifier.predict(combined)
        disease = pred.get("disease") if not pred.get("abstained", True) else None
        score = pred.get("disease_confidence") if disease else None
        source = "neural_candidate" if disease else "unavailable"
        # The current small lexical classifier cannot reliably resolve negation.
        # Do not override an explicit negative or healthy description with a label.
        has_negation = contains_any(combined, ["no", "not", "never", "without", "ruled out", "healthy"])
        if has_negation:
            disease, score, source = None, None, "insufficient_evidence"
        # A named condition can be looked up as a reference, never as a diagnosis
        # of the user's specimen. This remains useful before a model is installed.
        if not disease and not has_negation:
            for name, profile in self.CLINICAL_PROFILES.items():
                if contains_term(combined, name) or contains_term(combined, profile["pathogen"]):
                    disease, source = name, "named_condition_reference"
                    break
        citations = self.book_engine.search(query=combined, shelf="pathology", top_k=2)
        keywords = ["disease", "blight", "mildew", "wilt", "rot", "canker", "spot", "spots",
                    "scab", "lesion", "lesions", "pathogen", "fungal", "bacterial", "viral",
                    "virus", "nematode", "chlorosis", "healthy", "yellow", "yellowing", "crop"]
        relevant = bool(disease) or contains_any(combined, keywords)
        if not relevant:
            return {"relevant": False, "status": "unsupported", "message": "No supported plant pathology task matched."}
        common = {"relevant": True, "domain": "Plant Pathology", "source": source,
                  "diagnosis_confirmed": False, "neural_confidence": round(score * 100, 1) if score is not None else None,
                  "score_type": "uncalibrated_softmax" if score is not None else "not_available",
                  "textbook_citations": citations, "textbook_citation": citations[0] if citations else None,
                  "clinical_treatment": None, "ipm_action": None, "recommended_lab_assay": None,
                  "model_available": bool(pred.get("available", False))}
        profile = self.CLINICAL_PROFILES.get(disease)
        if not profile:
            return {**common, "status": "insufficient_evidence", "pathology_condition": "Undetermined",
                    "message": "No supported disease candidate. Provide the host, affected tissue, observed and absent symptoms, and test results.",
                    "model_reason": pred.get("reason"), "clinical_division": "Unresolved condition"}
        return {**common, "status": "candidate" if source == "neural_candidate" else "reference_only",
                "clinical_division": profile.get("division", "Reference profile"),
                "pathology_condition": f"{disease} ({profile['pathogen']})",
                "pathogen_latin_name": profile["pathogen"], "causal_kingdom": profile["kingdom"],
                "symptoms_profile": profile["symptoms"], "pathogen_mode_of_action": profile["etiology"],
                "reference_review_status": "unreviewed_legacy_profile",
                "message": "Condition reference only; the stored profile has not been independently reviewed. Management recommendations are not generated from this label.",
                "disease_triangle_risk": DiseaseTriangleEngine.evaluate_outbreak_risk(disease_name=disease, query=combined)}


# Compatibility for existing integrations and model-training imports.
PathologyExpert = PathologyCandidateAdapter
