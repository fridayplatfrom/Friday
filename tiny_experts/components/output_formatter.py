import json
from typing import Any, Dict
from .base_component import BaseComponent
from ..pipeline.multilingual_normalizer import MultilingualVernacularNormalizer

class OutputFormatter(BaseComponent):
    """Formats structured results as cards or JSON."""
    name = 'Output Formatter'
    description = 'Formats structured results as cards or JSON.'
    component_kind = 'formatter'
    uses_neural_model = False
    updates_parameters_at_inference = False

    def __init__(self):
        super().__init__(
            name='Output Formatter',
            description='Formats structured results as cards or JSON.'
        )

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        output_format = context.get("format", "card").lower()
        aggregated = context.get("aggregated_results", {})

        if output_format == "json":
            return {
                "format": "json",
                "rendered": json.dumps(aggregated, indent=2)
            }

        lines = []
        border = "=" * 64
        sub_border = "-" * 64

        lines.append(border)
        lines.append("   TINY EXPERT SYSTEM: COMPONENT EXECUTION REPORT   ")
        lines.append(border)
        lines.append("Reference content is unreviewed unless its source record explicitly says otherwise.")
        if aggregated.get("unsupported"):
            lines.append(aggregated["unsupported"]["message"])
        for failed in aggregated.get("errors", []):
            lines.append(f"[STAGE ERROR] {failed['stage']}: {failed['error']}")
        for key in ("math", "electronics", "mechanics", "thermodynamics"):
            for error in aggregated.get(key, {}).get("errors", []):
                lines.append(f"[{key.upper()} INPUT ERROR] {error}")

        # 0. Communicator Expert Persona & Conversational Dialogue
        comm = aggregated.get("communicator", {})
        narrative = aggregated.get("human_narrative") or (comm.get("speech_synthesis") if isinstance(comm, dict) else None)
        if comm and isinstance(comm, dict) and comm.get("persona_title"):
            badge = comm.get("persona_badge", "🧑‍🌾")
            title = comm.get("persona_title", "Universal Communicator")
            lines.append(f"[{badge} {title.upper()}]")
            if comm.get("tone"):
                lines.append(f"   * Tone: {comm.get('tone')}")
            if comm.get("pedagogy_principles_applied"):
                lines.append(f"   * Pedagogy:      {', '.join(comm.get('pedagogy_principles_applied', [])[:2])}")
            lines.append("")
            for p in (narrative or "").splitlines():
                lines.append(f"  {p}")
            lines.append(sub_border)
        elif narrative:
            lines.append("[RENDERED COMPONENT RESULTS]")
            for p in narrative.splitlines():
                lines.append(f"  {p}")
            lines.append(sub_border)

        for expert_id, result in aggregated.items():
            if isinstance(result, dict) and "model_predictions" in result:
                lines.append(f"[NEURAL TASK: {expert_id}] [{result.get('status')}]")
                lines.append(result.get("message") or "")
                for head, prediction in result.get("model_predictions", {}).items():
                    lines.append(f"   * {head}: {prediction['label']} (uncalibrated score {prediction['score']:.3f})")
                lines.append(sub_border)

        # 1. Subject Identification
        vision = aggregated.get("vision", {})
        if vision.get("detected"):
            lines.append(f"[SUBJECT]     {vision.get('species')} ({vision.get('scientific_name')})")
            if vision.get("confidence") is not None:
                lines.append(f"[MODEL SCORE] {vision['confidence']:.3f} (uncalibrated) [via {vision.get('source')}]")
            else:
                lines.append(f"[INPUT SOURCE] {vision.get('source')} (identity not independently verified)")
            lines.append(f"[CATEGORY]    {vision.get('category', '').upper()}")
            lines.append(sub_border)

        # 2. Safety / Toxicity Alert
        toxicity = aggregated.get("toxicity", {})
        if toxicity.get("is_hazardous"):
            lines.append(f"[TOXICITY ALERT] [{toxicity.get('hazard_level')}]")
            lines.append(f"   * Toxin Agent:  {toxicity.get('toxic_agent')}")
            lines.append(f"   * Symptoms:     {toxicity.get('symptoms')}")
            lines.append(f"   * Action:       {toxicity.get('emergency_first_aid')}")
            lines.append(sub_border)
        elif toxicity.get("advisory") and "NONE" not in toxicity.get("hazard_level", ""):
            lines.append(f"[SAFETY CHECK]  {toxicity.get('hazard_level')}")
            lines.append(f"   * Note: {toxicity.get('advisory')}")
            lines.append(sub_border)

        # 3. PubChem Chemical Record
        pubchem = toxicity.get("pubchem")
        if pubchem:
            lines.append(f"[PUBCHEM CHEMICAL RECORD] (CID: {pubchem.get('pubchem_cid')})")
            lines.append(f"   * Compound:     {pubchem.get('compound')}")
            lines.append(f"   * Formula:      {pubchem.get('formula')} | MW: {pubchem.get('molecular_weight')}")
            lines.append(f"   * IUPAC Name:   {pubchem.get('iupac_name')}")
            lines.append(f"   * Mechanism:    {pubchem.get('mechanism')}")
            lines.append(sub_border)

        # 4. ASPCA Pet Safety Advisory
        pet_safety = toxicity.get("pet_safety")
        if pet_safety:
            lines.append("[ASPCA PET & ANIMAL SAFETY ADVISORY]")
            if isinstance(pet_safety, dict):
                lines.append(f"   * Dogs:   {pet_safety.get('dogs')}")
                lines.append(f"   * Cats:   {pet_safety.get('cats')}")
                lines.append(f"   * Horses: {pet_safety.get('horses')}")
            else:
                lines.append(f"   * Advisory: {str(pet_safety)}")
            lines.append(sub_border)

        # 4b. Multi-Agent Debate & Cross-Verification Matrix
        debate = aggregated.get("multi_agent_debate")
        if debate:
            lines.append("[RULE-BASED RESULT COMPARISON: NOT INDEPENDENT VERIFICATION]")
            r1 = debate.get("round_1_proposition", {})
            r2 = debate.get("round_2_cross_examination", {})
            r3 = debate.get("round_3_corroboration")
            if r1.get("squad"):
                lines.append(f"   * Proposition ({r1.get('squad', '').title()}):      {r1.get('claim')}")
            if r2.get("squad"):
                lines.append(f"   * Cross-Examination ({r2.get('squad', '').title()}): {r2.get('audit')}")
            if r3 and r3.get("squad"):
                lines.append(f"   * Corroboration ({r3.get('squad', '').title()}):    {r3.get('audit')}")
            lines.append(f"   * Consensus Finding:    {debate.get('final_consensus')}")
            lines.append(sub_border)

        # 4c. Evolutionary Taxonomy & Trait Inheritance
        taxa = aggregated.get("taxonomic_lineage")
        if taxa and taxa.get("matched"):
            lineage_names = [item["node"] for item in taxa.get("lineage", [])]
            traits = taxa.get("inherited_traits", {})
            lines.append(f"[EVOLUTIONARY TAXONOMY & TRAIT INHERITANCE] [{taxa.get('rank', 'Clade').upper()}]")
            lines.append(f"   * Lineage:       {' > '.join(lineage_names[-4:])}")
            if traits.get("chemical_family"):
                lines.append(f"   * Phyto-Family:  {traits.get('chemical_family')}")
            if traits.get("hazard_effect"):
                lines.append(f"   * Inherited Tox: {traits.get('hazard_effect')}")
            if traits.get("symbiosis"):
                lines.append(f"   * Symbiosis:     {traits.get('symbiosis')}")
            lines.append(sub_border)

        # 4d. Biochemical Pathway & Clinical Drug Interactions
        biochem = aggregated.get("biochemical_pathway")
        if biochem:
            lines.append(f"[BIOCHEMICAL PATHWAY: {biochem.get('pathway_name').upper()}]")
            lines.append(f"   * Target Receptor: {biochem.get('target')}")
            lines.append(f"   * Cellular Action: {biochem.get('biochemical_mechanism')}")
            if biochem.get("antidote_protocol"):
                lines.append(f"   * Antidote Guide:  {biochem.get('antidote_protocol')}")
            if biochem.get("detected_drug_interactions"):
                lines.append("   * [WARNING] CLINICAL DRUG INTERACTIONS:")
                for inter in biochem.get("detected_drug_interactions", []):
                    lines.append(f"     - {inter.get('class')} [{inter.get('severity')}]: {inter.get('advisory')}")
            lines.append(sub_border)

        # 4e. Bayesian Lookalike Disambiguation
        bayes = aggregated.get("bayesian_calibration")
        if bayes:
            lines.append("[LOOKALIKE HEURISTIC SCORES: NOT CALIBRATED PROBABILITIES]")
            for c in bayes.get("calibrated_posterior", []):
                lines.append(f"   * {c.get('candidate')} -> score {c.get('evidence_score', c.get('probability'))} [{c.get('hazard')}]")
            if bayes.get("differentiator_test"):
                lines.append(f"   * MANDATORY TEST: {bayes.get('differentiator_test')}")
            lines.append(sub_border)

        # 5. Genetics & Genomics
        genetics = aggregated.get("genetics", {})
        if genetics.get("relevant"):
            lines.append("[GENETICS & MOLECULAR BIOLOGY]")
            lines.append(f"   * Concept:    {genetics.get('concept')}")
            lines.append(f"   * Mechanism:  {genetics.get('mechanism')}")
            lines.append(f"   * Regulation: {genetics.get('regulatory_control')}")
            lines.append(sub_border)

        # 6. Cell Biology & Bioenergetics
        cell_bio = aggregated.get("cell_biology", {})
        if cell_bio.get("relevant"):
            lines.append("[CELL BIOLOGY & BIOENERGETICS]")
            lines.append(f"   * Concept:   {cell_bio.get('concept')}")
            lines.append(f"   * Pathway:   {cell_bio.get('cellular_pathway')}")
            lines.append(f"   * Organelle: {cell_bio.get('organelle_locus')}")
            lines.append(sub_border)

        # 7. Microbiology & Virology (NEW)
        micro = aggregated.get("microbiology", {})
        if micro.get("relevant"):
            lines.append("[MICROBIOLOGY & VIROLOGY]")
            lines.append(f"   * Concept:    {micro.get('concept')}")
            lines.append(f"   * Mechanism:  {micro.get('mechanism')}")
            lines.append(f"   * Machinery:  {micro.get('biochemical_machinery')}")
            lines.append(f"   * Role:       {micro.get('ecological_importance')}")
            lines.append(sub_border)

        # 8. Evolutionary Biology & Paleontology (NEW)
        evo = aggregated.get("evolution", {})
        if evo.get("relevant"):
            lines.append("[EVOLUTIONARY BIOLOGY & PALEONTOLOGY]")
            lines.append(f"   * Concept:      {evo.get('concept')}")
            lines.append(f"   * Mechanism:    {evo.get('mechanism')}")
            lines.append(f"   * Significance: {evo.get('macroevolution_significance')}")
            lines.append(f"   * Cladistics:   {evo.get('phylogenetic_principle')}")
            lines.append(sub_border)

        # 9. Marine Biology & Oceanography (NEW)
        marine = aggregated.get("marine", {})
        if marine.get("relevant"):
            lines.append("[MARINE BIOLOGY & OCEANOGRAPHY]")
            lines.append(f"   * Concept:      {marine.get('concept')}")
            lines.append(f"   * Mechanism:    {marine.get('mechanism')}")
            lines.append(f"   * Ocean Impact: {marine.get('oceanographic_impact')}")
            lines.append(f"   * Carbon Role:  {marine.get('biogeochemical_role')}")
            lines.append(sub_border)

        # 10. Plant Pathology & Diagnostic Clinic
        pathology = aggregated.get("pathology", {})
        if pathology.get("relevant"):
            lines.append(f"[PLANT PATHOLOGY REFERENCE] [{pathology.get('clinical_division', 'General Clinic').upper()}]")
            if pathology.get("differential_alert"):
                lines.append(f"   * {pathology.get('differential_alert')}")
            lines.append(f"   * Condition: {pathology.get('pathology_condition')} [{pathology.get('status')}]")
            if pathology.get("message"):
                lines.append(f"   * Note: {pathology['message']}")
            if pathology.get("pathogen_latin_name"):
                lines.append(f"   * Pathogen:  {pathology.get('pathogen_latin_name')} [{pathology.get('causal_kingdom', 'Microorganism')}]")
            lines.append(f"   * Symptoms:  {pathology.get('symptoms_profile')}")
            lines.append(f"   * Etiology:  {pathology.get('pathogen_mode_of_action')}")
            if pathology.get("clinical_treatment"):
                lines.append(f"   * Management reference: {pathology['clinical_treatment']}")
            if pathology.get("ipm_action"):
                lines.append(f"   * IPM Plan:  {pathology.get('ipm_action')}")
            if pathology.get("recommended_lab_assay"):
                lines.append(f"   * Lab Assay: {pathology.get('recommended_lab_assay')}")
            if pathology.get("visual_reference_plate"):
                v_plate = pathology.get("visual_reference_plate")
                lines.append(f"   * Visual Ref: [{v_plate.get('plate_id')}] {v_plate.get('book')}")
                lines.append(f"     Hallmarks:  {v_plate.get('hallmarks')}")
            lines.append(sub_border)

        # 10b. Quantitative Disease Triangle & Outbreak Forecasting
        dt = pathology.get("disease_triangle_risk")
        if dt:
            lines.append(f"[WEATHER EPIDEMIOLOGY: {dt.get('risk_level', 'OUTBREAK ASSESSMENT').upper()}]")
            lines.append(f"   * Disease:       {dt.get('disease')}")
            lines.append(f"   * Model:         {dt.get('model_used')}")
            lines.append(f"   * Rule assessment: {dt.get('status', 'heuristic')} [{dt.get('severity_value')}]; no calibrated outbreak probability")
            lines.append(f"   * Microclimate:  {dt.get('weather_snapshot')}")
            lines.append(f"   * Forecast:      {dt.get('symptom_window')}")
            lines.append(f"   * Action Plan:   {dt.get('preventative_action')}")
            lines.append(sub_border)

        # 10c. Statutory Agrochemical Ban & Regulatory Alert
        reg = pathology.get("regulatory_alert") or (aggregated.get("toxicity", {}).get("statutory_violation") if isinstance(aggregated.get("toxicity"), dict) else None)
        if reg:
            lines.append("[LEGAL & STATUTORY REGULATORY ALERT: BANNED PESTICIDE]")
            lines.append(f"   * Prohibited:    {reg.get('banned_chemical', 'Banned Pesticide')}")
            lines.append(f"   * Statutory Law: {reg.get('statutory_order')}")
            lines.append(f"   * Hazard Class:  {reg.get('hazard_class', reg.get('hazard'))}")
            lines.append(f"   * Legal Warning: {reg.get('statutory_warning')}")
            lines.append(f"   * Legal Option:  {reg.get('legal_alternative')}")
            lines.append(sub_border)

        # 10d. Multilingual Regional Advisory (Hindi / Punjabi / Telugu / Tamil / Marathi)
        vern = aggregated.get("vernacular_meta", {})
        if vern and vern.get("is_vernacular"):
            lang = vern.get("detected_language", "hi")
            d_name = vern.get("canonical_disease") or (pathology.get("pathology_condition", "").split(" (")[0] if pathology.get("relevant") else "Crop Condition")
            p_name = vern.get("canonical_pathogen") or pathology.get("pathogen_latin_name", "")
            tx = pathology.get("clinical_treatment") or "विशेषज्ञ से संपर्क करें"
            loc_advice = MultilingualVernacularNormalizer.get_localized_advisory(lang=lang, disease=d_name, pathogen=p_name, treatment=tx)
            if loc_advice:
                lines.append(f"[REGIONAL MULTILINGUAL ADVISORY: {lang.upper()} (क्षेत्रीय कृषक परामर्श)]")
                lines.append(f"   * भाषा / Language: {lang.upper()}")
                lines.append(f"   * कृषक परामर्श:    {loc_advice}")
                lines.append(sub_border)

        # 10e. Real-Time Outbreak News Alert (Tier 3)
        outbreak = aggregated.get("outbreak_alert")
        if outbreak:
            lines.append(f"[ARCHIVED OUTBREAK REFERENCE] [{outbreak.get('urgency')}]")
            lines.append(f"   * Bulletin ID: {outbreak.get('bulletin_id')} (Date: {outbreak.get('date')})")
            lines.append(f"   * Headline:    {outbreak.get('headline')}")
            lines.append(f"   * Surveillance:{outbreak.get('summary')}")
            lines.append(f"   * Mandate:     {outbreak.get('mandatory_advisory')}")
            lines.append(f"   * Source:      {outbreak.get('source')}")
            lines.append(sub_border)

        # 10f. 60-Second In-Field Diagnostic Decision Key (Tier 7)
        in_test = aggregated.get("in_field_diagnostic_test")
        if in_test:
            lines.append(f"[🔬 60-SECOND IN-FIELD DIAGNOSTIC TEST] ({in_test.get('university_source')})")
            lines.append(f"   * Test Name: {in_test.get('test_name')}")
            for step in in_test.get("in_field_steps", []):
                lines.append(f"     • {step}")
            lines.append(f"   * Outcome:   {in_test.get('rapid_diagnostic_outcome')}")
            lines.append(sub_border)

        # 10g. Mandi Commodity Economics & Treatment ROI (Tier 6)
        market_eco = aggregated.get("market_economics")
        if market_eco:
            lines.append(f"[💰 MANDI MARKET ECONOMICS & ROI] [{market_eco.get('viability_status')}]")
            lines.append(f"   * Commodity:   {market_eco.get('crop')} (Modal Price: ₹{market_eco.get('modal_price_per_kg_inr')}/kg | e-NAM)")
            lines.append(f"   * Mandi Hub:   {market_eco.get('primary_mandi')} [Trend: {market_eco.get('market_trend')}]")
            lines.append(f"   * Feasibility: {market_eco.get('financial_advisory')}")
            lines.append(sub_border)

        # 10h. Field Demonstration Video Technique (Tier 5)
        video_demo = aggregated.get("field_demonstration")
        if video_demo:
            lines.append(f"[🎥 FIELD VIDEO DEMONSTRATION] ({video_demo.get('demonstrator')})")
            lines.append(f"   * Video Title: {video_demo.get('video_title')} [Timestamp: {video_demo.get('timestamp')}]")
            lines.append(f"   * Topic:       {video_demo.get('technique_title')}")
            lines.append(f"   * Technique:   {video_demo.get('key_technique')}")
            lines.append(sub_border)

        # 10i. Authoritative Extension Blog Deep Links (Tier 4)
        blog_guide = aggregated.get("extension_blog")
        if blog_guide:
            lines.append(f"[🌐 VERIFIED EXTENSION BLOG & DEEP LINKS] ({blog_guide.get('institution')})")
            lines.append(f"   * Guide Title: {blog_guide.get('title')}")
            lines.append(f"   * Author:      {blog_guide.get('author')} ({blog_guide.get('publication_year')})")
            lines.append(f"   * Deep URL:    {blog_guide.get('canonical_url')}")
            for tip in blog_guide.get("field_pro_tips", [])[:2]:
                lines.append(f"     • Pro-Tip: {tip}")
            lines.append(sub_border)

        # 11. Mycology & Fungal Networks
        mycology = aggregated.get("mycology", {})
        if mycology.get("relevant"):
            lines.append("[MYCOLOGY & FUNGAL SYMBIOSIS]")
            lines.append(f"   * Concept:   {mycology.get('concept')}")
            lines.append(f"   * Mechanism: {mycology.get('mechanism')}")
            lines.append(f"   * Ecology:   {mycology.get('ecological_role')}")
            lines.append(sub_border)

        # 12. Entomology (Insects)
        entomology = aggregated.get("entomology", {})
        if entomology.get("relevant"):
            lines.append("[ENTOMOLOGY & INSECT PHYSIOLOGY]")
            lines.append(f"   * Concept:    {entomology.get('concept')}")
            lines.append(f"   * Physiology: {entomology.get('mechanism')}")
            lines.append(f"   * Advantage:  {entomology.get('ecological_advantage')}")
            lines.append(sub_border)

        # 13. Ornithology (Avian Science)
        ornithology = aggregated.get("ornithology", {})
        if ornithology.get("relevant"):
            lines.append("[ORNITHOLOGY & AVIAN SCIENCE]")
            lines.append(f"   * Concept:     {ornithology.get('concept')}")
            lines.append(f"   * Biomechanics:{ornithology.get('mechanism')}")
            lines.append(f"   * Adaptation:  {ornithology.get('physiological_adaptation')}")
            lines.append(sub_border)

        # 14. Botany Details
        botany = aggregated.get("botany", {})
        if botany.get("relevant"):
            lines.append("[BOTANICAL PROFILE]")
            lines.append(f"   * Type:     {botany.get('botanical_type')}")
            lines.append(f"   * Sun:      {botany.get('sunlight_requirement')}")
            lines.append(f"   * Watering: {botany.get('watering_schedule')}")
            lines.append(f"   * Soil:     {botany.get('soil_profile')}")
            lines.append(f"   * Care:     {botany.get('recommendation')}")
            lines.append(sub_border)

        # 15. Wildlife Details
        wildlife = aggregated.get("wildlife", {})
        if wildlife.get("relevant"):
            lines.append("[WILDLIFE & ECOLOGY PROFILE]")
            lines.append(f"   * Class:     {wildlife.get('biological_class')}")
            lines.append(f"   * Diet:      {wildlife.get('diet')}")
            lines.append(f"   * Habitat:   {wildlife.get('primary_habitat')}")
            lines.append(f"   * Migration: {wildlife.get('migration_profile')}")
            lines.append(f"   * Status:    {wildlife.get('status')}")
            lines.append(f"   * Behavior:  {wildlife.get('behavioral_notes')}")
            lines.append(sub_border)

        # 16. Ecology & Trophic Cascades
        ecology = aggregated.get("ecology", {})
        if ecology.get("relevant"):
            lines.append("[ECOLOGY & BIOME DYNAMICS]")
            lines.append(f"   * Concept:   {ecology.get('concept')}")
            lines.append(f"   * Mechanism: {ecology.get('mechanism')}")
            lines.append(f"   * Impact:    {ecology.get('biogeochemical_impact')}")
            lines.append(sub_border)

        # 17. Math & Calculations
        math = aggregated.get("math", {})
        if math.get("performed_calculation"):
            lines.append("[MATHEMATICAL CALCULATIONS & SYMBOLIC CAS]")
            for item in math.get("details", []):
                t = item.get("type")
                if t == "Plot Density Calculation":
                    lines.append(f"   * Spacing:   {item.get('recommended_spacing')}")
                    lines.append(f"   * Capacity:  {item.get('row_capacity')}")
                    lines.append(f"   * Density:   {item.get('square_plot_capacity')}")
                elif t == "Height Unit Conversion":
                    lines.append(f"   * Height:    {item.get('metric')} ({item.get('imperial')})")
                elif t == "Arithmetic":
                    lines.append(f"   * Math:      {item.get('expression')} = {item.get('result')}")
                elif t == "Symbolic Differentiation":
                    lines.append(f"   * Derivative: d/dx [{item.get('expression')}] = {item.get('derivative')}")
                    if item.get("latex"):
                        lines.append(f"     LaTeX:      $${item.get('latex')}$$")
                elif t == "Symbolic Integration":
                    lines.append(f"   * Integral:   ∫ {item.get('expression')} dx = {item.get('integral')}")
                    if item.get("numerical_value") is not None:
                        lines.append(f"     Definite:   {item.get('numerical_value')}")
                    if item.get("latex"):
                        lines.append(f"     LaTeX:      $${item.get('latex')}$$")
                elif t == "Algebraic Equation Solver":
                    lines.append(f"   * Equation:   {item.get('equation')}")
                    lines.append(f"     Roots:      {', '.join(item.get('roots', []))}")
                    if item.get("latex"):
                        lines.append(f"     LaTeX:      {item.get('latex')}")
                elif t == "First-Principles Physics Derivation":
                    lines.append(f"   * Law:        {item.get('law')}")
                    lines.append(f"     Formula:    {item.get('formula')}")
                    if item.get("latex"):
                        lines.append(f"     LaTeX:      $${item.get('latex')}$$")
            lines.append(sub_border)

        # 17a. Dynamic Visual Schematic & Vector Diagram
        if aggregated.get("svg_diagram"):
            lines.append("[📐 DYNAMIC VECTOR SCHEMATIC GENERATED]")
            lines.append("   * Visualization: Dark-Mode Responsive SVG Vector Schematic Rendered.")
            lines.append("   * Accessible in: Telemetry JSON as svg_diagram.")
            lines.append(sub_border)

        # 17b. Universal Librarian & Master Book Encyclopedia
        librarian = aggregated.get("librarian", {})
        if librarian.get("relevant") and librarian.get("matched_books"):
            lines.append("[📚 UNIVERSAL BOOK ENCYCLOPEDIA & MASTER BIBLIOGRAPHY]")
            lines.append(f"   * Total Library Size: {librarian.get('total_catalog_size')} catalog records")
            for b in librarian.get("matched_books", [])[:3]:
                auth = ", ".join(b.get("authors") or []) or "not supplied"
                t_title = b.get("translated_title") or b.get("title")
                lines.append(f"   📖 {t_title} ({b.get('year') or 'year not supplied'}) - {b.get('edition') or 'edition not supplied'}")
                lines.append(f"      • Author:    {auth}")
                lines.append(f"      • Faculty:   {b.get('faculty_label')} [{b.get('discipline_label')}]")
                lines.append(f"      • Publisher: {b.get('publisher') or 'not supplied'} (ISBN: {b.get('isbn') or 'not supplied'})")
                lines.append(f"      • Review:    {b.get('review_status', 'unreviewed')}")
                if b.get("translated_summary"):
                    lines.append(f"      • Summary:   {b.get('translated_summary')}")
            lines.append(sub_border)

        # 17c. Thermodynamics Calculations & Thermal Physics
        thermo = aggregated.get("thermodynamics", {})
        if thermo.get("calculations") or (thermo.get("active") and thermo.get("detected_principles")):
            lines.append("[🔥 THERMODYNAMICS & THERMAL TRANSPORT]")
            for p in thermo.get("detected_principles", []):
                lines.append(f"   * Principle: {p}")
            for c_name, c_data in thermo.get("calculations", {}).items():
                if isinstance(c_data, dict):
                    f_str = c_data.get("formula", "")
                    lines.append(f"   ⚡ {c_name.replace('_', ' ').title()}: `{f_str}`")
                    for k, v in c_data.items():
                        if k not in ["formula", "formulas"]:
                            lines.append(f"      • {k}: {v}")
            lines.append(sub_border)

        # 17d. Electronics & Circuit Electrodynamics
        elec = aggregated.get("electronics", {})
        if elec.get("calculations") or (elec.get("active") and elec.get("detected_principles")):
            lines.append("[⚡ ELECTRONICS & CIRCUIT THEORY]")
            for p in elec.get("detected_principles", []):
                lines.append(f"   * Principle: {p}")
            for c_name, c_data in elec.get("calculations", {}).items():
                if isinstance(c_data, dict):
                    f_str = c_data.get("formula", "")
                    lines.append(f"   ⚡ {c_name.replace('_', ' ').title()}: `{f_str}`")
                    for k, v in c_data.items():
                        if k not in ["formula", "formulas"]:
                            lines.append(f"      • {k}: {v}")
            lines.append(sub_border)

        # 17e. Mechanics & Classical Dynamics
        mech = aggregated.get("mechanics", {})
        if mech.get("calculations") or (mech.get("active") and mech.get("detected_principles")):
            lines.append("[⚙️ CLASSICAL MECHANICS & DYNAMICS]")
            for p in mech.get("detected_principles", []):
                lines.append(f"   * Principle: {p}")
            for c_name, c_data in mech.get("calculations", {}).items():
                if isinstance(c_data, dict):
                    f_str = c_data.get("formula", "")
                    lines.append(f"   ⚙️ {c_name.replace('_', ' ').title()}: `{f_str}`")
                    for k, v in c_data.items():
                        if k not in ["formula", "formulas"]:
                            lines.append(f"      • {k}: {v}")
            lines.append(sub_border)

        # 17f. Epistemic Peer Review, Consensus & Dialectics
        rev = aggregated.get("review", {})
        if rev.get("matched"):
            lines.append("[⚖️ EPISTEMIC PEER REVIEW & SCHOLARLY CONSENSUS]")
            lines.append(f"   * Work:      {rev.get('book_title')}")
            lines.append(f"   * Stored review status: {rev.get('consensus_status')} (not independently verified)")
            for pr in rev.get("peer_reviews", [])[:2]:
                lines.append(f"   📰 Review:   {pr.get('source')} ({pr.get('rating')}/5.0)")
                lines.append(f"      • Verdict:    {pr.get('verdict')}")
                lines.append(f"      • Strengths:  {pr.get('key_strengths')}")
                lines.append(f"      • Limitation: {pr.get('identified_limitations')}")
            for deb in rev.get("debates_and_critiques", [])[:2]:
                lines.append(f"   ⚖️ Debate:    {deb.get('topic')}")
                lines.append(f"      • Canonical: {deb.get('canonical_view')}")
                lines.append(f"      • Critique:  {deb.get('critique_and_counterview')}")
                lines.append(f"      • Verdict:   {deb.get('consensus_verdict')}")
            lines.append(sub_border)

        # 17g. Cross-Disciplinary Concept Graph Bridges
        cross_bridges = aggregated.get("cross_disciplinary_bridges", [])
        if cross_bridges:
            lines.append("[🌐 CROSS-DISCIPLINARY CONCEPT BRIDGES]")
            for b in cross_bridges[:2]:
                lines.append(f"   * Link:      [{b.get('subject_faculty')}] {b.get('subject')} ──({b.get('predicate')})──> [{b.get('object_faculty')}] {b.get('object')}")
                lines.append(f"     Mechanism: {b.get('mechanism')}")
            lines.append(sub_border)

        # 17h. Dialectical Contradiction & Arbitration
        dialectic = aggregated.get("dialectic_arbitration", {})
        if dialectic.get("has_contradiction"):
            lines.append("[⚠️ DIALECTICAL CONTRADICTION & ARBITRATION]")
            for disp in dialectic.get("paradigm_disputes", []):
                lines.append(f"   * Dispute:     {disp.get('topic')}")
                lines.append(f"     • School A:  {disp.get('school_a')}")
                lines.append(f"     • School B:  {disp.get('school_b')}")
                lines.append(f"     • Resolution:{disp.get('arbitration')}")
            for warn in dialectic.get("boundary_condition_warnings", []):
                lines.append(f"   * Boundary:    {warn.get('parameter')} ({warn.get('value')}): {warn.get('note')}")
            lines.append(sub_border)

        # 17h-2. Dynamic Automated Contradiction Discovery
        auto_dialectic = aggregated.get("automated_contradiction", {})
        if auto_dialectic.get("contradiction_detected"):
            lines.append("[⚡ AUTOMATED DIALECTICAL RECONCILIATION MATRIX]")
            for rec in auto_dialectic.get("reconciliations", [])[:2]:
                lines.append(f"   * Variance Type: {rec.get('type')}")
                lines.append(f"     • Thesis:     {rec.get('thesis')}")
                lines.append(f"     • Antithesis: {rec.get('antithesis')}")
                lines.append(f"     • Synthesis:  {rec.get('synthesis')}")
            lines.append(sub_border)

        # 17i. Universal Biographer Profile (Tier 2)
        biographer = aggregated.get("biographer", {})
        if biographer.get("matched") and biographer.get("primary_person"):
            p = biographer.get("primary_person")
            lines.append("[👤 UNIVERSAL BIOGRAPHICAL PROFILE & IMPACT]")
            lines.append(f"   * Person:     {p.get('display_name') or p.get('name')} ({p.get('birth_death_years')}) [{p.get('nationality')}]")
            lines.append(f"   * Faculty:    {p.get('faculty')}")
            lines.append(f"   * Overview:   {p.get('biography_summary')}")
            for inv in p.get("major_inventions_and_theories", [])[:3]:
                lines.append(f"   💡 Innovation: {inv}")
            if p.get("landmark_quotes"):
                lines.append(f"   💬 Quote:     \"{p.get('landmark_quotes')[0]}\"")
            lines.append(sub_border)

        # 17j. Multilingual Lexicon & Epistemic Dictionary
        lexicon = aggregated.get("lexicon_definition")
        if lexicon:
            lines.append("[📖 MULTILINGUAL LEXICON & ETYMOLOGY]")
            lines.append(f"   * Term:       {lexicon.get('term', '').upper()} ({lexicon.get('part_of_speech')})")
            lines.append(f"   * Vernacular: {lexicon.get('localized_term')}")
            lines.append(f"   * Etymology:  {lexicon.get('etymology')}")
            defs = lexicon.get("definitions", {})
            for d_faculty, d_text in defs.items():
                lines.append(f"   * Def [{d_faculty}]: {d_text}")
            lines.append(sub_border)

        # 17k. Curated Consensus Top 10 / How-To / What-Is
        top10 = aggregated.get("consensus_top_10")
        if top10:
            lines.append(f"[🏆 CONSENSUS RANKED COLLECTION: {top10.get('title')}]")
            lines.append(f"   * Methodology: {top10.get('consensus_method')}")
            for item in top10.get("ranked_items", [])[:5]:
                lines.append(f"   #{item.get('rank')}: {item.get('title')} ({item.get('author') or item.get('discoverer', '')})")
                lines.append(f"      • Impact: {item.get('justification') or item.get('impact')}")
            lines.append(sub_border)

        howto = aggregated.get("procedural_how_to")
        if howto:
            lines.append(f"[🛠️ PROCEDURAL FIELD MANUAL: {howto.get('title')}]")
            lines.append(f"   * Source: {howto.get('authoritative_source')}")
            for s in howto.get("steps", []):
                lines.append(f"   Step {s.get('step_num')}: {s.get('action')} - {s.get('detail')}")
            lines.append(sub_border)

        whatis = aggregated.get("axiomatic_what_is")
        if whatis:
            lines.append(f"[💡 AXIOMATIC PRIMER: {whatis.get('title')}]")
            lines.append(f"   * Authority: {whatis.get('authoritative_source')}")
            lines.append(f"   * Core Axiom:{whatis.get('axiomatic_summary')}")
            lines.append(sub_border)

        # 17l. Authoritative Sovereign & Research Web Directory
        web_sites = aggregated.get("authoritative_web_directory", [])
        if web_sites:
            lines.append("[🏛️ VERIFIED WEB & STATUTORY DIRECTORY]")
            for s in web_sites[:3]:
                lines.append(f"   * {s.get('badge')}: {s.get('title')}")
                lines.append(f"     URL:  {s.get('url')}")
                lines.append(f"     Desc: {s.get('description')}")
            lines.append(sub_border)

        # 18. Aggregated Textbook & Communication Citations
        citations = []
        for exp_key, data in aggregated.items():
            if isinstance(data, dict):
                c = data.get("textbook_citation")
                if c:
                    citations.append(c)
                plural = data.get("textbook_citations")
                if isinstance(plural, list):
                    citations.extend(c for c in plural if isinstance(c, dict))
                comm_cits = data.get("communication_citations")
                if isinstance(comm_cits, list):
                    citations.extend(comm_cits)

        if citations:
            lines.append("[RETRIEVED SOURCE PASSAGES: RELEVANCE IS NOT CLAIM VERIFICATION]")
            seen_sources = set()
            for c in citations:
                src = c.get("source")
                if src and src not in seen_sources:
                    seen_sources.add(src)
                    lines.append(f"   * Source: {src} [{c.get('review_status', 'unreviewed')}]")
                    lines.append(f"     \"{c.get('text')}\"")
            lines.append(sub_border)

        # Router metadata
        router_meta = aggregated.get("orchestration_meta", {})
        lines.append(f"[ACTIVE COMPONENTS] {', '.join(router_meta.get('invoked_experts', []))}")
        lines.append(f"[SYSTEM LATENCY] {router_meta.get('latency_ms', 0)} ms on Local CPU")
        lines.append(border)

        return {
            "format": "card",
            "rendered": "\n".join(lines)
        }


# Compatibility for existing integrations and model-training imports.
FormatExpert = OutputFormatter
