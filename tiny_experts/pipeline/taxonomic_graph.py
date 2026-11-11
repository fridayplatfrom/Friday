import networkx as nx
from typing import Dict, Any, List, Optional

class TaxonomicKnowledgeGraph:
    """
    Hierarchical Evolutionary Knowledge Graph (DAG).
    Maintains taxonomic lineage:
    Domain -> Kingdom -> Phylum -> Class -> Order -> Family -> Genus -> Species.
    Enables automatic biological trait inheritance:
    When an unknown species is introduced, it inherits ancestral physiological,
    chemical, and metabolic properties from its Family/Genus nodes.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_tree()

    def _build_tree(self):
        # Root node
        self.graph.add_node("Biota", rank="domain", traits={})

        # Kingdoms
        self.graph.add_node("Plantae", rank="kingdom", traits={"chloroplasts": True, "photosynthesis": True, "cell_wall": "cellulose"})
        self.graph.add_node("Animalia", rank="kingdom", traits={"motility": True, "heterotrophic": True, "cell_wall": "none"})
        self.graph.add_node("Fungi", rank="kingdom", traits={"chitin_cell_wall": True, "absorptive_heterotroph": True, "hyphae": True})
        self.graph.add_node("Bacteria", rank="kingdom", traits={"prokaryotic": True, "peptidoglycan_wall": True})

        self.graph.add_edge("Biota", "Plantae")
        self.graph.add_edge("Biota", "Animalia")
        self.graph.add_edge("Biota", "Fungi")
        self.graph.add_edge("Biota", "Bacteria")

        # 1. Family: Anacardiaceae (Cashew / Sumac)
        self.graph.add_node(
            "Anacardiaceae",
            rank="family",
            traits={
                "chemical_family": "pentadecylcatechols",
                "active_compounds": ["urushiol"],
                "hazard_effect": "Type IV cell-mediated contact dermatitis",
                "morphology": "resin canals containing phenolic allergenic resins"
            }
        )
        self.graph.add_edge("Plantae", "Anacardiaceae")
        self.graph.add_node("Toxicodendron", rank="genus", traits={"growth_habit": "woody vine or shrub"})
        self.graph.add_edge("Anacardiaceae", "Toxicodendron")
        self.graph.add_node(
            "Toxicodendron radicans",
            common_name="Poison Ivy",
            rank="species",
            traits={"leaflet_count": 3, "foliage": "shiny trifoliate leaves"}
        )
        self.graph.add_edge("Toxicodendron", "Toxicodendron radicans")

        # 2. Family: Solanaceae (Nightshades)
        self.graph.add_node(
            "Solanaceae",
            rank="family",
            traits={
                "chemical_family": "tropane alkaloids & steroidal glycoalkaloids",
                "active_compounds": ["atropine", "scopolamine", "hyoscyamine", "solanine"],
                "hazard_effect": "Anticholinergic muscarinic receptor blockade",
                "antidote": "physostigmine"
            }
        )
        self.graph.add_edge("Plantae", "Solanaceae")
        self.graph.add_node("Atropa", rank="genus", traits={"flower_form": "bell-shaped dull purple corolla"})
        self.graph.add_edge("Solanaceae", "Atropa")
        self.graph.add_node(
            "Atropa belladonna",
            common_name="Deadly Nightshade",
            rank="species",
            traits={"fruit": "shiny black spherical berries"}
        )
        self.graph.add_edge("Atropa", "Atropa belladonna")

        # 3. Family: Fabaceae (Legumes)
        self.graph.add_node(
            "Fabaceae",
            rank="family",
            traits={
                "symbiosis": "root nodule mutualism with diazotrophic Rhizobia",
                "nitrogen_fixation": True,
                "protein_buffer": "leghemoglobin",
                "fruit_type": "legume pod with marginal placentation"
            }
        )
        self.graph.add_edge("Plantae", "Fabaceae")

        # 4. Family: Amanitaceae (Amanita Fungi)
        self.graph.add_node(
            "Amanitaceae",
            rank="family",
            traits={
                "chemical_family": "cyclic peptides (amatoxins & phallotoxins)",
                "active_compounds": ["alpha-amanitin"],
                "hazard_effect": "Irreversible inhibition of eukaryotic RNA Polymerase II; centrilobular hepatic lysis",
                "spore_print": "white",
                "basal_structure": "volva universal veil cup"
            }
        )
        self.graph.add_edge("Fungi", "Amanitaceae")
        self.graph.add_node("Amanita", rank="genus", traits={"gills": "free white lamellae"})
        self.graph.add_edge("Amanitaceae", "Amanita")
        self.graph.add_node(
            "Amanita phalloides",
            common_name="Death Cap",
            rank="species",
            traits={"lethality": "fatal in ingestion doses as low as 0.1 mg/kg"}
        )
        self.graph.add_edge("Amanita", "Amanita phalloides")

        # 5. Order: Scleractinia (Stony Corals)
        self.graph.add_node(
            "Scleractinia",
            rank="order",
            traits={
                "skeleton": "biogenic aragonite calcium carbonate (CaCO3)",
                "endosymbiosis": "Symbiodiniaceae dinoflagellates",
                "salinity_requirement": "marine (34-37 ppt)",
                "thermal_vulnerability": "photoinhibition and reactive oxygen species bleaching"
            }
        )
        self.graph.add_edge("Animalia", "Scleractinia")

        # 6. Family: Nymphalidae (Brush-footed Butterflies)
        self.graph.add_node(
            "Nymphalidae",
            rank="family",
            traits={
                "forelegs": "reduced non-functional brush-like forelegs",
                "metamorphosis": "holometabolous"
            }
        )
        self.graph.add_edge("Animalia", "Nymphalidae")
        self.graph.add_node("Danaus", rank="genus", traits={"aposematism": "orange and black cautionary coloration"})
        self.graph.add_edge("Nymphalidae", "Danaus")
        self.graph.add_node(
            "Danaus plexippus",
            common_name="Monarch Butterfly",
            rank="species",
            traits={
                "sequestration": "cardenolides (cardiac glycosides) from Asclepias",
                "resistance_mutation": "Na+/K+-ATPase Asn122His substitution",
                "predator_defense": "emetic deterrent against avian Passeriformes"
            }
        )
        self.graph.add_edge("Danaus", "Danaus plexippus")

        # 7. Family: Ailuridae (Red Panda Family)
        self.graph.add_node(
            "Ailuridae",
            rank="family",
            traits={
                "diet_specialization": "specialized folivore (bamboo)",
                "adaptation": "modified radial sesamoid false thumb",
                "habitat": "temperate montane cloud forests"
            }
        )
        self.graph.add_edge("Animalia", "Ailuridae")
        self.graph.add_node("Ailurus", rank="genus", traits={"claws": "semi-retractile curved claws"})
        self.graph.add_edge("Ailuridae", "Ailurus")
        self.graph.add_node(
            "Ailurus fulgens",
            common_name="Red Panda",
            rank="species",
            traits={"range": "Eastern Himalayas", "status": "Endangered"}
        )
        self.graph.add_edge("Ailurus", "Ailurus fulgens")

    def find_node(self, name: str) -> Optional[str]:
        """Finds matching node by scientific name, common name, or genus."""
        n_lower = name.lower()
        for node, data in self.graph.nodes(data=True):
            if node.lower() == n_lower:
                return node
            if data.get("common_name", "").lower() == n_lower:
                return node
            if n_lower in node.lower():
                continue
        return None

    def get_inherited_traits(self, name: str) -> Dict[str, Any]:
        """
        Traverses ancestral nodes in the DAG to aggregate all inherited traits.
        Even if an individual species has never been observed, it automatically
        inherits ancestral chemical, physiological, and metabolic properties.
        """
        matched_node = self.find_node(name)
        if not matched_node:
            return {"matched": False, "inherited_traits": {}, "lineage": []}

        # Find all ancestors in the DAG
        ancestors = nx.ancestors(self.graph, matched_node)
        # Order lineage topologically from Root down to the matched node
        ordered_nodes = [n for n in nx.topological_sort(self.graph) if n in ancestors or n == matched_node]

        aggregated_traits: Dict[str, Any] = {}
        ancestral_trait_hints: Dict[str, Any] = {}
        lineage_trace: List[Dict[str, str]] = []

        for node in ordered_nodes:
            node_data = self.graph.nodes[node]
            rank = node_data.get("rank", "clade")
            traits = node_data.get("traits", {})
            lineage_trace.append({"node": node, "rank": rank})

            for key, val in traits.items():
                if node == matched_node:
                    aggregated_traits[key] = val
                else:
                    # Ancestral annotations can have exceptions. Hazard, dose,
                    # active compounds and antidotes are not species-level facts.
                    ancestral_trait_hints[key] = val

        return {
            "matched": True,
            "target": matched_node,
            "rank": self.graph.nodes[matched_node].get("rank"),
            "lineage": lineage_trace,
            "inherited_traits": aggregated_traits,
            "ancestral_trait_hints_unverified": ancestral_trait_hints,
            "lineage_verification": "hardcoded_unreviewed",
            "hazard_inference_allowed": False
        }
