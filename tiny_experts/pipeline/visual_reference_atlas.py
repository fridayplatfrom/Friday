import os
import json
from typing import Dict, Any, Optional

class VisualReferenceAtlas:
    """
    Unverified visual reference lookup for plant pathology.
    Contains legacy illustrative labels and unverified textbook references,
    figure callouts, diagnostic hallmarks, and local photographic file paths.
    """

    _sources_figures_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "books", "pathology", "figures"
    )
    _legacy_figures_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "books", "pathology", "figures"
    )
    DEFAULT_FIGURES_DIR = _sources_figures_dir if os.path.exists(_sources_figures_dir) else _legacy_figures_dir

    ATLAS_REGISTRY: Dict[str, Dict[str, Any]] = {
        # --- Division 1: Fungi & Oomycetes ---
        "Early Blight": {
            "book": "Agrios' Plant Pathology 6th Edition (2024)",
            "plate_id": "Plate 11.4",
            "page": 412,
            "hallmarks": "Concentric necrotic rings ('target-board' / 'bullseye' pattern) with chlorotic yellow halo.",
            "tissue": "Lower foliage, petioles, and stem collar lesions",
            "plate_file": "plate_early_blight.png"
        },
        "Late Blight": {
            "book": "Agrios' Plant Pathology 6th Edition (2024)",
            "plate_id": "Plate 10.2",
            "page": 385,
            "hallmarks": "Water-soaked dark lesions with profuse white cottony sporulation on abaxial (underside) leaf surface.",
            "tissue": "Foliage, petioles, and potato tubers",
            "plate_file": "plate_late_blight.png"
        },
        "Powdery Mildew": {
            "book": "Agrios' Plant Pathology 6th Edition (2024)",
            "plate_id": "Plate 12.1",
            "page": 468,
            "hallmarks": "Superficial white powdery fungal patches (epiphytic mycelium and conidiophores) over adaxial leaf surface.",
            "tissue": "Upper leaf surface, petioles, and young stems",
            "plate_file": "plate_powdery_mildew.png"
        },
        "Downy Mildew": {
            "book": "APS Compendium of Cucurbit Diseases 2nd Ed. (2020)",
            "plate_id": "Plate 3.5",
            "page": 29,
            "hallmarks": "Angular chlorotic lesions strictly delimited by leaf veins; purplish-grey felt-like down on leaf underside.",
            "tissue": "Leaf blades (interveinal)",
            "plate_file": "plate_downy_mildew.png"
        },
        "Fusarium Wilt": {
            "book": "Agrios' Plant Pathology 6th Edition (2024)",
            "plate_id": "Plate 11.18",
            "page": 435,
            "hallmarks": "Unilateral yellowing of foliage and distinctive dark brown vascular ring discoloration in xylem split stems.",
            "tissue": "Xylem vessels, lower stem, taproot",
            "plate_file": "plate_fusarium_wilt.png"
        },
        "Black Stem Rust": {
            "book": "Mehrotra & Aggarwal Plant Pathology 3rd Edition",
            "plate_id": "Plate 8.1",
            "page": 320,
            "hallmarks": "Elongated reddish-brown uredinial pustules rupturing stem epidermis; black telia late in season.",
            "tissue": "Culms, leaf sheaths, and cereal spikes",
            "plate_file": "plate_black_stem_rust.png"
        },
        "Apple Scab": {
            "book": "APS Compendium of Apple and Pear Diseases 2nd Ed.",
            "plate_id": "Plate 2.1",
            "page": 14,
            "hallmarks": "Olive-green velvety fungal lesions on foliage turning dark brown and corky with fruit cracking.",
            "tissue": "Foliage, calyx, and mature fruit",
            "plate_file": "plate_apple_scab.png"
        },

        # --- Division 2: Agricultural Bacteriology ---
        "Bacterial Canker": {
            "book": "Agrios' Plant Pathology 6th Edition (2024)",
            "plate_id": "Plate 14.2",
            "page": 532,
            "hallmarks": "'Bird's-eye' circular fruit spots with brown centers and white haloes; open stem cankers with yellow bacterial ooze.",
            "tissue": "Stems, petioles, and fruit",
            "plate_file": "plate_bacterial_canker.png"
        },
        "Bacterial Wilt": {
            "book": "Agrios' Plant Pathology 6th Edition (2024)",
            "plate_id": "Plate 14.5",
            "page": 544,
            "hallmarks": "Rapid green wilting without prior yellowing; viscous milky bacterial streaming in clear water test.",
            "tissue": "Vascular xylem bundles and root crown",
            "plate_file": "plate_bacterial_wilt.png"
        },
        "Citrus Canker": {
            "book": "Mehrotra & Aggarwal Plant Pathology 3rd Edition",
            "plate_id": "Plate 15.3",
            "page": 580,
            "hallmarks": "Raised, crateriform corky lesions surrounded by characteristic oily, chlorotic yellow halos.",
            "tissue": "Leaves, green twigs, and citrus rind",
            "plate_file": "plate_citrus_canker.png"
        },
        "Bacterial Soft Rot": {
            "book": "Agrios' Plant Pathology 6th Edition (2024)",
            "plate_id": "Plate 14.9",
            "page": 558,
            "hallmarks": "Rapid, slimy, water-soaked tissue breakdown with strong putrid odor (pectinolytic maceration).",
            "tissue": "Fleshy storage organs, tubers, fruit",
            "plate_file": "plate_bacterial_soft_rot.png"
        },

        # --- Division 3: Plant Virology ---
        "Tobacco Mosaic Virus": {
            "book": "Roger Hull, Plant Virology 5th Edition (2014)",
            "plate_id": "Plate 4.1",
            "page": 110,
            "hallmarks": "Light green and dark green blistered mosaic patterns, foliar distortion, and fern leaf deformation.",
            "tissue": "Young actively growing apical leaves",
            "plate_file": "plate_tobacco_mosaic_virus.png"
        },
        "Tomato Yellow Leaf Curl": {
            "book": "APS Compendium of Tomato Diseases 2nd Ed.",
            "plate_id": "Plate 8.6",
            "page": 74,
            "hallmarks": "Severe upward leaf cupping, marginal chlorosis, internodal stunting, and bushy upright rosettes.",
            "tissue": "Apical vegetative meristems and flowers",
            "plate_file": "plate_tomato_yellow_leaf_curl.png"
        },
        "Tomato Spotted Wilt": {
            "book": "Roger Hull, Plant Virology 5th Edition (2014)",
            "plate_id": "Plate 9.4",
            "page": 312,
            "hallmarks": "Concentric bronze ringspots, foliar bronzing, terminal bud necrosis, and chlorotic fruit rings.",
            "tissue": "Foliage, growing shoot tips, and green fruit",
            "plate_file": "plate_tomato_spotted_wilt.png"
        },

        # --- Division 4: Nematology ---
        "Root-Knot Nematode": {
            "book": "Perry & Moens, Plant Nematology 2nd Edition (2013)",
            "plate_id": "Plate 5.2",
            "page": 195,
            "hallmarks": "Spherical to irregularly lobed swollen root galls with absence of root hairs and stunted vascular cylinder.",
            "tissue": "Subterranean root system and taproot",
            "plate_file": "plate_root_knot_nematode.png"
        },
        "Soybean Cyst Nematode": {
            "book": "Perry & Moens, Plant Nematology 2nd Edition (2013)",
            "plate_id": "Plate 6.1",
            "page": 240,
            "hallmarks": "Tiny white to yellow lemon-shaped female cysts clinging to roots; severe interveinal leaf chlorosis ('yellow dwarf').",
            "tissue": "Feeder roots and foliar canopy",
            "plate_file": "plate_soybean_cyst_nematode.png"
        },

        # --- Division 5: Abiotic Differential Diagnoses ---
        "Blossom End Rot": {
            "book": "APS Compendium of Tomato Diseases 2nd Ed.",
            "plate_id": "Plate 14.1",
            "page": 102,
            "hallmarks": "Flat to sunken dark brown to black leathery lesion strictly at the distal blossom end (NON-INFECTIOUS Ca2+ DEFICIENCY).",
            "tissue": "Distal blossom end of green/ripening fruit",
            "plate_file": "plate_blossom_end_rot.png"
        },
        "Iron Chlorosis": {
            "book": "Mineral Nutrition and Plant Disease 2nd Edition",
            "plate_id": "Plate 7.3",
            "page": 145,
            "hallmarks": "Sharp ivory-yellow interveinal chlorosis with dark green veins preserved on newest terminal leaves.",
            "tissue": "Youngest upper apical foliage",
            "plate_file": "plate_iron_chlorosis.png"
        },
        "Herbicide Drift": {
            "book": "APS Compendium of Tomato Diseases 2nd Ed.",
            "plate_id": "Plate 14.8",
            "page": 115,
            "hallmarks": "Epinasty, severe downward twisting and bending of petioles, strap-like leaf blades with parallel venation.",
            "tissue": "Rapidly growing shoots and leaves",
            "plate_file": "plate_herbicide_drift.png"
        },

        # --- Indian Tropical & ICAR Crop Diseases ---
        "Rice Bacterial Leaf Blight": {
            "book": "ICAR / TNAU Rice Pathology Handbook (2024)",
            "plate_id": "Plate 6.2",
            "page": 88,
            "hallmarks": "Water-soaked streaks with wavy margins on leaf blades turning straw-colored; seedling kresek systemic wilting.",
            "tissue": "Leaf blades and seedling tillers",
            "plate_file": "plate_rice_bacterial_leaf_blight.png"
        },
        "Sugarcane Red Rot": {
            "book": "ICAR Sugarcane Diseases Manual",
            "plate_id": "Plate 4.1",
            "page": 112,
            "hallmarks": "Internal longitudinal red discoloration of stalk pith interspersed with diagnostic white transverse patches.",
            "tissue": "Internal stem pith and foliar midribs",
            "plate_file": "plate_sugarcane_red_rot.png"
        },
        "Cotton Leaf Curl": {
            "book": "ICAR Central Institute for Cotton Research (CICR) Bulletin",
            "plate_id": "Plate 3.1",
            "page": 45,
            "hallmarks": "Upward leaf curling, extreme vein thickening, and enations (cup-shaped foliar outgrowths on leaf undersides).",
            "tissue": "Foliar veins and shoot terminals",
            "plate_file": "plate_cotton_leaf_curl.png"
        },
        "Citrus Greening": {
            "book": "APS Compendium of Citrus Diseases",
            "plate_id": "Plate 9.2",
            "page": 130,
            "hallmarks": "Asymmetrical blotchy foliar mottle crossing leaf veins; lopsided bitter fruit with aborted dark seeds.",
            "tissue": "Canopy foliage, branches, and fruit",
            "plate_file": "plate_citrus_greening.png"
        }
    }

    @staticmethod
    def _mark_unverified(entry: Dict[str, Any]) -> Dict[str, Any]:
        # The historical atlas shipped book/plate/page attributions without
        # direct verified image provenance. Never surface these as citations.
        entry["legacy_unverified_attribution"] = {
            "book": entry.pop("book", None),
            "plate_id": entry.pop("plate_id", None),
            "page": entry.pop("page", None)
        }
        entry["verification_status"] = "unverified"
        entry["review_status"] = "unreviewed"
        entry["image_type"] = "illustrative_unverified"
        entry["citation"] = None
        return entry

    @classmethod
    def get_reference_plate(cls, disease_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves visual textbook plate data for a given disease entity.
        Supports fuzzy lookup across synonyms.
        """
        if not disease_name:
            return None

        clean_name = disease_name.strip()
        # Direct lookup
        if clean_name in cls.ATLAS_REGISTRY:
            data = dict(cls.ATLAS_REGISTRY[clean_name])
            plate_path = os.path.join(cls.DEFAULT_FIGURES_DIR, data.get("plate_file", ""))
            data["exists_locally"] = os.path.exists(plate_path)
            data["local_path"] = plate_path if os.path.exists(plate_path) else None
            return cls._mark_unverified(data)

        # Substring / alias lookup
        lower_name = clean_name.lower()
        for reg_disease, data in cls.ATLAS_REGISTRY.items():
            if lower_name in reg_disease.lower() or reg_disease.lower() in lower_name:
                ret = dict(data)
                plate_path = os.path.join(cls.DEFAULT_FIGURES_DIR, ret.get("plate_file", ""))
                ret["exists_locally"] = os.path.exists(plate_path)
                ret["local_path"] = plate_path if os.path.exists(plate_path) else None
                return cls._mark_unverified(ret)

        return None
