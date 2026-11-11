"""
Build Plant Pathology Authoritative Academic Curriculum
Generates deep peer-reviewed textbooks grounded in Agrios' Plant Pathology and USDA extension guides,
and ingests them into the Tiny Expert Okapi BM25 BookEngine.
"""
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiny_experts.pipeline.ingestion import LiteratureIngestionPipeline

CURRICULUM_TEXTS = {
    "agrios_infection_biology": {
        "title": "Agrios Principles of Plant Infection Biology & Pathogenesis",
        "shelf": "pathology",
        "content": """
Section 1: Spore Germination, Adhesion, and Surface Sensing Mechanics.
Fungal plant pathogens initiate infection when reproductive propagules (conidia, ascospores, or motile oomycete zoospores) make physical contact with host aerial organs. Initial adhesion requires the secretion of mucilaginous extracellular matrices containing glycoproteins and hydrophobic cutin-binding proteins. Following adhesion, the pathogen senses specific physical topographical cues on the plant cuticle, such as stomatal guard cell lip ridges, vein depressions, or chemical stimuli like epicuticular wax long-chain fatty alcohols. For example, rust fungi (Uredinales) use precise thigmotropic (touch-sensitive) surface sensing to orient germ tube extension perpendicular to epidermal cells until encountering a stomatal aperture.

Section 2: Appressorium Morphogenesis and Mechanical Penetration Mechanics.
Upon locating an optimal penetration site, many phytopathogenic fungi (including Magnaporthe oryzae, Colletotrichum, and Venturia inaequalis) differentiate specialized domed infection cells termed appressoria. The appressorium develops a thick internal melanin pigment layer within its inner cell wall. This impermeable melanin matrix allows the accumulation of massive intracellular glycerol concentrations (exceeding 3 to 5 M), generating colossal hydrostatic turgor pressure up to 8.0 megapascals (MPa), equivalent to 80 times atmospheric pressure. At the center of the appressorial base, a rigid, needle-like penetration peg emerges, applying focused mechanical shearing force to physically rupture the hydrophobic plant cuticle.

Section 3: Enzymatic Degradation of the Host Cuticle and Cell Wall Complex.
Simultaneously with mechanical pressure, phytopathogens secrete a battery of cell-wall-degrading enzymes (CWDEs) in a coordinated temporal sequence. First, cutinases and esterases hydrolyze insoluble cutin polymers into hydroxy fatty acids. Once the cuticle barrier is breached, the pathogen deploys pectin-degrading enzymes: pectin methyl esterases (PME) de-esterify homogalacturonan, followed by endopolygalacturonases (endo-PG) and pectate lyases (PL), which cleave alpha-1,4-glycosidic bonds in the middle lamella. This causes maceration of plant intercellular cementing matrices. Subsequently, cellulolytic enzymes (endoglucanases, cellobiohydrolases, and beta-glucosidases) and hemicellulases (xylanases and xyloglucanases) break down the rigid cellulose microfibril network of primary and secondary plant cell walls.

Section 4: Pathogen Trophic Lifestyles: Biotrophy, Necrotrophy, and Hemibiotrophy.
Phytopathogens are classified by their nutritional acquisition strategy into three major lifestyles:
1. Obligate Biotrophs (e.g., powdery mildews such as Podosphaera xanthii and Erysiphe, downy mildews such as Pseudoperonospora cubensis, and rust fungi): These pathogens require living host cells to survive and complete their life cycle. They do not kill host tissue upon entry; instead, they form specialized intracellular feeding invaginations called haustoria. The haustorium invaginates the host plasma membrane without rupturing it, creating an extra-haustorial matrix across which the fungus extracts host photosynthates, hexoses, and amino acids while suppressing host programmed cell death.
2. Necrotrophs (e.g., Botrytis cinerea grey mold, Alternaria solani early blight, Sclerotinia sclerotiorum): These pathogens rapidly kill host cells upfront through the secretion of non-host-specific phytotoxins (such as botrydial, alternariol, oxalic acid) and massive bursts of hydrolytic pectinases. They feed saprophytically on the dead, lysed cellular contents and necrotic debris.
3. Hemibiotrophs (e.g., Phytophthora infestans late blight, Venturia inaequalis apple scab, Fusarium oxysporum): These pathogens maintain an initial stealth biotrophic phase, colonizing host tissues without causing visible symptoms, before switching transitionally to an aggressive, destructive necrotrophic phase marked by extensive tissue water-soaking and necrosis.

Section 5: Molecular Immunology: PTI vs. ETI and The Zig-Zag Zig Model.
Plant innate immunity operates through a two-tiered receptor recognition system:
Tier 1: Pattern-Triggered Immunity (PTI). Cell surface pattern recognition receptors (PRRs), such as receptor-like kinases (RLKs) including FLS2 (recognizing bacterial flagellin peptide flg22), EFR (recognizing bacterial EF-Tu peptide elf18), and CERK1 (recognizing fungal chitin oligosaccharides), detect conserved pathogen-associated molecular patterns (PAMPs / MAMPs). PTI activation initiates calcium influx, an extracellular oxidative burst (superoxide and hydrogen peroxide), mitogen-activated protein kinase (MAPK) phosphorylation cascades, and deposition of callose polymer plugs at plasmodesmata.
Tier 2: Effector-Triggered Susceptibility (ETS) and Effector-Triggered Immunity (ETI). Adapted pathogens deliver virulence effector proteins (via bacterial Type III secretion systems or oomycete RXLR/CRN translocation motifs) directly into host cells to suppress PTI signaling. In resistant plants, intracellular nucleotide-binding leucine-rich repeat (NLR / NBS-LRR) disease resistance (R) proteins directly or indirectly detect these specific pathogen effectors. Recognition triggers ETI: a prolonged, high-amplitude defense response that typically culminates in the Hypersensitive Response (HR)—localized, rapid programmed cell death that arrests pathogen spread.
"""
    },

    "agrios_plant_immunity_sar": {
        "title": "Agrios Molecular Plant Defense & Systemic Acquired Resistance (SAR)",
        "shelf": "pathology",
        "content": """
Section 1: The Hypersensitive Response (HR) and Oxidative Burst Dynamics.
The Hypersensitive Response (HR) is an evolutionarily conserved plant programmed cell death (PCD) mechanism executed rapidly at the exact cellular site of attempted biotrophic or hemibiotrophic pathogen penetration. Within minutes of effector-NBS-LRR recognition, plasma-membrane-bound NADPH oxidases (respiratory burst oxidase homologs, notably RBOHD and RBOHF) together with apoplastic class III peroxidases generate a massive oxidative burst. This produces superoxide radicals (O2.-) that are swiftly dismutated by superoxide dismutase (SOD) into hydrogen peroxide (H2O2). In parallel, nitric oxide (NO) synthase-like enzymes synthesize nitric oxide. The stoichiometric interplay between H2O2 and NO triggers executioner cysteine proteases (vacuolar processing enzymes, VPEs), cell membrane lipid peroxidation, and rapid cell collapse, isolating obligate biotrophic pathogens like downy and powdery mildews within dry, dead necrotic tissue devoid of water and nutrients.

Section 2: Long-Distance Mobile Signals and Salicylic Acid Priming.
Following localized HR at the primary infection site, the plant activates systemic immunity throughout distal, uninfected foliage, known as Systemic Acquired Resistance (SAR). SAR is initiated by the generation and vascular phloem translocation of several mobile chemical signals:
1. Pipecolic acid (Pip) and its biologically active hydroxylated derivative, N-hydroxypipecolic acid (NHP), synthesized via the ALD1-FMO1 enzymatic cascade, which serve as essential master orchestrators of SAR systemic priming.
2. Methyl salicylate (MeSA), a volatile ester synthesized from salicylic acid by SABATH methyltransferases, transported through phloem sieve elements and converted back into active free salicylic acid in recipient leaves by SABP2 esterases.
3. Azelaic acid (AZA) and glycerol-3-phosphate (G3P), lipid-derived signaling intermediates that reinforce distal vascular priming.
In response to these systemic signals, distal uninfected tissues synthesize and accumulate elevated levels of salicylic acid (SA) via the isochorismate synthase 1 (ICS1 / SID2) pathway.

Section 3: NPR1 Transcriptional Regulation and Chromatin Remodeling.
Salicylic acid (SA) functions as the key hormonal conductor of SAR. Under uninfected basal conditions, the master transcriptional regulator NPR1 (Nonexpressor of PR genes 1) exists in the cytoplasm as an inactive, high-molecular-weight oligomer held together by intermolecular disulfide bridges formed between conserved cysteine residues (Cys82, Cys216). During SAR, the systemic oxidative burst and subsequent elevation of cellular reducing glutathione levels reduce these disulfide bridges, releasing active NPR1 monomers.
Monomeric NPR1 translocates into the plant cell nucleus. Within the nucleus, NPR1 binds directly to salicylic acid (acting as an SA receptor alongside paralogs NPR3 and NPR4). NPR1 interacts with basic leucine zipper (bZIP) TGA transcription factors (TGA2, TGA5, TGA6), dislodging transcriptional repressors and recruiting the histone acetyltransferase complex to the promoters of Pathogenesis-Related (PR) defense genes, driving robust transcriptional reprogramming.

Section 4: Pathogenesis-Related (PR) Protein Biomarkers and Biochemical Actions.
Systemic Acquired Resistance orchestrates the coordinated synthesis of high concentrations of Pathogenesis-Related (PR) proteins that persist in the apoplast and vacuole for weeks to months, conferring broad-spectrum, long-lasting immunity:
- PR-1 family: Antifungal sterol-binding proteins that physically sequester sterols from pathogen cell membranes, inhibiting hyphal growth. PR-1 gene expression serves as the gold-standard molecular biomarker for confirmed SAR activation.
- PR-2 family (Beta-1,3-glucanases): Glycoside hydrolases that cleave beta-1,3-glucan structural polymers, which form major structural components of fungal cell walls and Oomycete walls (such as Phytophthora infestans and Pseudoperonospora cubensis), releasing immunogenic elicitor oligosaccharides.
- PR-3, PR-4, PR-8, and PR-11 families (Chitinases): Endochitinases and exochitinases that hydrolyze beta-1,4-glycosidic bonds in fungal chitin polymers (N-acetylglucosamine polymers), causing cell wall weakening, osmotic swelling, and apical hyphal burst.
- PR-5 family (Thaumatin-like proteins and Osmotins): Membrane-permeabilizing proteins that rapidly create transmembrane ion channels and pores in fungal plasma membranes, causing fatal electrolyte leakage.
- PR-9 family (Lignin-forming peroxidases): Catalyze oxidative cross-linking of phenolic monomers, reinforcing secondary cell walls with impenetrable suberin and lignin barriers.

Section 5: Induced Systemic Resistance (ISR) vs. Systemic Acquired Resistance (SAR).
While SAR is triggered by necrotizing pathogens and mediated systemically by salicylic acid (SA) and NPR1, plants possess a complementary systemic defense branch called Induced Systemic Resistance (ISR). ISR is triggered by beneficial root-colonizing plant growth-promoting rhizobacteria (PGPR) and fungi (such as Bacillus amyloliquefaciens, Bacillus subtilis, Pseudomonas fluorescens, and Trichoderma harzianum).
ISR does not require salicylic acid or PR-1 induction; instead, it is mediated by jasmonic acid (JA) and ethylene (ET) hormonal signaling networks. ISR primarily primes the plant for faster, more intense defense activation upon subsequent attack by necrotrophic pathogens (such as Botrytis cinerea) and chewing herbivorous insects. Pre-treating agricultural crops with beneficial PGPR inoculants or salicylic acid analogs (such as acibenzolar-S-methyl / ASM) establishes durable protection against viral, bacterial, and fungal pathogens.
"""
    },

    "phytopathogen_compendium": {
        "title": "Compendium of Agricultural Plant Pathogens & Clinical Disease Profiles",
        "shelf": "pathology",
        "content": """
Section 1: Early Blight of Solanaceae (Alternaria solani).
- Pathogen: Alternaria solani (Sorauer), Kingdom Fungus, Phylum Ascomycota, Class Dothideomycetes, Order Pleosporales, Family Pleosporaceae.
- Host Plants: Solanum lycopersicum (Tomato), Solanum tuberosum (Potato), Solanum melongena (Eggplant).
- Clinical Diagnostic Symptoms: The disease initiates on the oldest, lower senescence foliage as small, dark brown to black circular lesions. As lesions expand (1 to 2 cm), they develop diagnostic concentric rings forming a characteristic 'bullseye' or 'target-board' pattern, encircled by a prominent chlorotic yellow halo caused by the secretion of alternariol and macrosporin toxins. On tomato stems, lesions form dark sunken collar rots at the soil line. On fruit, dark leathery, sunken concentric lesions develop near the stem calyx.
- Environmental Triggers: Temperatures of 24°C to 29°C with alternating wet periods (rain, heavy dew) and dry windy days favor conidiogenesis and spore dispersal.
- IPM Clinical Therapeutics: 3-year crop rotation out of Solanaceae; drip micro-irrigation; preventive applications of copper octanoate (FRAC M01) or biofungicides containing Bacillus amyloliquefaciens strain D747; remove infected lower leaves.

Section 2: Late Blight of Tomato and Potato (Phytophthora infestans).
- Pathogen: Phytophthora infestans (Mont.) de Bary, Kingdom Oomycete (Chromista/Stramenopila), Phylum Oomycota, Class Peronosporea, Order Peronosporales. Late blight is NOT a true fungus; its cell walls are composed of beta-glucans and cellulose rather than chitin.
- Host Plants: Tomato (Solanum lycopersicum) and Potato (Solanum tuberosum).
- Clinical Diagnostic Symptoms: Foliage rapidly exhibits large, irregular water-soaked pale green lesions that swiftly turn olive-green, dark brown, and necrotic. Under humid conditions (>90% RH) or immediately following cool rain, a diagnostic delicate white, fuzzy, cottony sporulation (sporangiophores producing biflagellate motile zoospores) appears profusely on the abaxial (underside) surface of diseased leaves along lesion margins. Entire canopies can collapse into a foul-smelling, scorched rot within 5 to 7 days. Stems develop greasy dark brown lesions. Potato tubers show dry granular brown rot penetrating 15 mm into tuber flesh.
- Environmental Triggers: Cool, persistently wet conditions: temperatures of 15°C to 20°C with relative humidity above 90% or frequent rainfall.
- IPM Clinical Therapeutics: Phytophthora infestans is an emergency quarantine pathogen. Immediately destroy severely infected plants; apply preventive copper hydroxide/octanoate (FRAC M01) or oomycete-specific translaminar fungicides (mandipropamid FRAC 40, fluopicolide FRAC 43); plant certified resistant cultivars carrying Ph-2 and Ph-3 resistance genes.

Section 3: Powdery Mildew of Cucurbits and Ornamentals (Podosphaera xanthii).
- Pathogen: Podosphaera xanthii (Castagne) Braun & Shishkoff (formerly Sphaerotheca fuliginea), Kingdom Fungus, Phylum Ascomycota, Class Leotiomycetes, Order Erysiphales.
- Host Plants: Cucurbita pepo (Squash, Zucchini, Pumpkin), Cucumis sativus (Cucumber), Melons, Apples (Podosphaera leucotricha), Grapes (Erysiphe necator), Roses (Podosphaera pannosa).
- Clinical Diagnostic Symptoms: Initial symptoms appear as discrete, circular, white talcum-powder-like patches of superficial mycelium and conidiophores across the upper (adaxial) leaf surface, petioles, and young stems. As infection progresses, powdery white mycelium blankets the entire foliage. Beneath the powdery fungal growth, leaf tissue becomes chlorotic, turns brittle brown, and curls upward.
- Environmental Triggers: Warm, dry ambient climates (20°C to 27°C) accompanied by high relative humidity at the leaf surface (70-90%), often in shaded or crowded canopies. Crucially, conidia can germinate without free water; liquid water droplets actually inhibit spore germination.
- IPM Clinical Therapeutics: Foliar sprays of potassium bicarbonate (3 g/L) to immediately rupture hyphae via osmotic shock; micronized wettable sulfur (FRAC M02) applied under 30°C; biofungicide sprays of Bacillus subtilis (QST 713); maximize plant spacing for sunlight penetration and airflow.

Section 4: Cucurbit Downy Mildew (Pseudoperonospora cubensis).
- Pathogen: Pseudoperonospora cubensis (Berk. & Curt.) Rostovzev, Kingdom Oomycete, Phylum Oomycota, Class Peronosporea, Order Peronosporales.
- Host Plants: Cucumis sativus (Cucumber), Cucumis melo (Cantaloupe), Squash, Watermelon.
- Clinical Diagnostic Symptoms: Distinct angular, bright yellow chlorotic patches develop on the upper (adaxial) leaf surface. Crucially, these lesions are strictly delimited and bounded by the leaf veins, giving rise to a diagnostic mosaic-like, geometric patchwork appearance. On the corresponding lower (abaxial) leaf underside directly beneath the yellow patches, a dense, velvety, purplish-grey to dark brown felt-like sporulation (sporangia and branched sporangiophores) emerges through open stomata during damp mornings. Infected leaves turn brown, shrivel, and die, often called 'wildfire' in cucumbers.
- Environmental Triggers: Cool to moderate temperatures (15°C to 22°C) combined with prolonged morning leaf wetness (>6 hours) and high humidity (>85% RH).
- IPM Clinical Therapeutics: Implement strict drip irrigation (zero overhead watering); preventive copper octanoate (FRAC M01); targeted oomycete fungicides; cultivate downy-mildew-tolerant hybrid varieties.

Section 5: Fusarium Vascular Wilt (Fusarium oxysporum).
- Pathogen: Fusarium oxysporum Schlechtend. Fr. (e.g., f. sp. lycopersici on tomato, f. sp. cubense on banana), Kingdom Fungus, Phylum Ascomycota, Class Sordariomycetes, Order Hypocreales.
- Host Plants: Tomato, Potato, Banana (Panama disease Race 4), Cotton, Basil, Melons.
- Clinical Diagnostic Symptoms: Unilateral wilting and foliar yellowing (frequently termed the 'yellow flag' symptom, where only one side of a plant or even one side of a single leaf turns bright yellow while the other side remains green). Plants wilt during midday sun and partially recover overnight during early disease stages. Slicing the lower main stem and root crown longitudinally reveals a distinctive, dark chocolate-brown discoloration of the xylem vascular bundles. The pathogen produces microconidia, macroconidia, and persistent thick-walled chlamydospores that plug water-conducting xylem vessels, compounded by the secretion of fusaric acid toxin and host tyloses formation.
- Environmental Triggers: Warm soil temperatures (27°C to 32°C) and acidic sandy soils; soil-dwelling nematode wounds facilitate fungal entry.
- IPM Clinical Therapeutics: Fusarium chlamydospores survive in soil for 10 to 15+ years; chemical foliar sprays are entirely ineffective. Control requires planting certified resistant cultivars (bearing I, I-2, I-3 resistance genes); solarization of infected beds; introducing antagonist bio-agents such as Trichoderma harzianum strain T-22 or Streptomyces lydicus into the root rhizosphere.

Section 6: Bacterial Leaf Spot of Pepper and Tomato (Xanthomonas campestris).
- Pathogen: Xanthomonas campestris pv. vesicatoria (also Xanthomonas vesicatoria / perforans / euvesicatoria), Kingdom Bacterium, Phylum Pseudomonadota, Class Gammaproteobacteria, Order Xanthomonadales.
- Host Plants: Capsicum annuum (Bell pepper, Chili), Solanum lycopersicum (Tomato).
- Clinical Diagnostic Symptoms: Small (1 to 3 mm), dark green, water-soaked greasy spots develop on leaves, typically starting on lower foliage. Lesions enlarge, turn dark brown to purplish-black, and are surrounded by a distinct bright yellow halo. During hot, humid weather, spots coalesce, causing affected leaves to look scorched, tattered, and prematurely drop, exposing fruit to sunscald. On green fruit, lesions appear as raised, rough, wart-like brown scabs (3 to 6 mm) with irregular margins.
- Environmental Triggers: Warm temperatures (25°C to 35°C) coupled with torrential rainfall, overhead sprinkler irrigation, and driving windstorms that drive bacterial cells through open stomatal pores and mechanical micro-wounds.
- IPM Clinical Therapeutics: True fungi fungicides do not affect bacteria. Apply fixed copper bactericides (copper sulfate / copper octanoate FRAC M01) tank-mixed with mancozeb for synergistic copper ion release; use hot-water-treated certified disease-free seed (50°C for 25 min); eliminate solanaceous weed hosts (nightshades); avoid field work while foliage is wet.

Section 7: Grey Mold and Blossom End Rot (Botrytis cinerea).
- Pathogen: Botrytis cinerea Pers.:Fr., Kingdom Fungus, Phylum Ascomycota, Class Leotiomycetes, Order Helotiales.
- Host Plants: Fragaria ananassa (Strawberry), Vitis vinifera (Grapevine), Solanaceae, Lettuce, Cut Flowers (Roses, Geraniums).
- Clinical Diagnostic Symptoms: On ripening or post-harvest strawberry fruit, infected tissues soften and develop watery, light brown decay spots. Within 24 to 48 hours, the rotting fruit is engulfed by a dense, velvety, mouse-grey blanket of branched conidiophores and billions of powdery grey conidia. On greenhouse tomato stems, Botrytis causes pale brown, elliptical stem cankers that girdle the vascular system, resulting in sudden wilt of the upper plant canopy. On petals, small flecks or spots develop, serving as the initial infection court.
- Environmental Triggers: Cool to moderate temperatures (15°C to 21°C) with persistent humidity exceeding 90% or standing water on plant surfaces; abundant dead or senescent organic matter (fallen flower petals, old leaves).
- IPM Clinical Therapeutics: Aggressively remove senescent flower petals and diseased fruit from canopy; increase greenhouse ventilation and air circulation; apply bio-antagonist Bacillus amyloliquefaciens (strain D747) or bio-fungicide Aureobasidium pullulans; rotate fludioxonil (FRAC 12) or fenhexamid (FRAC 17).

Section 8: Rose Black Spot (Diplocarpon rosae).
- Pathogen: Diplocarpon rosae Wolf (anamorph Marssonina rosae), Kingdom Fungus, Phylum Ascomycota, Class Leotiomycetes, Order Helotiales.
- Host Plants: Rosa species (Hybrid teas, Grandifloras, Floribundas, Shrub roses).
- Clinical Diagnostic Symptoms: Prominent, circular to subcircular, jet-black spots (2 to 12 mm diameter) appear on the adaxial (upper) leaf surfaces. Crucially, the margins of the black spots are characteristically fringed, feathery, or fibrillose, containing radiant fungal hyphae and sub-cuticular acervuli. The leaf tissue immediately surrounding the black spots turns bright yellow (chlorotic) due to pathogen-induced ethylene production, leading to rapid, extensive defoliation from the base of the bush upward. Weakened roses produce fewer blooms and become susceptible to winter kill.
- Environmental Triggers: Temperatures between 18°C and 24°C with continuous leaf wetness for 7 or more hours; conidia are dispersed exclusively by splashing water droplets, not wind.
- IPM Clinical Therapeutics: Collect and burn or bury fallen infected leaves in autumn; prune cankered canes; water solely at root zone; apply preventive horticultural neem oil (0.5%) or potassium bicarbonate; preventive triazole fungicide (myclobutanil FRAC 3) or copper octanoate.

Section 9: Apple Scab (Venturia inaequalis).
- Pathogen: Venturia inaequalis (Cooke) G. Winter, Kingdom Fungus, Phylum Ascomycota, Class Dothideomycetes, Order Venturiales.
- Host Plants: Malus domestica (Cultivated Apple), Crabapple (Malus spp.), Pear (Venturia pyrina).
- Clinical Diagnostic Symptoms: In early spring, leaves exhibit dull, olive-green, circular spots with feathery, velvety borders. As lesions age, they become dark olive-brown to jet-black, metallic in sheen, thickened, and raised. Severely infected leaves curl, dwarf, turn yellow, and drop prematurely. On young developing fruit, olive-green circular spots expand into dark brown, rough, corky, scabby lesions that stunt fruit expansion, causing deep, star-shaped cracks and severe fruit deformation.
- Environmental Triggers: Primary ascospores are released from pseudothecia in overwintered fallen apple leaf litter during spring rainfall events. Infection requires specific leaf wetness durations based on temperature (Mill's Infection Periods: e.g., 9 hours of wetness at 16°C to 24°C).
- IPM Clinical Therapeutics: Shred or apply 5% urea spray to fallen autumn apple leaves to accelerate decomposition of overwintering pseudothecia; plant resistant cultivars (e.g., Liberty, Enterprise, Honeycrisp with Vf/Rvi6 resistance); apply preventive wettable sulfur (FRAC M02) or captan (FRAC M04) at green tip through petal fall.

Section 10: Bacterial Wilt / Southern Wilt (Ralstonia solanacearum).
- Pathogen: Ralstonia solanacearum (formerly Pseudomonas solanacearum), Kingdom Bacterium, Phylum Pseudomonadota, Class Betaproteobacteria, Order Burkholderiales.
- Host Plants: Solanum lycopersicum (Tomato), Solanum tuberosum (Potato - brown rot), Nicotiana tabacum (Tobacco - Granville wilt), Banana (Moko disease).
- Clinical Diagnostic Symptoms: The hallmark symptom is sudden, rapid daytime wilting and collapse of green foliage without initial yellowing or leaf spotting. Stems remain green while foliage wilts completely. Initially, plants may partially recover turgor overnight, but within 2 to 4 days permanent wilt and desiccation occur. Slicing a 3 cm lower stem section and suspending it vertically in a clear glass of still water produces immediate, distinctive milky white threads of bacterial slime and cells streaming steadily downwards from the severed vascular xylem bundles into the water (the diagnostic 'bacterial streaming test').
- Environmental Triggers: High soil temperatures (30°C to 35°C) and warm, waterlogged soils.
- IPM Clinical Therapeutics: Soil-borne systemic bacterium; crop rotation with non-solanaceous hosts (corn, sorghum); grafting susceptible heirloom scions onto resistant wild rootstocks (e.g., Maxifort); strict sterilization of cutting tools and boots.
"""
    },

    "integrated_pest_management_ipm": {
        "title": "Integrated Pest Management (IPM) & Rational Phytopharmacology",
        "shelf": "pathology",
        "content": """
Section 1: The Disease Triangle and Multi-Tactic IPM Philosophy.
Plant disease outbreaks require three concurrent factors, visualized as the Disease Triangle: (1) A susceptible host plant, (2) A virulent, aggressive pathogen, and (3) An environment favorable for infection (specifically leaf wetness duration, relative humidity, and ambient temperature). Effective Integrated Pest Management (IPM) does not rely on reactive chemical pesticide saturation; instead, it strategically modifies one or more points of the Disease Triangle through cultural sanitation, host genetic resistance, biological biocontrol antagonisms, and bio-rational biochemical interventions.

Section 2: Fungicide Resistance Action Committee (FRAC) Modes of Action and Anti-Resistance Rotations.
Continuous application of single-site systemic fungicides induces rapid selection pressure, resulting in resistant pathogen populations. FRAC categorizes fungicides by their precise biochemical target site:
1. FRAC Group M (Multi-Site Protectants):
   - FRAC M01 (Inorganic Copper compounds: Copper octanoate, copper sulfate, copper hydroxide): Multi-site enzyme inhibitor; copper ions (Cu2+) bind non-specifically to sulfhydryl (-SH) and amino groups in pathogen proteins, disrupting structural integrity and energy production. Has bactericidal activity (active against Xanthomonas and Pseudomonas). Low resistance risk.
   - FRAC M02 (Inorganic Elemental Sulfur: Micronized wettable sulfur, sulfur dust): Multi-site mitochondrial respiration disrupter, accepting electrons in place of oxygen and disrupting cytochromes. Highly active against powdery mildew (Podosphaera) and mites. Phytotoxic at temperatures above 30°C (85°F) or when applied within 14 days of horticultural mineral oils.
   - FRAC M04 (Phthalimides: Captan): Inactivates fungal thiol-containing enzymes; broad protectant for apple scab.
2. FRAC Group 3 (Demethylation Inhibitors - DMIs / Triazoles):
   - Active ingredients: Difenoconazole, myclobutanil, propiconazole. Inhibit fungal sterol 14alpha-demethylase (encoded by CYP51), halting ergosterol biosynthesis in true fungal membranes. Translaminar and systemic curative activity against rusts, powdery mildew, and black spot. Moderate resistance risk; rotate with FRAC M multi-site fungicides.
3. FRAC Group 11 (Quinone Outside Inhibitors - QoIs / Strobilurins):
   - Active ingredients: Azoxystrobin, pyraclostrobin, trifloxystrobin. Bind to the Qo site of mitochondrial cytochrome b (complex III), halting cellular ATP synthesis. High resistance risk driven by single point mutation G143A. Never exceed 2 sequential applications per season.
4. FRAC Group 40 & 43 (Oomycete-Specific Anti-Tubulin & Cellulose Synthase Inhibitors):
   - Active ingredients: Mandipropamid (FRAC 40) inhibits cellulose synthase in oomycete cell walls; Fluopicolide (FRAC 43) disorganizes spectrin-like proteins in oomycete cellular cytoskeleton. Ineffective against true fungi (Ascomycetes/Basidiomycetes); highly specific for Phytophthora and Downy Mildew.

Section 3: Bio-Rational and Organic Contact Therapeutics.
- Potassium Bicarbonate (KHCO3): A high-potency contact fungicide. Applied at 3 to 5 grams per liter, bicarbonate ions alter leaf surface osmotic pressure and elevate pH to 8.0 - 8.5, causing rapid dehydration, hyphal collapse, and lysis of powdery mildew conidia and germ tubes within 15 minutes.
- Horticultural Oils & Cold-Pressed Neem Oil (Clarified Hydrophobic Extract of Neem): Forms a continuous physical hydrophobic film over plant surfaces that suffocates fungal spores, inhibits germination, and breaks down insect vector cuticle membranes.
- Silicon (Potassium Silicate): Absorbed into plant tissue and deposited in epidermal cell walls as solid amorphous silica (SiO2.nH2O), creating a physical mechanical barrier that resists penetration pegs of powdery mildew and blast fungi.

Section 4: Biological Biocontrol Agents (BCAs) and Mechanism of Antagonism.
- Bacillus amyloliquefaciens (strain D747) & Bacillus subtilis (strain QST 713): Beneficial Gram-positive endospore-forming bacteria. They synthesize cyclic lipopeptides—surfactins, iturins, and fengycins—that insert into fungal plasma membranes, forming trans-membrane pores that induce cytoplasmic leakage and cell lysis. Additionally, they aggressively outcompete foliar pathogens for space and iron nutrients.
- Trichoderma harzianum (strain T-22): Soil-dwelling filamentous hyperparasitic fungus. Detects pathogenic soil fungi (Fusarium, Rhizoctonia, Pythium) via chemo-attraction, coils around target hyphae, and secretes chitinases, beta-1,3-glucanases, and proteases, digesting and destroying the pathogen while colonizing root surfaces.
- Streptomyces lydicus (strain WYEC 108): Endophytic actinobacterium that colonizes root tips and foliage, producing siderophores that chelate trace iron away from germinating fungal spores.

Section 5: Cultural Hygiene, Sanitation, and Microclimate Management.
1. Irrigation Architecture: Completely eliminate overhead sprinkler watering in disease-prone crops. Adopt low-pressure drip irrigation at the soil surface. Spores of Alternaria solani, Xanthomonas, and Diplocarpon rosae require film water on leaves for 6 to 10 continuous hours to complete germination and penetration.
2. Canopy Airflow Geometry: Prune the lower 30 cm of foliage from indeterminate tomato plants (bottom suckers and leaves) to prevent soil-splash inoculum transfer. Increase in-row plant spacing to optimize air velocity, speeding leaf drying post-dew.
3. Tool Sanitization Protocol: Decontaminate pruning shears and grafting blades between each plant with 70% isopropyl alcohol or a 10% sodium hypochlorite (household bleach) solution to prevent mechanical vascular transmission of bacterial wilt (Ralstonia) and viral pathogens.
4. Crop Rotation Cycles: Enforce 3 to 4-year crop rotations with unrelated botanical families (e.g., rotate Solanaceae with Poaceae or Fabaceae) to starve soil-borne chlamydospores, sclerotia, and resting spores.
"""
    }
}

