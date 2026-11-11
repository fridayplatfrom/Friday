import re
from typing import List, Dict, Any, Optional

class UniversalConceptGraph:
    """Keyword retrieval over a small set of curated cross-domain triples.

    Returned links are references, not automatically established causal claims.
    """

    CONCEPT_TRIPLES = [
        # 1. Physics <-> Botany / Agronomy: Radiation & Photosynthesis
        {
            "subject": "Solar Radiation (Photon Flux)",
            "subject_faculty": "Physics",
            "predicate": "drives_light_reactions_in",
            "object": "Photosystem II & Chloroplasts",
            "object_faculty": "Botany / Cell Biology",
            "mechanism": "Photons at 400-700nm (PAR) excite chlorophyll P680 electrons, driving photolysis of water into protons, electrons, and O2."
        },
        # 2. Physics <-> Botany: Fourier Heat & Transpiration
        {
            "subject": "Fourier Heat Conduction & Latent Vaporization",
            "subject_faculty": "Physics",
            "predicate": "provides_evaporative_cooling_for",
            "object": "Leaf Canopy & Mesophyll Cells",
            "object_faculty": "Botany",
            "mechanism": "Phase-change latent heat of water (2.45 MJ/kg) absorbs solar thermal flux, keeping leaf temperature below protein denaturation thresholds."
        },
        # 3. Physics <-> Physiology: Electrodynamics & Action Potential
        {
            "subject": "Nernst Potential & Ohm's Law",
            "subject_faculty": "Physics",
            "predicate": "governs_ion_flux_across",
            "object": "Axonal Membrane & Voltage-Gated Channels",
            "object_faculty": "Cell Biology / Physiology",
            "mechanism": "Electrochemical potential gradient drives Na+/K+ ions through membrane channels, generating 100mV action potential spikes."
        },
        # 4. Thermodynamics <-> Mycology / Pathology: VPD & Infection
        {
            "subject": "Vapor Pressure Deficit (VPD)",
            "subject_faculty": "Physics / Meteorology",
            "predicate": "triggers_spore_germination_in",
            "object": "Phytophthora & Alternaria Spores",
            "object_faculty": "Pathology / Mycology",
            "mechanism": "When VPD falls below 0.2 kPa (relative humidity > 95%), free moisture films persist on leaf surfaces, allowing zoospores to encyst and penetrate stomata."
        },
        # 5. History <-> Constitutional Law: Decolonization & Constitutionalism
        {
            "subject": "Decolonization & 1947 Partition",
            "subject_faculty": "History",
            "predicate": "necessitated_fundamental_rights_in",
            "object": "Constitution of India (Articles 14-30)",
            "object_faculty": "Constitutional Law",
            "mechanism": "Communal displacement and social inequalities led Dr. Ambedkar and the Constituent Assembly to enshrine fundamental equality and minority cultural protections."
        }
    ]

    SEARCH_TERMS = [
        ["solar radiation", "photon", "photosynthesis", "chlorophyll", "photosystem"],
        ["heat conduction", "transpiration", "evaporative cooling", "leaf canopy", "latent heat"],
        ["nernst", "ohm", "action potential", "axon", "membrane potential"],
        ["vapor pressure deficit", "vpd", "phytophthora", "alternaria", "spore germination"],
        ["decolonization", "partition", "fundamental rights", "constitution of india"],
    ]

    @classmethod
    def find_cross_connections(cls, query: str) -> List[Dict[str, Any]]:
        """Retrieve curated concept links; do not claim causal inference."""
        q_lower = query.lower()
        found = []
        for triple, terms in zip(cls.CONCEPT_TRIPLES, cls.SEARCH_TERMS):
            matches = [term for term in terms if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", q_lower)]
            if matches:
                found.append({**triple, "matched_terms": matches, "status": "curated_concept_reference",
                              "inference_performed": False, "source_validation": "not_verified"})
        return found
