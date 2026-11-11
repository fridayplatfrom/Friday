"""Legacy plant-pathology examples and a reusable supervised training entry point.

The 165 hand-authored queries are unreviewed demonstration fixtures. Running
without --data trains only an experimental bundle; it does not certify accuracy.
Books must be converted into reviewed labeled JSONL before supervised training.
"""

from pathlib import Path

TRAINING_DATA = [
    # ====================================================
    # DIVISION 1: FUNGI & OOMYCETES
    # ====================================================
    {
        "queries": [
            "My tomato plant has dark brown concentric target rings on lower leaves with yellow halos. Is this early blight or late blight?",
            "Lower potato leaves show concentric bullseye lesions with dark brown margins and chlorotic yellow halos.",
            "Alternaria solani infection on tomato foliage showing concentric target board rings.",
            "Eggplant foliage showing dark brown target rings surrounded by yellow chlorosis on oldest leaves.",
            "Dark brown zoned concentric spots on lower tomato leaves following alternating wet and dry days.",
            "Early blight Alternaria solani necrotrophic alternariol toxin on solanaceous foliage."
        ],
        "disease": "Early Blight",
        "pathogen": "Alternaria solani",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "FRAC_M01_Copper_Protectant"
    },
    {
        "queries": [
            "Tomato foliage shows large water-soaked olive lesions with white fuzzy sporulation on leaf undersides after heavy rain. What pathogen is this?",
            "Potato leaves rapidly turning black and rotting with white fuzzy mold on leaf underside during cool wet weather.",
            "Phytophthora infestans late blight outbreak destroying tomato field after rainy week.",
            "Oomycete infection causing rapid foliar collapse and white cottony growth underneath leaves.",
            "Severe potato blight with granular brown tuber rot and white fuzzy zoosporangia on leaves.",
            "Late blight Phytophthora infestans biflagellate zoospore infection on Solanaceae."
        ],
        "disease": "Late Blight",
        "pathogen": "Phytophthora infestans",
        "kingdom": "Oomycete",
        "assay": "PARP_Selective_Media",
        "strategy": "FRAC_40_CAA_Oomycete_Specific"
    },
    {
        "queries": [
            "Squash leaves have white talcum-powder patches across the upper leaf surface in dry warm weather. What is the diagnosis?",
            "White powdery talcum-like spots coating cucumber and zucchini foliage in warm dry weather.",
            "Podosphaera xanthii powdery mildew superficial mycelium on cucurbit leaves.",
            "Superficial white powdery fungal epiphytic growth on upper adaxial squash leaf surface.",
            "How to treat white powdery spots on squash foliage using potassium bicarbonate?"
        ],
        "disease": "Powdery Mildew",
        "pathogen": "Podosphaera xanthii",
        "kingdom": "Fungus",
        "assay": "General_Symptom_Triangulation",
        "strategy": "Potassium_Bicarbonate_Shock"
    },
    {
        "queries": [
            "Cucumber leaves show angular yellow patches strictly bounded by leaf veins with purplish-grey spore fuzz on the bottom. What disease is this?",
            "Pseudoperonospora cubensis downy mildew on cucumber with angular mosaic yellow lesions.",
            "Angular yellow patches restricted by leaf veins with purplish-grey or brown felt on leaf undersides.",
            "Cucurbit downy mildew oomycete causing geometric yellow leaf mosaic pattern.",
            "Purplish-grey fuzzy sporulation under angular vein-bounded yellow cucumber leaf spots."
        ],
        "disease": "Downy Mildew",
        "pathogen": "Pseudoperonospora cubensis",
        "kingdom": "Oomycete",
        "assay": "PARP_Selective_Media",
        "strategy": "FRAC_40_CAA_Oomycete_Specific"
    },
    {
        "queries": [
            "One side of my tomato branch is severely wilting and cutting the lower stem reveals a dark brown ring in the vascular xylem bundle.",
            "Fusarium oxysporum vascular wilt showing unilateral yellowing and brown xylem discoloration.",
            "Yellow flag symptom where one side of tomato branch turns yellow and wilts.",
            "Tomato plant wilting during midday with chocolate brown staining inside stem xylem vessels.",
            "Soil-borne Fusarium vascular wilt plugging xylem with chlamydospores and fusaric acid."
        ],
        "disease": "Fusarium Wilt",
        "pathogen": "Fusarium oxysporum",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "Biofumigation_Soil_Solarization"
    },
    {
        "queries": [
            "Ripening strawberries are rotting with a dense fuzzy velvety grey spore blanket covering the soft collapsed fruit.",
            "Botrytis cinerea grey mold covering ripening strawberry fruit with powdery grey conidia.",
            "Soft watery fruit decay with dense velvety mouse-grey mold on strawberries and grapes.",
            "Velvety grey spore blanket on soft rotting strawberry fruit under cool damp conditions.",
            "Botrytis necrotrophic infection secreting pectinases and botrydial toxin on fruit."
        ],
        "disease": "Grey Mold",
        "pathogen": "Botrytis cinerea",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "Biofungicide_Bacillus_Lipopeptides"
    },
    {
        "queries": [
            "Rose bush leaves develop distinct circular black spots with fringed feathery margins followed by extensive leaf yellowing and defoliation.",
            "Diplocarpon rosae black spot on rose bushes causing yellow leaves and defoliation.",
            "Circular jet-black spots with feathery fibrillose margins on upper rose leaf surfaces.",
            "Rose leaves turning yellow around dark black spots with fringed borders and dropping."
        ],
        "disease": "Black Spot",
        "pathogen": "Diplocarpon rosae",
        "kingdom": "Fungus",
        "assay": "General_Symptom_Triangulation",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Apple tree leaves and young developing fruit show olive-green velvety spots that turn corky, dark brown, and scabby.",
            "Venturia inaequalis apple scab infection on foliage and developing apples.",
            "Olive-green velvety spots becoming raised, dark brown, and corky scabs on apple fruit.",
            "Apple fruit cracking and deformed with dark rough scabby lesions from Venturia."
        ],
        "disease": "Apple Scab",
        "pathogen": "Venturia inaequalis",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "FRAC_M02_Sulfur_Protectant"
    },
    {
        "queries": [
            "Wheat stems show elongated reddish-brown rust pustules bursting through leaf sheaths causing lodging.",
            "Puccinia graminis stem rust of wheat with alternating barberry host lifecycle.",
            "Urediniospores of wheat stem rust bursting through stem tissue in cereal crops.",
            "Ug99 virulent wheat stem rust lineage breaking Sr31 resistance gene."
        ],
        "disease": "Wheat Stem Rust",
        "pathogen": "Puccinia graminis",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "FRAC_03_DMI_Sterol_Inhibitor"
    },
    {
        "queries": [
            "Rice leaves exhibit spindle-shaped diamond lesions with gray centers and dark brown margins, with bleached white panicles.",
            "Magnaporthe oryzae rice blast causing neck blast and white head sterility in paddy fields.",
            "Appressorial turgor pressure penetration peg of rice blast fungus.",
            "Spindle-shaped diamond eye lesions on rice foliage caused by Pyricularia oryzae."
        ],
        "disease": "Rice Blast",
        "pathogen": "Magnaporthe oryzae",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "FRAC_07_SDHI_Respiration_Blocker"
    },
    {
        "queries": [
            "Wheat flowering heads have prematurely bleached spikelets with salmon-pink orange mold and shriveled grains.",
            "Fusarium graminearum head blight producing deoxynivalenol DON vomitoxin mycotoxins in wheat.",
            "Salmon-pink sporulation on bleached wheat glumes producing dangerous trichothecene vomitoxin.",
            "Fusarium head blight scab on barley with tombstone chalky kernels."
        ],
        "disease": "Fusarium Head Blight",
        "pathogen": "Fusarium graminearum",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "FRAC_03_DMI_Sterol_Inhibitor"
    },

    # ====================================================
    # DIVISION 2: ADVANCED AGRICULTURAL BACTERIOLOGY
    # ====================================================
    {
        "queries": [
            "Pepper leaves exhibit small water-soaked greasy spots that turn black with a pronounced yellow halo during hot humid thunderstorms.",
            "Bacterial spot caused by Xanthomonas campestris on bell pepper foliage and fruit.",
            "Small greasy water-soaked lesions turning dark brown with distinct yellow halos on pepper.",
            "Xanthomonas bacterial leaf spot on tomato leaves following heavy thunderstorm splash."
        ],
        "disease": "Bacterial Spot",
        "pathogen": "Xanthomonas campestris",
        "kingdom": "Bacterium",
        "assay": "KOH_String_Test_3Percent",
        "strategy": "FRAC_M01_Copper_Protectant"
    },
    {
        "queries": [
            "Tomato plant suddenly wilts during daytime while stems remain completely green without yellowing.",
            "Ralstonia solanacearum bacterial wilt showing milky white streaming threads from cut stem in water.",
            "Rapid collapse and green wilting of tomato foliage with positive bacterial streaming test.",
            "Suspending cut tomato stem in water reveals milky bacterial streaming from xylem vessels."
        ],
        "disease": "Bacterial Wilt",
        "pathogen": "Ralstonia solanacearum",
        "kingdom": "Bacterium",
        "assay": "Vascular_Stem_Streaming_Assay",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Apple and pear branch tips are hooked 180 degrees like a shepherd's crook with black scorched leaves and milky bacterial ooze.",
            "Erwinia amylovora fire blight causing blackened scorched twigs and shepherd's crook shoot bending.",
            "Milky amber bacterial ooze droplet exuding from blighted apple blossoms and cankers.",
            "Fire blight bacterial canker in pear orchard managed with streptomycin at bloom."
        ],
        "disease": "Fire Blight",
        "pathogen": "Erwinia amylovora",
        "kingdom": "Bacterium",
        "assay": "PCR_16S_Bacterial_Sequencing",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Tiny pinpoint black specks with yellow halos on tomato leaves and raised black ground-pepper specks on green fruit.",
            "Pseudomonas syringae bacterial speck secreting coronatine toxin and ice nucleation active proteins.",
            "Coronatine toxin reopening stomata and tiny black specks on tomato foliage.",
            "Bacterial speck Pseudomonas syringae pv tomato management with copper."
        ],
        "disease": "Bacterial Speck",
        "pathogen": "Pseudomonas syringae",
        "kingdom": "Bacterium",
        "assay": "Kings_B_UV_Fluorescence",
        "strategy": "FRAC_M01_Copper_Protectant"
    },
    {
        "queries": [
            "Harvested potato tubers and cabbage heads turning into a foul-smelling, water-soaked, slimy liquid mush.",
            "Pectobacterium carotovorum bacterial soft rot liquefying vegetable storage tissues with pectate lyases.",
            "Soft slimy watery rot of carrot and potato storage organs with macerated middle lamella.",
            "Bacterial soft rot in postharvest potato storage caused by Dickeya and Pectobacterium."
        ],
        "disease": "Bacterial Soft Rot",
        "pathogen": "Pectobacterium carotovorum",
        "kingdom": "Bacterium",
        "assay": "KOH_String_Test_3Percent",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Woody rough swollen tumors and galls forming at the soil crown and root junctions of rose and fruit trees.",
            "Agrobacterium tumefaciens crown gall transferring Ti plasmid T-DNA into plant chromosomes.",
            "Uncontrolled tumor cell proliferation and opine synthesis induced by crown gall bacterium.",
            "Swollen woody galls on grapevine and apple rootstock caused by Agrobacterium."
        ],
        "disease": "Crown Gall",
        "pathogen": "Agrobacterium tumefaciens",
        "kingdom": "Bacterium",
        "assay": "PCR_16S_Bacterial_Sequencing",
        "strategy": "Biofumigation_Soil_Solarization"
    },

    # ====================================================
    # DIVISION 3: PLANT VIROLOGY & VECTORS
    # ====================================================
    {
        "queries": [
            "Tomato fruits develop brown rugose wrinkled patches, yellow marbling, and leaves show narrow mosaic fern-leaf bubbling.",
            "Tomato Brown Rugose Fruit Virus ToBRFV breaking Tm-2^2 resistance in commercial greenhouse tomatoes.",
            "Mechanically transmitted Tobamovirus causing brown necrotic rugose wrinkling on ripening tomato fruit.",
            "ToBRFV seed-borne virus surviving on greenhouse tools and trellising wires."
        ],
        "disease": "Tomato Brown Rugose Fruit Virus",
        "pathogen": "Tomato Brown Rugose Fruit Virus (ToBRFV)",
        "kingdom": "Virus",
        "assay": "Lateral_Flow_ImmunoStrip",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Tomato and tobacco leaves show light and dark green mosaic mottling, distorted blistering, and stunted shoe-string leaves.",
            "Tobacco mosaic virus TMV rod-shaped virion transmitted mechanically on workers hands and tools.",
            "Mosaic pattern on tomato foliage with leaf distortion caused by Tobamovirus TMV.",
            "Disinfecting tools with non-fat dry milk to inactivate Tobacco Mosaic Virus."
        ],
        "disease": "Tobacco Mosaic Virus",
        "pathogen": "Tobacco Mosaic Virus (TMV)",
        "kingdom": "Virus",
        "assay": "Lateral_Flow_ImmunoStrip",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Tomato plants are severely stunted and bushy with leaves curled tightly upward and yellow margins; clouds of whiteflies present.",
            "Tomato Yellow Leaf Curl Virus TYLCV transmitted by silverleaf whitefly Bemisia tabaci.",
            "Upward leaf cupping and flower drop in tomato caused by Begomovirus whitefly vector.",
            "Managing TYLCV through 50-mesh insect exclusion netting and whitefly control."
        ],
        "disease": "Tomato Yellow Leaf Curl Virus",
        "pathogen": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "kingdom": "Virus",
        "assay": "RT_qPCR_Viral_Amplification",
        "strategy": "Vector_Control_Thrips_Whitefly"
    },
    {
        "queries": [
            "Tomato foliage displays bronze spotting, terminal stem blighting, and ripening fruit has concentric yellow and necrotic ring spots.",
            "Tomato Spotted Wilt Virus TSWV transmitted by Western flower thrips Frankliniella occidentalis.",
            "Tospovirus causing bronze foliar lesions and necrotic rings on tomato fruit surfaces.",
            "Thrips vector transmission of Tomato Spotted Wilt Virus and weed reservoir hosts."
        ],
        "disease": "Tomato Spotted Wilt Virus",
        "pathogen": "Tomato Spotted Wilt Virus (TSWV)",
        "kingdom": "Virus",
        "assay": "Lateral_Flow_ImmunoStrip",
        "strategy": "Vector_Control_Thrips_Whitefly"
    },
    {
        "queries": [
            "Potato tubers are abnormally elongated, cylindrical, spindle-shaped with cracked skin, and foliage has upright epinasty.",
            "Potato spindle tuber viroid PSTVd circular single-stranded non-coding RNA pathogen.",
            "Sub-viral viroid lacking a protein capsid replicating via host RNA polymerase II.",
            "Spindle tuber disease of potato caused by PSTVd viroid."
        ],
        "disease": "Potato Spindle Tuber Viroid",
        "pathogen": "Potato Spindle Tuber Viroid (PSTVd)",
        "kingdom": "Viroid",
        "assay": "RT_qPCR_Viral_Amplification",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },

    # ====================================================
    # DIVISION 4: NEMATOLOGY & SOIL DISEASE COMPLEXES
    # ====================================================
    {
        "queries": [
            "Tomato plants are stunted and wilting at midday; digging up roots reveals numerous swollen bumpy knots and galls.",
            "Meloidogyne incognita root-knot nematode causing multinucleated giant cells and heavy root galling.",
            "Root galls and knots on tomato root system with midday wilt and nutrient stunting.",
            "Microscopic J2 juvenile nematodes penetrating root tips and forming giant feeding cells."
        ],
        "disease": "Root Knot Nematode",
        "pathogen": "Meloidogyne incognita",
        "kingdom": "Nematode",
        "assay": "Microscopic_Root_Gall_Index",
        "strategy": "Biofumigation_Soil_Solarization"
    },
    {
        "queries": [
            "Tomato plants collapse rapidly with severe root galls and brown vascular xylem ring, breaking Fusarium resistance genes.",
            "Synergistic disease complex between Meloidogyne root-knot nematodes and Fusarium oxysporum wilt.",
            "Nematode feeding wounds facilitating fungal vascular entry and breaking single-gene host resistance.",
            "Meloidogyne-Fusarium wilt complex collapsing crops 10 times faster than either alone."
        ],
        "disease": "Nematode Fusarium Wilt Complex",
        "pathogen": "Meloidogyne Fusarium Synergistic Complex",
        "kingdom": "Nematode",
        "assay": "Microscopic_Root_Gall_Index",
        "strategy": "Biofumigation_Soil_Solarization"
    },

    # ====================================================
    # DIVISION 5: ABIOTIC LOOKALIKES & DIFFERENTIAL DIAGNOSIS
    # ====================================================
    {
        "queries": [
            "Tomatoes have dark, sunken, circular leathery black rot on the bottom of green fruits opposite the stem. What fungus is this?",
            "Blossom end rot on tomatoes and peppers caused by localized calcium deficiency during dry spells, not a fungus.",
            "Bottom of green pepper fruit turning flat, sunken, dry and black leathery.",
            "Is blossom end rot caused by a pathogen and should I spray copper or fungicide?",
            "Sunken leathery black spot on tomato blossom end caused by irregular watering and calcium transport deficit."
        ],
        "disease": "Blossom End Rot",
        "pathogen": "Abiotic Calcium Transport Deficiency",
        "kingdom": "Abiotic / Physiological Stress",
        "assay": "Soil_Moisture_And_Tissue_Ca_Assay",
        "strategy": "Calcium_Moisture_Stabilization"
    },
    {
        "queries": [
            "Tomato leaves are suddenly twisting, cupping upward, narrowing like straps, and veins resemble a fan after neighbors sprayed lawn.",
            "Synthetic auxin herbicide drift 2,4-D or dicamba causing severe petiole epinasty and fan-shaped leaves.",
            "Herbicide drift injury mimicking viral mosaic symptoms across whole greenhouse simultaneously.",
            "Strap-like leaf narrowing and downward twisting caused by volatilized 2,4-D herbicide drift."
        ],
        "disease": "Herbicide Drift Injury",
        "pathogen": "Synthetic Auxin Herbicide 2,4-D Drift",
        "kingdom": "Abiotic / Physiological Stress",
        "assay": "General_Symptom_Triangulation",
        "strategy": "Herbicide_Decontamination_Buffer"
    },
    {
        "queries": [
            "Youngest uppermost tomato leaves show bright sharp interveinal yellowing while veins stay dark green in high pH soil.",
            "Iron deficiency interveinal chlorosis on youngest terminal foliage in alkaline soil.",
            "Iron chlorosis with green veins and bleached yellow leaf blades on new upper growth.",
            "Correcting high pH iron deficiency using chelated Fe-EDDHA."
        ],
        "disease": "Iron Deficiency Chlorosis",
        "pathogen": "Alkaline Soil Insoluble Iron Deficiency",
        "kingdom": "Abiotic / Physiological Stress",
        "assay": "Soil_Moisture_And_Tissue_Ca_Assay",
        "strategy": "Calcium_Moisture_Stabilization"
    },
    {
        "queries": [
            "Oldest lowest leaves of tomato plants turn uniformly pale yellow and drop while upper foliage remains green.",
            "Nitrogen deficiency causing general uniform chlorosis on oldest bottom leaves first.",
            "Nitrogen mobile nutrient translocation from old leaves to new growth causing lower yellowing.",
            "Distinguishing uniform nitrogen yellowing on lower leaves from fungal leaf spots."
        ],
        "disease": "Nitrogen Deficiency",
        "pathogen": "Soil Available Nitrogen Depletion",
        "kingdom": "Abiotic / Physiological Stress",
        "assay": "Soil_Moisture_And_Tissue_Ca_Assay",
        "strategy": "Calcium_Moisture_Stabilization"
    },
    {
        "queries": [
            "Green tomato fruit develops bleached white, papery, sunken blisters on shoulders exposed to direct intense sun.",
            "Sunscald injury on green tomatoes following sudden defoliation and solar thermal shock.",
            "Bleached papery blisters on sun-exposed fruit surfaces without pathogen sporulation.",
            "Preventing sunscald through canopy shading and controlling defoliating diseases."
        ],
        "disease": "Sunscald Injury",
        "pathogen": "Solar Radiation Thermal Shock",
        "kingdom": "Abiotic / Physiological Stress",
        "assay": "General_Symptom_Triangulation",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Heirloom tomato fruits are severely scarred, malformed, puckered with deep cavity bands at blossom end.",
            "Catfacing fruit malformation caused by cold night temperatures during flower bud differentiation.",
            "Cold temperature shock during blossom stage causing puckered scarred tomato fruit catfacing.",
            "Distinguishing catfacing cold damage from fungal fruit rot."
        ],
        "disease": "Catfacing Malformation",
        "pathogen": "Cold Temperature Flower Bud Shock",
        "kingdom": "Abiotic / Physiological Stress",
        "assay": "General_Symptom_Triangulation",
        "strategy": "Calcium_Moisture_Stabilization"
    },

    # ====================================================
    # DIVISION 6: CLINICAL LAB ASSAYS & SAR
    # ====================================================
    {
        "queries": [
            "How to perform the rapid 3% KOH string test on a microscope slide to determine if bacteria is Gram negative?",
            "3% KOH string test protocol emulsifying colony to see viscous mucoid DNA strand formation.",
            "Differentiating Gram-negative Xanthomonas and Ralstonia from Gram-positive using 3% potassium hydroxide.",
            "Ten second KOH string test interpretation for plant pathogenic bacteria."
        ],
        "disease": "Clinical Laboratory Diagnostic Protocol",
        "pathogen": "Diagnostic Assay Protocol",
        "kingdom": "Bacterium",
        "assay": "KOH_String_Test_3Percent",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "How does salicylic acid signaling induce systemic acquired resistance and PR pathogenesis-related proteins in plants?",
            "Systemic acquired resistance SAR activation via salicylic acid and NPR1 transcription factor.",
            "Plant innate immunity hypersensitive response oxidative burst and PR protein synthesis.",
            "PR-1 biomarker and beta-1,3-glucanase chitinase induction during systemic acquired resistance."
        ],
        "disease": "Systemic Acquired Resistance",
        "pathogen": "Host Plant Innate Immune System",
        "kingdom": "Host Immune Response",
        "assay": "RT_qPCR_Viral_Amplification",
        "strategy": "Systemic_Acquired_Resistance_Elicitation"
    },

    # ====================================================
    # DIVISION 7: INDIAN AGRICULTURAL & TROPICAL STAPLE CROPS (ICAR / TNAU)
    # ====================================================
    {
        "queries": [
            "Rice seedlings roll inward, wilt, and die during early transplanting kresek phase with milky ooze.",
            "Paddy leaves show wavy translucent yellow margins turning straw-yellow and bleached white with amber bacterial beads.",
            "Xanthomonas oryzae pv oryzae bacterial leaf blight on rice in delta regions.",
            "Managing bacterial leaf blight using streptocycline, copper hydroxide, and Improved Samba Mahsuri."
        ],
        "disease": "Rice Bacterial Leaf Blight",
        "pathogen": "Xanthomonas oryzae pv. oryzae",
        "kingdom": "Bacterium",
        "assay": "Vascular_Stem_Streaming_Assay",
        "strategy": "FRAC_M01_Copper_Protectant"
    },
    {
        "queries": [
            "Rice leaf sheaths above water line develop snake-skin lesions with dark brown borders and black sclerotia.",
            "Rhizoctonia solani sheath blight in dense paddy canopies forming banded lesions.",
            "Grayish-green water-soaked lesions banding rice stems treated with validamycin or azoxystrobin."
        ],
        "disease": "Rice Sheath Blight",
        "pathogen": "Rhizoctonia solani",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "FRAC_03_DMI_Sterol_Inhibitor"
    },
    {
        "queries": [
            "Cotton leaves curling upward with swollen thickened veins and diagnostic cup-shaped enation leaf outgrowths underneath.",
            "Cotton Leaf Curl Virus CLCuV transmitted by silverleaf whitefly in Punjab and Haryana.",
            "Begomovirus CLCuV with DNA-beta satellite causing severe stunting and enations on cotton."
        ],
        "disease": "Cotton Leaf Curl Virus",
        "pathogen": "Cotton Leaf Curl Virus (CLCuV)",
        "kingdom": "Virus",
        "assay": "RT_qPCR_Viral_Amplification",
        "strategy": "Vector_Control_Thrips_Whitefly"
    },
    {
        "queries": [
            "Cotton leaves show water-soaked angular spots bounded by veins spreading into jet-black girdling cankers called black arm.",
            "Xanthomonas citri pv malvacearum bacterial blight and black arm snapping cotton branches.",
            "Acid delinting of cotton seed with sulfuric acid to eradicate bacterial blight."
        ],
        "disease": "Cotton Bacterial Blight",
        "pathogen": "Xanthomonas citri pv. malvacearum",
        "kingdom": "Bacterium",
        "assay": "KOH_String_Test_3Percent",
        "strategy": "FRAC_M01_Copper_Protectant"
    },
    {
        "queries": [
            "Chickpea seedlings exhibit sudden drooping of petioles and splitting taproot reveals dark brown internal xylem ring.",
            "Fusarium oxysporum f sp ciceri vascular wilt in gram and chana fields.",
            "Managing chickpea Fusarium wilt with Trichoderma seed treatment and resistant cultivar Avrodhi."
        ],
        "disease": "Chickpea Fusarium Wilt",
        "pathogen": "Fusarium oxysporum f. sp. ciceri",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "Biofumigation_Soil_Solarization"
    },
    {
        "queries": [
            "Pigeonpea arhar plants are bushy, stunted, with mosaic leaves and complete failure to produce flowers or pods.",
            "The green plague of pigeonpea caused by sterility mosaic virus transmitted by eriophyid mites Aceria cajani.",
            "Complete sterility and perpetual green foliage on arhar caused by PSMV emaravirus."
        ],
        "disease": "Pigeonpea Sterility Mosaic",
        "pathogen": "Pigeonpea Sterility Mosaic Virus (PSMV)",
        "kingdom": "Virus",
        "assay": "RT_qPCR_Viral_Amplification",
        "strategy": "Vector_Control_Thrips_Whitefly"
    },
    {
        "queries": [
            "Sugarcane top leaves wither and splitting the stalk longitudinally reveals blood-red pith with white transverse patches and sour alcoholic fermentation odor.",
            "Colletotrichum falcatum red rot of sugarcane converting sucrose into ethyl alcohol.",
            "Blood-red discoloration with white cross-patches inside sugarcane rind caused by red rot."
        ],
        "disease": "Sugarcane Red Rot",
        "pathogen": "Colletotrichum falcatum",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    },
    {
        "queries": [
            "Nagpur mandarin and sweet orange trees show asymmetric blotchy mottle leaves and small lopsided bitter green fruit.",
            "Citrus greening Huanglongbing HLB caused by Candidatus Liberibacter asiaticus transmitted by Diaphorina citri psyllid.",
            "Asymmetrical blotchy mottle foliar chlorosis with dark aborted seeds in citrus orchards."
        ],
        "disease": "Citrus Greening Huanglongbing",
        "pathogen": "Candidatus Liberibacter asiaticus",
        "kingdom": "Bacterium",
        "assay": "PCR_16S_Bacterial_Sequencing",
        "strategy": "Vector_Control_Thrips_Whitefly"
    },
    {
        "queries": [
            "Mango panicles turn into hypertrophied, hyper-branched, compact fleshy cauliflower-like male clusters with zero fruit set.",
            "Mango malformation caused by Fusarium mangiferae and mango bud mites producing bunchy top.",
            "Sterile cauliflower-like floral malformation and vegetative bunchy top on mango trees."
        ],
        "disease": "Mango Malformation",
        "pathogen": "Fusarium mangiferae",
        "kingdom": "Fungus",
        "assay": "PCR_ITS_Fungal_Barcoding",
        "strategy": "Sanitation_Pruning_Debris_Removal"
    }
]

def legacy_records():
    records = []
    for group in TRAINING_DATA:
        for query in group["queries"]:
            identifier = f"pathology-legacy-query-{len(records) + 1:04d}"
            records.append({
                "id": identifier, "case_id": identifier,
                "source_id": "legacy_inline_pathology_demo",
                "text": query,
                "labels": {head: group[head] for head in ("disease", "pathogen", "kingdom", "assay", "strategy")},
                "reviewed": False,
                "provenance_note": "Hand-authored demo query; no independent clinical-case provenance or source review.",
            })
    return records


def main(argv=None):
    from tiny_experts.neural.subject_training import subject_main
    return subject_main(
        "pathology", Path(__file__).resolve().parent / "training" / "configs" / "pathology.json",
        legacy_records, argv,
    )


def train():
    """Backward-compatible programmatic entry: train an explicitly experimental demo."""
    return main([])


if __name__ == "__main__":
    main()
