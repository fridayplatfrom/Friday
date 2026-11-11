"""
Ingests the comprehensive, research-grade curriculum for the 6 Advanced Plant Pathology Divisions:
1. Plant Virology & Insect Vector Transmission
2. Advanced Agricultural Bacteriology & Cankers
3. Cereal Rusts, Rice Blast, and DON Mycotoxins
4. Plant Nematology & Soil Disease Complexes
5. Abiotic Disorders & Physiological Differential Diagnosis
6. Clinical Laboratory Diagnostic Protocols & PCR Primer Directory
7. FRAC Mode-of-Action Chemical Directory & Resistance Management
"""
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiny_experts.pipeline.ingestion import LiteratureIngestionPipeline

ADVANCED_CURRICULUM_TEXTS = {
    "advanced_plant_virology_vectors": {
        "title": "Clinical Plant Virology, Tobamoviruses & Insect Vector Transmission",
        "shelf": "pathology",
        "content": """
Section 1: Tobamoviruses and High-Threat Emerging Plant Viruses.
Plant viruses are submicroscopic obligate intracellular entities consisting of single-stranded or double-stranded RNA or DNA encapsulated within a protective protein capsid. Among agricultural crops, Tobamoviruses represent catastrophic threats due to their extreme physical stability and lack of insect vector requirement.
1. Tomato Brown Rugose Fruit Virus (ToBRFV): A positive-sense single-stranded RNA (+ssRNA) Tobamovirus breaking durable Tm-2 and Tm-2^2 resistance genes in commercial tomato and pepper hybrids. Diagnostic symptoms include chlorotic mosaic, bubbling, and narrowing (fern-leaf or shoe-stringing) of foliage, accompanied by yellow patches, brown necrotic rugose wrinkling, and marbling on fruit surfaces. Crucially, ToBRFV is seed-borne and mechanically transmitted via workers' hands, pruning tools, and greenhouse trellising wires, surviving on glasshouse surfaces for months.
2. Tobacco Mosaic Virus (TMV) and Tomato Mosaic Virus (ToMV): Rod-shaped virions consisting of a helical coat protein wrapping a 6.4 kb +ssRNA genome. Transmitted mechanically via plant-to-plant contact, sap contamination, and tobacco smoking residues. Management requires strict greenhouse sanitation, virucidal tool dipping in 10% trisodium phosphate (TSP) or 20% non-fat dry skim milk (which encapsulates and inactivates virions), and destroying infected crop blocks.

Section 2: Begomoviruses, Tospoviruses, and Insect Vector Transmission Dynamics.
Unlike mechanically stable Tobamoviruses, many economically devastating viruses require specific arthropod vectors for transmission:
1. Tomato Yellow Leaf Curl Virus (TYLCV): A circular single-stranded DNA (ssDNA) Begomovirus (family Geminiviridae) transmitted in a persistent-circulative manner by the silverleaf whitefly (Bemisia tabaci, specifically cryptic species MEAM1 and MED). Symptoms include severe internode stunting, upright bushy habit, interveinal foliar chlorosis, and upward cupping of leaf margins. Flower abscission reaches 100% if plants are infected before flowering. Vector management requires 50-mesh insect exclusion netting, systemic neonicotinoid or diamide insecticides, and planting cultivars with Ty-1, Ty-2, or Ty-3 resistance genes.
2. Tomato Spotted Wilt Virus (TSWV): A tripartite negative/ambisense single-stranded RNA (-/ambisense ssRNA) Tospovirus (family Peribunyaviridae) transmitted in a propagative-circulative manner by thrips, primarily Western flower thrips (Frankliniella occidentalis). Crucially, virions must be acquired by larval thrips during feeding on infected plants; adults transmit the virus for life. Diagnostic foliar symptoms include bronze spotting, purpling of veins, terminal bud blighting, and prominent concentric necrotic rings or chlorotic halo rings on ripening fruit surfaces.
3. Potyviruses (Potato Virus Y - PVY): Flexuous rod +ssRNA viruses transmitted in a non-persistent, stylet-borne manner by over 50 aphid species (including Myzus persicae). Aphids acquire virions in seconds and inoculate recipient plants immediately upon probing. Insecticide sprays are ineffective because aphids transmit the virus before dying; control relies on stylet-cleansing mineral oil sprays (0.75-1%) and certified disease-free seed tubers.
4. Potato Spindle Tuber Viroid (PSTVd): Sub-viral pathogen composed exclusively of a circular, single-stranded non-coding RNA (359 nucleotides) possessing no protein capsid. Replicated by host DNA-dependent RNA polymerase II via a rolling circle mechanism in the host nucleolus, causing spindle-shaped elongated potato tubers and foliar epinasty.
"""
    },

    "advanced_agricultural_bacteriology": {
        "title": "Advanced Agricultural Bacteriology, Vascular Cankers & Toxin Mechanisms",
        "shelf": "pathology",
        "content": """
Section 1: Fire Blight of Pome Fruits (Erwinia amylovora).
Erwinia amylovora is a Gram-negative enterobacterium causing catastrophic Fire Blight in apples (Malus domestica), pears (Pyrus communis), and Rosaceae ornamentals.
- Clinical Diagnostic Symptoms: The hallmark early symptom is blossom blight, where floral clusters turn brown and wilt. As the bacterium moves systemically down succulent shoots, the shoot tips bend sharply 180 degrees, forming the pathognomonic 'shepherd's crook' symptom. Diseased leaves and twigs turn dark brown to black and remain tenaciously attached to the tree, giving the canopy a scorched, fire-burned appearance. Under warm humid conditions (>18°C), milky white to amber droplets of bacterial ooze (millions of bacterial cells suspended in exopolysaccharide amylovoran) exude from infected lenticels and cankers.
- Mode of Action: Deploys a Type III secretion system (T3SS) delivering the harpin protein HrpN, which triggers rapid membrane depolarization and tissue necrosis.
- IPM Therapeutics: Dormant season pruning of cankers 30 cm below visible lesion borders using tools sterilized between cuts with 70% ethanol; timely bloom sprays of streptomycin sulfate (100 ppm) or oxytetracycline (200 ppm) timed precisely by the Maryblyt or Cougarblight disease forecasting models; preventive sprays of Bacillus amyloliquefaciens (strain D747) during early bloom to colonize stigmas.

Section 2: Bacterial Speck and Coronatine Toxin Biology (Pseudomonas syringae).
Pseudomonas syringae pv. tomato is a Gram-negative polar flagellated rod causing Bacterial Speck on tomato foliage and fruit.
- Clinical Diagnostic Symptoms: Tiny (1 to 2 mm), superficial, jet-black pinpoint spots surrounded by distinct bright yellow chlorotic halos on leaves. On green fruit, spots are tiny, superficial black specks (under 1 mm) slightly raised like ground black pepper, reducing fruit commercial grade.
- Biochemical Pathogenesis: Pathogen secretes coronatine (COR), a structural analog of jasmonic acid-isoleucine (JA-Ile). Coronatine binds the plant COI1-JAZ co-receptor complex, activating the jasmonic acid defense pathway, which antagonistically suppresses the plant's salicylic acid (SA) defense pathway and actively forces closed stomatal apertures to reopen, facilitating mass bacterial entry. Additionally, strains produce Ice Nucleation Active (INA) outer membrane proteins (InaZ) that catalyze ice crystal nucleation in plant tissues at temperatures as high as -1.5°C to -2°C, creating frost micro-wounds through which bacteria invade.
- IPM Therapeutics: Fixed copper bactericides (FRAC M01) mixed with mancozeb; preventive application of acibenzolar-S-methyl (ASM) to stimulate Systemic Acquired Resistance (SAR); avoid overhead sprinkler irrigation.

Section 3: Bacterial Soft Rot and Tissue Maceration (Pectobacterium & Dickeya).
Pectobacterium carotovorum (formerly Erwinia carotovora) and Dickeya dadantii are pectinolytic Gram-negative bacteria causing bacterial soft rot of potato tubers, onions, carrots, and brassicas.
- Pathogenesis: The bacteria secrete massive quantities of pectate lyases (Pel), polygalacturonases (Peh), and cellulases via the Type II secretion system. These enzymes rapidly depolymerize the middle lamella cementing adjacent plant cell walls, transforming firm, crisp plant storage organs into a foul-smelling, slimy, water-soaked liquid pulp within 24 to 48 hours.
- IPM Therapeutics: Avoid harvesting tubers during wet weather or when tuber pulp temperature exceeds 20°C; minimize mechanical bruising during grading; cure potato tubers at 10-15°C with high humidity and forced ventilation to promote wound periderm (suberin) synthesis; chlorinate wash flume water at 100-150 ppm free available chlorine (pH 6.5-7.5).

Section 4: Crown Gall and Natural Genetic Transformation (Agrobacterium tumefaciens).
Agrobacterium tumefaciens (Rhizobium radiobacter) is a soil-dwelling bacterium inducing massive woody neoplastic tumors (galls) on roots, crowns, and stems of fruit trees, grapes, and roses.
- Molecular Mechanism: Possesses a large Tumor-Inducing (Ti) plasmid. Upon sensing wound-released plant phenolics (such as acetosyringone) via the VirA/VirG two-component sensor system, virulence (Vir) proteins excise the single-stranded Transfer DNA (T-DNA) segment and translocate it into the plant cell nucleus. The T-DNA stably integrates into the host nuclear chromosomes and transcribes enzymes synthesizing auxins (indole-3-acetic acid), cytokinins (zeatin), and opines (octopine/nopaline), driving uncontrolled plant cell proliferation (gall formation) and producing opines consumed exclusively by the bacterium.
- Biological Control: Dip non-rooted cuttings and roots of nursery transplants into a suspension of antagonistic Agrobacterium radiobacter strain K84 (or genetically engineered K1026), which produces agrocin 84, a bacteriocin that selectively kills pathogenic A. tumefaciens strains.
"""
    },

    "cereal_pathogens_and_mycotoxins": {
        "title": "Staple Cereal Pathogens, Rust Lifecycles & Dangerous Mycotoxins",
        "shelf": "pathology",
        "content": """
Section 1: Stem Rust of Wheat (Puccinia graminis f. sp. tritici).
Puccinia graminis is a macrocyclic, heteroecious Basidiomycete fungus causing devastating Wheat Stem Rust.
- Five Spore Lifecycle Stages:
  1. Stage 0 (Pycnia / Spermogonia): Formed on upper leaf surface of alternate host (Common Barberry, Berberis vulgaris), releasing haploid spermatia and receptive hyphae for sexual fertilization.
  2. Stage I (Aecia): Formed on lower barberry leaf surface, discharging dikaryotic aeciospores that infect primary host cereals (wheat).
  3. Stage II (Uredinia - The Repeating Asexual Stage): Large, elongated, reddish-brown pustules (urediniospores) bursting through wheat stem and leaf sheaths. Dispersed by wind across thousands of kilometers; causes lodging and total crop failure.
  4. Stage III (Telia): As wheat matures, pustules switch to producing dark brown to black, two-celled, thick-walled overwintering teliospores on straw.
  5. Stage IV (Basidia): In spring, germinating teliospores undergo meiosis to produce 4 haploid basidiospores that reinfect young barberry leaves.
- Resistance Crisis: Lineage Ug99 (detected in Uganda in 1999) overcame the widely deployed Sr31 resistance gene, rendering 85-90% of global wheat cultivars susceptible. Breeding efforts focus on multi-gene adult plant resistance (APR) combining Sr2, Sr25, and Sr33.

Section 2: Rice Blast (Magnaporthe oryzae / Pyricularia oryzae).
Magnaporthe oryzae is an Ascomycete fungus and the most destructive disease of cultivated rice (Oryza sativa) worldwide.
- Symptoms: Spindle-shaped or diamond-shaped lesions with gray or white centers and dark brown to reddish-brown borders develop on leaves. Panicle blast or neck blast occurs when the pathogen attacks the collar of the flag leaf or panicle stem, choking nutrient flow and resulting in sterile, bleached, unfilled white panicles ('white heads').
- Biomechanics: Three-celled conidia adhere to hydrophobic waxy rice leaves via spore-tip mucilage. The germ tube differentiates a melanized domed appressorium. Melanin in the appressorial wall prevents solute leakage, allowing glycerol accumulation to reach 5 to 8 MPa of hydrostatic turgor pressure. This drives a rigid mechanical penetration peg through the silica-reinforced rice cuticle.
- IPM: Treat seeds with tricyclazole (melanin biosynthesis inhibitor MBI-D, FRAC 16.1); avoid excessive nitrogen fertilization (which thins silica cell walls); apply strobilurins (FRAC 11) or isoprothiolane (FRAC 6).

Section 3: Fusarium Head Blight (FHB) & Dangerous Mycotoxins (Fusarium graminearum).
Fusarium graminearum (teleomorph Gibberella zeae) causes Fusarium Head Blight (scab) of wheat and barley, and Gibberella ear rot of maize.
- Symptoms: Premature bleaching of individual spikelets or entire wheat heads during anthesis (flowering). Under humid conditions, a diagnostic salmon-pink to orange fungal sporulation (macroconidia) appears at the margins of glumes. Grains become shriveled, lightweight, and chalky white or pink-tinted ('tombstones').
- Deadly Agricultural Mycotoxins:
  1. Deoxynivalenol (DON / Vomitoxin): A type B trichothecene mycotoxin that binds eukaryotic 60S ribosomal subunits, inhibiting protein synthesis. Causes feed refusal, emesis (vomiting), and severe immune suppression in swine and livestock. Regulatory threshold in grain for human consumption is strictly limited by FDA/EFSA to 1.0 ppm (mg/kg).
  2. Zearalenone (ZEN): A non-steroidal estrogenic mycotoxin causing hyperestrogenism, infertility, and reproductive tract swelling in animals.
- Therapeutics: Flowering wheat heads are susceptible only during anthesis (Feekes 10.5.1); apply targeted triazole fungicides (prothioconazole, metconazole, or tebuconazole FRAC 3) precisely at early flowering; never apply strobilurin fungicides (FRAC 11) during FHB, as strobilurins induce stress-mediated upregulation of DON mycotoxin synthesis!
"""
    },

    "plant_nematology_and_complexes": {
        "title": "Plant Parasitic Nematodes, Root-Knot Galls & Disease Complexes",
        "shelf": "pathology",
        "content": """
Section 1: Root-Knot Nematodes (Meloidogyne incognita / hapla / javanica).
Root-Knot Nematodes (RKN) are microscopic, obligate endoparasitic roundworms (phylum Nematoda, family Meloidogynidae) attacking over 3,000 plant species, especially tomatoes, melons, carrots, and potatoes.
- Infection Lifecycle:
  1. Second-stage juveniles (J2) hatch from egg masses in the soil and migrate toward root elongation zones attracted by root exudates.
  2. J2 nematodes penetrate behind root tips using their hollow chitinous mouth specks (stylets) and secretion of cellulases and pectate lyases.
  3. Juveniles migrate intercellularly into the vascular cylinder, establish permanent feeding sites, and inject subventral and dorsal esophageal gland secretions into 4 to 8 vascular parenchyma cells.
  4. These cells undergo repeated rounds of nuclear division without cytokinesis (endoreduplication), forming massive, multinucleated, metabolically hyperactive 'giant cells'.
  5. The surrounding cortical cells proliferate rapidly (hyperplasia) and enlarge (hypertrophy), producing the conspicuous, swollen diagnostic root galls or knots.
- Above-Ground Clinical Symptoms: Severely stunted plant growth, chlorosis, micro-nutrient deficiencies, and severe midday wilting even in moist soil because gall formation destroys the root xylem architecture.
- Root Galling Index: Evaluated on a 0 to 5 Zeck rating scale (0 = no galls, 5 = over 75% of root system severely galled with deformed root system).

Section 2: Synergistic Nematode-Fungal Disease Complexes.
Plant parasitic nematodes rarely act alone; they frequently establish lethal synergistic disease complexes with soil-borne fungi:
- The Meloidogyne-Fusarium Wilt Complex: Physical penetration wounds created by nematode stylets serve as primary portals of entry for Fusarium oxysporum chlamydospores. More critically, physiological changes induced by giant cells suppress host phytoalexin production and alter xylem fluid chemistry, breaking genetic resistance in tomato cultivars that carry single-gene Fusarium resistance (e.g. I-gene). Plants collapse 10 times faster than when exposed to either pathogen alone.
- Black Shank Complex: Root-knot nematode infection dramatically exacerbates Phytophthora nicotianae (black shank) severity in solanaceous crops.

Section 3: Sustainable Nematode IPM & Management.
Nematode control cannot be achieved with single foliar pesticide sprays:
1. Bio-Fumigation with Brassica Cover Crops: Planting and shredding high-glucosinolate mustard crops (Brassica juncea, Sinapis alba). Incorporating fresh tissue into moist soil and immediately covering with plastic film releases volatile allyl isothiocyanates (AITC) through myrosinase enzyme breakdown, acting as a natural broad-spectrum nematicide and bio-fumigant.
2. Soil Solarization: Laying transparent polyethylene plastic sheets over moist soil for 6 to 8 weeks during peak summer sunshine elevates soil temperatures to 45°C - 55°C in top 15 cm, killing J2 nematodes and fungal resting structures.
3. Biological Bionematicides: Applying beneficial nematophagous fungi such as Purpureocillium lilacinum (formerly Paecilomyces lilacinus, strain 251), which parasitizes nematode egg masses, or Pasteuria penetrans, an obligate bacterial parasite whose endospores adhere to and kill migrating J2 juveniles.
"""
    },

    "abiotic_disorders_differential_diagnosis": {
        "title": "Abiotic Disorders, Nutritional Deficiencies & Differential Diagnosis",
        "shelf": "pathology",
        "content": """
Section 1: The Critical Necessity of Differential Diagnosis.
A critical vulnerability in clinical agriculture is the frequent misdiagnosis of abiotic (non-infectious) physiological disorders as fungal or bacterial plant diseases. Applying fungicides, bactericides, or systemic chemicals to abiotic environmental disorders wastes economic resources, contaminates ecosystems, and fails to remedy the underlying physiological stress.

Section 2: Blossom End Rot (BER) of Tomato and Pepper - NOT A FUNGUS!
- Clinical Presentation: Initiates as a water-soaked, light tan sunken spot directly at the blossom end (distal fruit tip opposite the stem calyx) of rapidly developing green tomatoes, peppers, and eggplants. The lesion rapidly enlarges, darkens, and flattens into a distinct, circular, dry, leathery, sunken black or dark brown plate.
- The Diagnostic Pitfall: Secondary opportunistic saprophytic fungi (such as Alternaria or black molds) often colonize the dead leathery tissue, causing growers to mistakenly identify BER as 'early blight' or 'fruit rot' and spray copper or chlorothalonil.
- True Physiological Cause: Blossom End Rot is caused exclusively by a localized Calcium (Ca2+) deficiency within the rapidly expanding distal fruit pericarp cells. Calcium is an immobile structural element bound in cell wall middle lamellae as calcium pectate. Because calcium is transported exclusively through xylem transpiration flow driven by water loss from leaves, leafy canopies transpire far more water than fruit. When soil moisture fluctuates (e.g. drought stress followed by heavy deluge, or irregular watering cycles), calcium fails to reach the distal fruit tip, causing cell wall collapse and dry necrosis.
- Correct Clinical Remedy: DO NOT APPLY FUNGICIDES. Maintain uniform, consistent soil moisture through automated drip irrigation; apply organic mulch (5-10 cm straw or wood chips) to prevent rapid soil drying; avoid excessive ammonium-nitrogen (NH4+) fertilizer, which directly competes with Ca2+ ions for root uptake; verify soil pH is maintained between 6.2 and 6.8.

Section 3: Herbicide Drift vs. Viral Infections.
Synthetic auxin growth-regulator herbicides (notably 2,4-D, dicamba, and triclopyr) applied to nearby turfgrass or grain fields easily volatilize and drift on wind currents over miles:
- Diagnostic Symptoms: Susceptible crops (especially tomatoes and grapes) exhibit dramatic downward epinasty, twisting of petioles, strap-like leaf narrowing, thickening of leaf veins, and parallel venation resembling a folded fan or duck foot.
- Differential Diagnosis: Often misdiagnosed as Tomato Mosaic Virus (TMV) or Tomato Yellow Leaf Curl Virus. Differential rule: Herbicide drift symptoms appear suddenly across an entire greenhouse or field within 24-48 hours after wind/lawn spraying, with all plants of a similar age affected simultaneously; viral infections start on isolated plants and spread progressively via vectors or mechanical pruning lines over weeks.

Section 4: Macro- and Micronutrient Chlorosis Differential Matrix.
- Iron (Fe) Deficiency Chlorosis: Characterized by brilliant, sharp interveinal chlorosis (leaf veins remain dark green while interveinal areas turn pale yellow to white) strictly on the YOUNGEST, uppermost terminal foliage. Caused by high soil pH (>7.5) rendering iron insoluble. Corrected with chelated iron (Fe-EDDHA).
- Nitrogen (N) Deficiency: General, uniform, pale yellow-green chlorosis initiating on the OLDEST, lowermost senescence foliage first, as the plant mobilizes mobile nitrogen to support young growing tips. Corrected with nitrogen fertilizer.
- Magnesium (Mg) Deficiency: Interveinal chlorosis with reddish-purple margins occurring primarily on LOWER mature leaves (because Mg is mobile in phloem). Corrected with magnesium sulfate (Epsom salts).

Section 5: Sunscald, Catfacing, and Physiological Edema.
- Sunscald: Bleached, white, papery, sunken blisters on shoulders of green fruit directly exposed to intense sunlight following sudden defoliation (e.g. after pruning or black spot leaf drop). Not infectious.
- Catfacing: Severe malformation, puckering, scarring, and deep cavity bands at the blossom end of heirloom tomatoes. Caused by cold ambient temperatures (<12°C / 54°F) during flower bud differentiation, disrupting pistil carpel fusion.
- Physiological Edema (Oedema): Blister-like, water-soaked, corky bumps on lower leaf surfaces and petioles. Occurs in greenhouse plants when warm, wet soil drives root water uptake while cool, humid, overcast air halts foliar transpiration, bursting leaf mesophyll cells.
"""
    },

    "clinical_laboratory_diagnostic_protocols": {
        "title": "Clinical Laboratory Diagnostic Protocols, Assay Directory & PCR Primers",
        "shelf": "pathology",
        "content": """
Section 1: Rapid In-Field Clinical Diagnostic Tests.
Before running expensive molecular assays, clinical plant pathologists perform standardized field tests:
1. The 10-Second 3% KOH String Test (Gram Status Differentiation):
   - Principle: Distinguishes Gram-negative from Gram-positive phytopathogenic bacteria without microscopic Gram staining.
   - Protocol: Place one drop of 3% aqueous potassium hydroxide (KOH) on a clean microscope slide. Using a sterile toothpick or loop, transfer a heavy mass of pure bacterial colony from agar into the drop. Vigorously emulsify for 10 to 15 seconds, then slowly raise the loop 1 to 2 cm above the slide.
   - Interpretation: If the liquid becomes viscous and forms a persistent mucoid slime thread (stringing 5 to 20 mm high), the bacterium is Gram-Negative (cell walls lyse instantly, releasing high-molecular-weight chromosomal DNA; e.g. Xanthomonas, Ralstonia, Erwinia, Pseudomonas, Agrobacterium). If the mixture remains watery with no stringing, it is Gram-Positive (rigid peptidoglycan wall resists lysis; e.g. Clavibacter michiganensis).
2. The Vascular Stem Streaming Assay:
   - Protocol: Slice a 2 to 3 cm section of suspect wilted stem (e.g. tomato with suspected bacterial wilt). Suspend the cut end vertically in a clear beaker or test tube filled with still, room-temperature water against a dark background without agitating.
   - Interpretation: Within 1 to 3 minutes, distinct milky white threads of bacterial slime and cells streaming downward from the vascular xylem bundles confirms bacterial vascular wilt (Ralstonia solanacearum). If no streaming occurs within 5 minutes, vascular wilt is caused by fungal pathogens (Fusarium oxysporum or Verticillium dahliae).

Section 2: ImmunoStrip & Lateral Flow Diagnostic Strips.
- Lateral Flow Immunoassay (LFIA): Agdia ImmunoStrip test kits provide 5-minute on-site clinical verification for high-threat viral and oomycete pathogens (ToBRFV, Phytophthora, CMV, INSV, TSWV).
- Protocol: Place a 0.15 g sample of symptomatic leaf tissue into an extraction buffer pouch. Macerate thoroughly with a mesh roller. Insert the ImmunoStrip strip vertically into the liquid up to the sample line.
- Reading: Capillary action draws antigen through colloidal-gold-labeled monoclonal antibodies. The appearance of two red lines (Test Line + Control Line) confirms a POSITIVE diagnosis. A single Control Line confirms a negative test.

Section 3: Authoritative Molecular PCR Primers & DNA Barcoding.
When species-level identification requires genetic sequence confirmation, standard validated PCR primers are utilized:
1. Universal Fungal DNA Barcode (Ribosomal Internal Transcribed Spacer):
   - Forward Primer (ITS1): 5'-TCCGTAGGTGAACCTGCGG-3'
   - Reverse Primer (ITS4): 5'-TCCTCCGCTTATTGATATGC-3'
   - Target: ITS1-5.8S-ITS2 nuclear ribosomal cistron (~550-650 bp amplicon). Validated for Alternaria, Fusarium, Botrytis, Venturia, Diplocarpon.
2. Universal Bacterial 16S Ribosomal DNA Barcode:
   - Forward Primer (27F): 5'-AGAGTTTGATCMTGGCTCAG-3'
   - Reverse Primer (1492R): 5'-GGTTACCTTGTTACGACTT-3'
   - Target: Near full-length 16S rRNA gene (~1,465 bp amplicon). Validated for Xanthomonas, Pseudomonas, Erwinia, Ralstonia, Agrobacterium.
3. Oomycete-Specific Mitochondrial Cytochrome c Oxidase:
   - Primers: CoxI and CoxII forward/reverse primers amplify the mitochondrial locus, discriminating Phytophthora infestans from Pythium and fungal lookalikes.
4. ToBRFV Real-Time RT-qPCR Specific Primer Pair:
   - Targets the RNA-dependent RNA polymerase (RdRp) or coat protein (CP) gene of Tomato Brown Rugose Fruit Virus, discriminating ToBRFV from TMV and ToMV.

Section 4: Semi-Selective Culture Media Formulations.
1. King's B Medium (KB): For isolating and confirming fluorescent Pseudomonas species. Contains proteose peptone, glycerol, K2HPO4, and MgSO4.7H2O. Under 365 nm UV ultraviolet light, colonies produce a brilliant blue-green or yellow-green fluorescent siderophore pigment (pyoverdine).
2. PARP / PARPH Selective Agar: Specific isolation of Oomycetes (Phytophthora and Pythium) from soil and plant roots. Formulated with cornmeal agar amended with selective antibiotics: Pimaricin (antifungal), Ampicillin (antibacterial), Rifampicin (antibacterial), and PCNB (pentachloronitrobenzene, suppresses true fungi), plus Hymexazol (H) to inhibit Pythium when isolating Phytophthora.
3. Komada's Selective Medium: Formulated with D-galactose, L-asparagine, bile salts, PCNB, and sodium tetraborate for the specific diagnostic enumeration of Fusarium oxysporum from soil and vascular xylem.
"""
    },

    "frac_phytopharmacology_directory": {
        "title": "Comprehensive FRAC Fungicide Directory, Modes of Action & Resistance Management",
        "shelf": "pathology",
        "content": """
Section 1: Principles of Fungicide Resistance Management.
The Fungicide Resistance Action Committee (FRAC) classifies chemical and biological active ingredients by their target biochemical site of action. Repeated application of single-site fungicides (e.g. FRAC 11 QoIs or FRAC 3 DMIs) exerts intense selective pressure, driving selection of resistant mutant subpopulations. To prevent resistance development:
1. Tank-mix or alternate single-site systemic fungicides with multi-site contact protectants (FRAC Group M).
2. Never exceed 2 sequential applications of a single FRAC group before rotating to an unrelated target site.
3. Strictly adhere to label Pre-Harvest Intervals (PHI) and Maximum Residue Limits (MRL).

Section 2: The Comprehensive FRAC Code Classification:
1. FRAC Group M (Multi-Site Contact Protectants - Low Resistance Risk):
   - FRAC M01 (Inorganic Copper: copper octanoate, copper sulfate, copper hydroxide): Non-specific binding to fungal protein thiol groups. Bactericidal against Xanthomonas and Pseudomonas.
   - FRAC M02 (Inorganic Elemental Sulfur: micronized wettable sulfur): Multi-site disruptor of mitochondrial respiratory electron transport. Highly active on Powdery Mildew (Podosphaera) and mites. Phytotoxic above 30°C.
   - FRAC M03 (Dithiocarbamates: Mancozeb, Maneb): Inactivates sulfhydryl groups in enzymes. Excellent protectant tank-mix partner.
   - FRAC M04 (Phthalimides: Captan, Folpet): Thiol-reacting enzyme inhibitor. Core apple scab protectant.
2. FRAC Group 7 (SDHI - Succinate Dehydrogenase Inhibitors):
   - Active Ingredients: Boscalid, fluxapyroxad, fluopyram, penthiopyrad.
   - Biochemical Target: Complex II (succinate dehydrogenase) in the mitochondrial respiration chain. High-potency translaminar activity against Botrytis, Alternaria, and powdery mildews. Moderate to high resistance risk.
3. FRAC Group 3 (DMI - Demethylation Inhibitors / Triazoles):
   - Active Ingredients: Difenoconazole, myclobutanil, propiconazole, tebuconazole, prothioconazole.
   - Biochemical Target: Sterol 14alpha-demethylase (encoded by CYP51), inhibiting ergosterol biosynthesis in true fungal membranes. Systemic curative and preventative activity. Resistance mechanism is multi-step (CYP51 overexpression or point mutations).
4. FRAC Group 11 (QoI - Quinone Outside Inhibitors / Strobilurins):
   - Active Ingredients: Azoxystrobin, pyraclostrobin, trifloxystrobin.
   - Biochemical Target: Cytochrome b Qo site (Complex III) in mitochondrial respiration. High resistance risk driven by a single qualitative point mutation (G143A amino acid substitution). Never spray during Fusarium Head Blight (triggers DON toxin surge).
5. FRAC Group 40 (CAA - Carboxylic Acid Amides):
   - Active Ingredients: Mandipropamid, dimethomorph.
   - Biochemical Target: Cellulose synthase (CesA3) in Oomycetes. Ineffective on true fungi; highly specific for Phytophthora and Downy Mildew.
6. FRAC Group 44 (Microbial Biological Lipopeptides):
   - Active Ingredients: Bacillus amyloliquefaciens (strain D747), Bacillus subtilis (strain QST 713).
   - Biochemical Mode of Action: Synthesize cyclic lipopeptides (surfactins, iturins, and fengycins) that insert into fungal membranes and form pore channels, causing osmotic burst. Zero chemical residues, 0-day PHI, OMRI-listed organic.
7. FRAC Group P / P01 (Host Plant Defense Inducers):
   - Active Ingredients: Salicylic acid, acibenzolar-S-methyl (ASM), laminarin, potassium silicate.
   - Biochemical Mode of Action: Primes plant innate Systemic Acquired Resistance (SAR) without direct antimicrobial activity.
"""
    }
}

def build_advanced_curriculum():
    print("\n========================================================")
    print("  [PLANT PATHOLOGY] 6-DIVISION ADVANCED CURRICULUM")
    print("========================================================")

    pipeline = LiteratureIngestionPipeline()
    books_dir = os.path.join(pipeline.book_engine.data_dir, "pathology")
    os.makedirs(books_dir, exist_ok=True)

    total_chunks = 0
    total_words = 0

    for file_key, meta in ADVANCED_CURRICULUM_TEXTS.items():
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
    print(f"Total Advanced Curriculum: {total_chunks} chunks, {total_words} words indexed.")
    print("All BM25 indexes updated.\n")

if __name__ == "__main__":
    build_advanced_curriculum()