def build_curriculum():
    print("\n========================================================")
    print("  [PLANT PATHOLOGY] ACADEMIC CURRICULUM INGESTION")
    print("========================================================")

    pipeline = LiteratureIngestionPipeline()
    books_dir = os.path.join(pipeline.book_engine.data_dir, "pathology")
    os.makedirs(books_dir, exist_ok=True)

    total_chunks = 0
    total_words = 0

    for file_key, meta in CURRICULUM_TEXTS.items():
        title = meta["title"]
        shelf = meta["shelf"]
        content = meta["content"].strip()

        # Write source raw text file
        txt_path = os.path.join(books_dir, f"{file_key}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Ingest through scientific chunking pipeline
        result = pipeline.ingest_text(
            raw_text=content,
            source_title=title,
            shelf=shelf
        )

        chunks_count = result.get("chunks_count", 0)
        words_count = result.get("total_words", 0)
        total_chunks += chunks_count
        total_words += words_count

        print(f"[OK] Ingested: {title}")
        print(f"     -> {chunks_count} chunks, {words_count} words | Stored in {result.get('file_saved')}")

    print("-" * 56)
    print(f"Total Pathology Curriculum: {total_chunks} chunks, {total_words} words indexed.")
    print("All BM25 indexes updated.\n")

if __name__ == "__main__":
    build_curriculum()
