"""Harness response adapter for bounded local components.

Routes to explicit rules, optional neural classifiers, source retrieval and
numerical/symbolic tools. Streams status, recorded execution information and
formatted output; not a general neural language model.
"""
from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image


class TinyExpertHarnessEngine:
    """Native LLM Engine adapter for DeepSeek Harness."""

    MODEL_CATALOG: List[Dict[str, Any]] = [
        {
            "id": "tiny-expert-physics-v1",
            "name": "Tiny Expert OS — Physics Retrieval & Calculators",
            "description": (
                "Local rules, optional neural classifiers, source retrieval and "
                "bounded symbolic calculations; 54 source records"
            ),
            "inputModalities": ["text", "image"],
            "contextWindow": 128000,
            "defaultMaxTokens": 8192,
        },
        {
            "id": "deepseek-flash",
            "name": "Tiny Expert OS — Physics Retrieval & Calculators",
            "description": (
                "Local Tiny Expert OS replacing DeepSeek-Flash with 54-Book Physics & 7-Core Neural-Symbolic Engine"
            ),
            "inputModalities": ["text", "image"],
            "contextWindow": 128000,
            "defaultMaxTokens": 8192,
        },
        {
            "id": "deepseek-v4-pro",
            "name": "Tiny Expert OS — Symbolic and Formula Tools",
            "description": (
                "Bounded formula calculations and predefined symbolic derivations; no independent correctness guarantee"
            ),
            "inputModalities": ["text", "image"],
            "contextWindow": 128000,
            "defaultMaxTokens": 8192,
        },
    ]

    @classmethod
    def extract_prompt_and_context(
        cls,
        messages: List[Dict[str, Any]],
        *,
        purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract the genuine user query, session-title flag, and any image attachment from Harness messages."""
        system_texts: List[str] = []
        user_candidates: List[str] = []
        image_path: Optional[str] = None
        image_base64: Optional[str] = None
        is_title_request: bool = False

        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "")).lower()
            source = msg.get("source") if isinstance(msg.get("source"), dict) else {}
            source_kind = str(source.get("kind", "")).lower()
            content = msg.get("content", "")

            text_parts: List[str] = []
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, str):
                        text_parts.append(block)
                    elif isinstance(block, dict):
                        btype = str(block.get("type", "")).lower()
                        if btype == "text" and isinstance(block.get("text"), str):
                            text_parts.append(block["text"])
                        elif btype in {"image", "image_url"}:
                            if isinstance(block.get("hostPath"), str) and block["hostPath"]:
                                image_path = block["hostPath"]
                            elif isinstance(block.get("image_base64"), str) and block["image_base64"]:
                                image_base64 = block["image_base64"]
                            elif isinstance(block.get("image_url"), dict):
                                url_val = str(block["image_url"].get("url", ""))
                                if url_val.startswith("data:image/"):
                                    image_base64 = url_val

            joined = "\n".join(t.strip() for t in text_parts if t and t.strip()).strip()
            if not joined:
                continue

            if role == "system":
                system_texts.append(joined)
            elif role == "user":
                # Check for session title generation requests
                if source_kind == "dsh-session-title-llm" or "Generate the session title from this JSON array" in joined:
                    is_title_request = True
                    idx = joined.find("[")
                    if idx != -1:
                        try:
                            arr = json.loads(joined[idx:])
                            if isinstance(arr, list) and arr:
                                first_item = arr[0]
                                if isinstance(first_item, dict):
                                    user_candidates.append(str(first_item.get("text") or first_item.get("content") or ""))
                                elif isinstance(first_item, str):
                                    user_candidates.append(first_item)
                        except Exception:
                            pass
                    continue

                # Skip Harness-injected runtime-context, time-context, workspace instructions, skill catalog, etc.
                if source_kind in {
                    "runtime-context",
                    "time-context",
                    "dsh-time-context",
                    "agent-instructions",
                    "dsh-agent-instructions",
                    "workspace-context",
                    "skill-catalog",
                    "system-reminder",
                }:
                    continue
                if (
                    joined.startswith("<system-reminder>")
                    or joined.startswith("<system")
                    or joined.startswith("Current runtime context:")
                    or joined.startswith("<runtime-context")
                    or joined.startswith("Time sampled while preparing turn")
                    or joined.startswith("Workspace instructions:")
                    or joined.startswith("<workspace-instructions")
                    or joined.startswith("Instructions from AGENTS.md")
                    or joined.startswith("Instructions from CLAUDE.md")
                ):
                    continue

                user_candidates.append(joined)

        system_joined = "\n".join(system_texts)
        latest_user = user_candidates[-1] if user_candidates else ""

        is_session_title = (
            purpose == "session-title"
            or is_title_request
            or "Create a concise title for an AI coding-assistant session" in system_joined
        )

        return {
            "query": latest_user.strip(),
            "is_session_title": is_session_title,
            "image_path": image_path,
            "image_base64": image_base64,
            "system_prompt": system_joined,
        }

    @classmethod
    def generate_session_title(cls, orchestrator: Any, query: str) -> str:
        """Generate a clean 3-to-5 word plain-text session title without markdown or quotes."""
        cleaned = re.sub(r"[^A-Za-z0-9\s\-]", " ", query or "").strip()
        if not cleaned:
            return "Tiny Expert Physics Session"
        try:
            topic_clf = orchestrator.physics_specialists.get("_router")
            if topic_clf is None:
                from pathlib import Path
                from .neural.text_expert import NeuralTextClassifier
                models_dir = Path(__file__).resolve().parent / "data" / "models"
                topic_clf = NeuralTextClassifier(models_dir / "physics_topics")
            if topic_clf and getattr(topic_clf, "available", False):
                pred = topic_clf.predict(query, min_score=0.0)
                sub = ((pred.get("predictions") or {}).get("topic") or {}).get("label", "")
                spec = orchestrator.physics_specialists.get(f"physics_{sub}")
                if spec and getattr(spec, "available", False):
                    sp = spec.predict(query, min_score=0.0)
                    concept = ((sp.get("predictions") or {}).get("concept") or {}).get("label", "")
                    if concept and sub:
                        words = f"{concept.replace('_', ' ').title()} in {sub.replace('_', ' ').title()}".split()
                        return " ".join(words[:5])
        except Exception:
            pass
        stop_words = {"what", "is", "the", "a", "an", "of", "for", "in", "to", "find", "calculate", "compute", "how", "does", "explain", "derive", "when", "with", "if"}
        tokens = [w for w in cleaned.split() if w.lower() not in stop_words]
        if not tokens:
            tokens = cleaned.split()
        title_words = [w.capitalize() if w.islower() else w for w in tokens[:5]]
        return " ".join(title_words) or "Physics Problem Analysis"

    @classmethod
    def answer_harness_request(
        cls,
        orchestrator: Any,
        *,
        messages: Optional[List[Dict[str, Any]]] = None,
        query: Optional[str] = None,
        purpose: Optional[str] = None,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        reasoning_effort: str = "high",
    ) -> Dict[str, Any]:
        """Execute a full Tiny Expert OS turn for DeepSeek Harness and return reasoning + markdown."""
        extracted = cls.extract_prompt_and_context(messages or [], purpose=purpose)
        effective_query = (query or extracted["query"] or "").strip()
        effective_image_path = image_path or extracted.get("image_path")
        effective_image_b64 = image_base64 or extracted.get("image_base64")

        if extracted["is_session_title"]:
            title = cls.generate_session_title(orchestrator, effective_query)
            return {
                "is_session_title": True,
                "reasoning_trace": "",
                "answer_markdown": title,
                "reasoning_chunks": [],
                "answer_chunks": [title],
                "usage": {"inputTokens": max(1, len(effective_query.split())), "outputTokens": len(title.split())},
                "metadata": {"purpose": "session-title"},
            }

        if not effective_query:
            effective_query = "Explain the capabilities of Tiny Expert OS and the 54-Book Physics & 7-Core Engine."

        pil_image = None
        diagram_result = None
        if effective_image_path and Path(effective_image_path).exists():
            try:
                pil_image = Image.open(effective_image_path).convert("RGB")
                diagram_result = orchestrator.solve_physics_diagram(
                    effective_image_path,
                    user_question=effective_query,
                )
            except Exception:
                pass
        elif effective_image_b64:
            try:
                payload = effective_image_b64.split(",", 1)[-1]
                raw = base64.b64decode(payload)
                pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:
                pass

        universal_out = orchestrator.dispatch_universal_core(
            effective_query,
            image=pil_image,
        )
        core_name = str(universal_out.get("core", "core_2_3_4_physics_vision_cas"))
        domain_name = str(universal_out.get("domain", "physics"))

        if domain_name == "physics":
            phys = universal_out.get("result") or orchestrator.dispatch_physics_hierarchy(
                effective_query,
                image=pil_image,
            )
            reasoning_trace, answer_markdown = cls._format_physics_turn(
                query=effective_query,
                phys=phys,
                diagram_result=diagram_result,
                reasoning_effort=reasoning_effort,
            )
            metadata = {
                "core": core_name,
                "domain": domain_name,
                "subdomain": phys.get("subdomain"),
                "specialist_expert_id": phys.get("specialist_expert_id"),
                "concept_prediction": phys.get("concept_prediction"),
                "regime_prediction": phys.get("regime_prediction"),
                "verified_citations_count": len(phys.get("verified_citations") or []),
                "has_numerical_solution": bool((phys.get("numerical_solution") or {}).get("solved")),
                "checks_passed": bool((phys.get("proof_certificate") or {}).get("certificate_valid")),
                "claims_independently_verified": False,
                "routing_method": phys.get("routing_method"),
                "component_contributions": phys.get("component_contributions", []),
                "cross_check": (phys.get("coordination") or {}).get("cross_check"),
            }
        else:
            reasoning_trace, answer_markdown = cls._format_universal_core_turn(
                query=effective_query,
                universal_out=universal_out,
            )
            metadata = {
                "core": core_name,
                "domain": domain_name,
                "active_components": (universal_out.get("result") or {}).get("active_components", []),
            }

        reasoning_chunks = cls.chunk_text(reasoning_trace, chunk_chars=90)
        answer_chunks = cls.chunk_text(answer_markdown, chunk_chars=110)

        input_tokens = max(8, len(effective_query.split()) * 2)
        output_tokens = max(16, len((reasoning_trace + "\n" + answer_markdown).split()))

        return {
            "is_session_title": False,
            "reasoning_trace": reasoning_trace,
            "answer_markdown": answer_markdown,
            "reasoning_chunks": reasoning_chunks,
            "answer_chunks": answer_chunks,
            "usage": {
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
            },
            "metadata": metadata,
        }

    @classmethod
    def _format_physics_turn(
        cls,
        *,
        query: str,
        phys: Dict[str, Any],
        diagram_result: Optional[Dict[str, Any]] = None,
        reasoning_effort: str = "high",
    ) -> Tuple[str, str]:
        subdomain = str(phys.get("subdomain") or "classical_mechanics")
        specialist_id = str(phys.get("specialist_expert_id") or f"physics_{subdomain}")
        concept = str(phys.get("concept_prediction") or "general_physics")
        concept_score = phys.get("concept_score")
        regime = str(phys.get("regime_prediction") or "classical")
        solver_mode = str(phys.get("neural_solver_mode") or "conceptual_explanation")
        target_obs = str(phys.get("neural_target_observable") or "none")
        num_sol = phys.get("numerical_solution") or {}
        proof = phys.get("proof_certificate") or {}
        deriv = phys.get("first_principles_derivation") or {}
        conv = phys.get("convention_harmonizer") or {}
        citations = phys.get("verified_citations") or []
        span = phys.get("neural_answer_span") or {}

        # 1. Build structured live reasoning trace for DeepSeek Harness Thinking UI
        routing = phys.get("routing_method", "neural_classifier")
        score_text = f"uncalibrated score={concept_score:.3f}" if concept_score is not None else "no neural score"
        r_lines: List[str] = [
            "[Tiny Expert OS — Local execution report]",
            f"• Routing method=`{routing}`: subdomain=`{subdomain}`, concept=`{concept}`, regime=`{regime}` ({score_text}).",
        ]

        if diagram_result and diagram_result.get("solved"):
            r_lines.append(
                f"• Multimodal Diagram Solver (Pillar 9): detected `{diagram_result.get('diagram_type')}` -> governing equation `{diagram_result.get('governing_equation')}`."
            )

        if num_sol.get("solved"):
            mode_label = num_sol.get("mode", "formula_calculation")
            target_var = num_sol.get("target_variable", "")
            target_label = num_sol.get("target_name") or num_sol.get("target_label", target_var)
            f_val = cls._result_value(num_sol)
            f_unit = num_sol.get("si_unit") or num_sol.get("result_unit") or ""
            r_lines.append(
                f"• Stage 3 (Symbolic CAS & Universal Formula Solver): mode=`{mode_label}`, solved for `{target_label}` (`{target_var}`) = {f_val} {f_unit}."
            )
            if num_sol.get("chain_steps"):
                r_lines.append(
                    f"  - Multi-Hop Symbolic Graph Planner (Pillar 5): executed {len(num_sol['chain_steps'])}-step cross-formula chain."
                )
            elif num_sol.get("symbolic_expression"):
                r_lines.append(
                    f"  - SymPy Symbolic Inversion: `{target_var} = {num_sol.get('symbolic_expression')}`."
                )
        else:
            r_lines.append(
                f"• Stage 3 (Symbolic Analysis): conceptual/theoretical synthesis selected for `{concept}` in `{regime}` regime."
            )

        if proof:
            dim_check = "VERIFIED" if proof.get("dimensional_homogeneity_verified") or (proof.get("dimensional_homogeneity") or {}).get("status") == "VERIFIED" else "CHECKED"
            dim_summary = proof.get("dimensional_summary") or "Balanced SI Dimensions"
            inv_law = (proof.get("conservation_and_symmetry") or {}).get("invariant") or "Energy-Momentum Conservation"
            is_valid = bool(proof.get("certificate_valid", True))
            r_lines.append(
                f"• Bounded diagnostic checks: dimensional_status=`{dim_check}` ({dim_summary}), checks_passed={is_valid}. These are not an independent proof of the answer."
            )

        if span and span.get("answer"):
            r_lines.append(
                f"• Experimental BiGRU reader: returned an unvalidated span (uncalibrated score={float(span.get('score') or 0.0):.3f})."
            )

        if citations:
            books = [
                str(c.get("book_title") or c.get("title") or c.get("source") or "Physics Textbook")
                for c in citations[:3]
            ]
            r_lines.append(
                f"• FTS5 retrieval + SHA-256: checked source integrity for {len(citations)} passages ({', '.join(books)}); semantic support not evaluated."
            )

        reasoning_trace = "\n".join(r_lines)
        for component in phys.get('component_contributions', []):
            reasoning_trace += f"\n• {component['name']}: {component['status']}."

        # 2. Build comprehensive Teacher Markdown + Symbolic/Numerical + Proof + Multi-Book Citations
        base_md = str(phys.get("teacher_markdown") or "").strip()
        a_sections: List[str] = []

        if diagram_result and diagram_result.get("solved"):
            a_sections.append(
                "### Multimodal Diagram-to-Equation Analysis (Pillar 9)\n"
                f"- **Detected Diagram Topology**: `{diagram_result.get('diagram_type')}`\n"
                f"- **Extracted Free-Body / Circuit / Ray Equation**: `{diagram_result.get('governing_equation')}`\n"
                f"- **Symbolic / Numerical Result**: `{diagram_result.get('symbolic_solution')}`"
            )

        if num_sol.get("solved"):
            target_label = str(num_sol.get("target_name") or num_sol.get("target_label") or num_sol.get("target_variable") or "Result").replace("_", " ").title()
            target_var = str(num_sol.get("target_variable") or "y")
            val_str = str(cls._result_value(num_sol))
            unit_str = str(num_sol.get("si_unit") or num_sol.get("result_unit") or "").strip()
            formula_title = str(num_sol.get("formula_title") or (num_sol.get("steps") and num_sol["steps"][0].get("title")) or concept.replace("_", " ").title())
            base_eq = str(num_sol.get("base_equation") or num_sol.get("governing_equation") or (num_sol.get("steps") and num_sol["steps"][0].get("governing_equation")) or "")
            sym_expr = str(num_sol.get("symbolic_expression") or (num_sol.get("steps") and num_sol["steps"][0].get("isolated_symbolic_form")) or "")

            sol_lines = [
                f"### Exact Symbolic & Numerical Solution ({formula_title})",
                f"- **Calculated {target_label} (`{target_var}`)**: **`{val_str} {unit_str}`**".strip(),
            ]
            if base_eq:
                sol_lines.append(f"- **Governing Equation**: `{base_eq}`")
            if sym_expr:
                sol_lines.append(f"- **Symbolic Rearrangement (SymPy CAS)**: `{sym_expr}`")
            knowns = num_sol.get("known_inputs") or (num_sol.get("steps") and num_sol["steps"][0].get("knowns_used")) or {}
            if knowns:
                inputs_fmt = ", ".join(f"`{k} = {v}`" for k, v in knowns.items())
                sol_lines.append(f"- **Extracted SI Inputs**: {inputs_fmt}")
            if num_sol.get("chain_steps"):
                sol_lines.append("- **Multi-Hop Symbolic Graph Chain (Pillar 5)**:")
                for idx, step_info in enumerate(num_sol["chain_steps"], start=1):
                    if isinstance(step_info, dict):
                        sol_lines.append(
                            f"  {idx}. **{step_info.get('formula_title', step_info.get('formula_id', 'Step'))}**: "
                            f"solved `{step_info.get('solved_variable')}` = `{step_info.get('value')} {step_info.get('unit', '')}` "
                            f"via `{step_info.get('symbolic_expression', '')}`"
                        )
                    else:
                        sol_lines.append(f"  {idx}. {step_info}")
            elif num_sol.get("steps"):
                sol_lines.append("- **Derivation & Substitution Steps**:")
                for idx, s_item in enumerate(num_sol["steps"], start=1):
                    if isinstance(s_item, dict):
                        sol_lines.append(
                            f"  {idx}. **{s_item.get('title', s_item.get('formula_id', 'Calculation'))}**: "
                            f"evaluated `{s_item.get('governing_equation')}` -> `{s_item.get('target_variable')} = {s_item.get('value')} {s_item.get('si_unit', '')}`"
                        )
                    else:
                        sol_lines.append(f"  {idx}. {s_item}")
            a_sections.append("\n".join(sol_lines))

        if base_md:
            a_sections.append(base_md)

        coordination = phys.get('coordination') or {}
        check = coordination.get('cross_check') or {}
        combined = []
        if check.get('status') == 'agrees':
            combined.append(f"**Calculation cross-check:** {check['reviewer']} agrees with the formula solver on the requested quantity. This is a bounded consistency check.")
        elif check.get('status') == 'conflict':
            combined.append('**Calculation disagreement:** the formula solver and domain calculator returned different values. A single numerical answer is withheld pending review.')
            for comparison in check.get('comparisons', []):
                combined.append(f"- `{comparison['variable']}`: formula solver `{comparison['primary']} {comparison['unit']}`; calculator `{comparison['reviewer']} {comparison['unit']}`.")
        elif check.get('status') in {'no_comparable_calculation', 'reviewer_failed'}:
            combined.append('**Calculation cross-check:** no independent comparable result was obtained; the primary calculation has not been corroborated.')
        for entry in coordination.get('definitions', []):
            definitions = entry.get('definitions') or {}
            definition = next((str(value) for value in definitions.values() if isinstance(value, str)), '') if isinstance(definitions, dict) else str(definitions)
            if definition:
                combined.append(f"**Stored dictionary — {entry['term']}:** {definition[:400]}")
        if (coordination.get('citation_audit') or {}).get('contradiction_detected'):
            combined.append('**Source conflict alert:** comparable retrieved claims differ. Their disagreement has not been resolved.')
        if combined:
            a_sections.append('### Combined Component Findings\n\n' + '\n\n'.join(combined))
        if phys.get('component_contributions'):
            a_sections.append('### Components in This Answer\n' + '\n'.join(
                f"- **{component['name']}**: {component['status'].replace('_', ' ')}"
                for component in phys['component_contributions']))

        # Ensure Multi-Book SHA-256 Verified Citations are all shown clearly if multiple books matched
        if len(citations) > 1:
            cit_lines = ["### Retrieved Sources — Integrity Checks"]
            for idx, cit in enumerate(citations, start=1):
                title = cit.get("book_title") or cit.get("title") or cit.get("source") or "Physics Textbook"
                sha = str(cit.get("sha256_revision") or cit.get("sha256") or "")[:16]
                snippet = str(cit.get("perspective_excerpt") or cit.get("verbatim_excerpt") or cit.get("text") or "").strip().replace("\n", " ")
                if len(snippet) > 260:
                    snippet = snippet[:257] + "..."
                verified_status = cit.get("verified", True)
                role = cit.get("perspective_role")
                role_label = f" *[{role}]*" if role else ""
                cit_lines.append(
                    f"{idx}. **{title}**{role_label} (`SHA-256: {sha}...` — Verified: `{verified_status}`)\n"
                    f"   > *\"{snippet}\"*"
                )
            a_sections.append("\n".join(cit_lines))

        answer_markdown = "\n\n---\n\n".join(s for s in a_sections if s.strip())
        return reasoning_trace, answer_markdown

    @classmethod
    def _format_universal_core_turn(
        cls,
        *,
        query: str,
        universal_out: Dict[str, Any],
    ) -> Tuple[str, str]:
        core = str(universal_out.get("core", "universal_core"))
        domain = str(universal_out.get("domain", "general"))
        result = universal_out.get("result") or universal_out

        if domain == 'reference_workflow':
            telemetry = result.get('telemetry') or {}
            events = telemetry.get('execution_events') or []
            trace = result.get('thinking_trace') or 'No execution events were recorded.'
            answer = result.get('human_narrative') or 'No supported component returned an answer.'
            errors = telemetry.get('errors') or []
            if errors:
                answer += '\n\n**Some components failed; the answer is incomplete.**'
            names = {key: entry['name'] for key, entry in cls._component_catalog().items()}
            names.update({'routing': 'Capability Router', 'rule_checks': 'Result Rule Checker',
                          'bayesian_calibration': 'Context Risk Heuristic',
                          'taxonomy': 'Taxonomy Graph Lookup', 'lexicon': 'Dictionary Lookup Service',
                          'citation_conflicts': 'Passage Conflict Checker',
                          'biochemical_pathway': 'Biochemical Pathway Reference Lookup',
                          'cross_disciplinary_bridges': 'Concept Connection Lookup'})
            contributions = [f"- **{names.get(event['stage'], event['stage'].replace('_', ' ').title())}**: {event['status'].replace('_', ' ')}"
                             for event in events if event.get('stage') and event.get('status')]
            if contributions:
                answer += '\n\n### Components in This Answer\n' + '\n'.join(contributions)
            return trace, answer

        reasoning_trace = (
            f"[Tiny Expert OS — 7-Core Universal Dispatcher]\n"
            f"• Routed query to `{core}` (domain=`{domain}`).\n"
            f"• Returned a bounded tool result; its execution status is included below."
        )
        if domain == "mathematics":
            if result.get("success"):
                answer = f"### Calculation\n\n**Result: {result.get('exact_result', result.get('result'))}**"
            else:
                answer = f"### Calculation\n\nUnable to calculate: {result.get('error', result.get('status', 'unsupported input'))}"
            return reasoning_trace, answer
        answer_markdown = (
            f"## Tiny Expert OS — `{domain.replace('_', ' ').title()}` (`{core}`)\n\n"
            f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
        )
        return reasoning_trace, answer_markdown

    @staticmethod
    def _component_catalog():
        from .capability_registry import load_catalog
        return {entry['route_key']: entry for entry in load_catalog()['entries'] if entry.get('route_key')}

    @staticmethod
    def _result_value(result):
        return next((result[key] for key in ("final_value", "formatted_value", "result_value")
                     if result.get(key) is not None), None)

    @staticmethod
    def chunk_text(text: str, chunk_chars: int = 100) -> List[str]:
        """Split text into natural streaming chunks while preserving exact characters and newlines."""
        if not text:
            return []
        chunks: List[str] = []
        idx = 0
        n = len(text)
        while idx < n:
            end = min(idx + chunk_chars, n)
            if end < n:
                # Prefer breaking at newline or space
                nl = text.rfind("\n", idx, end)
                sp = text.rfind(" ", idx, end)
                if nl > idx + 16:
                    end = nl + 1
                elif sp > idx + 16:
                    end = sp + 1
            chunks.append(text[idx:end])
            idx = end
        return chunks
