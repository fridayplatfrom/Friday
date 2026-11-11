"""Offline review/evidence gate for source-backed categorical model training.

Validates bytes, passage offsets and declared reviews, not scientific truth,
copyright permissions or a human reviewer's identity.
"""
import hashlib
import re
from pathlib import Path


def audit_book_corpus(records, sources, root, *, require_review=True, current_sources=None):
    errors, texts, passages = [], {}, {}
    root = Path(root).resolve()
    if not isinstance(sources, dict) or not sources:
        return {"ready_for_training": False, "errors": ["Source manifest must be a nonempty object"]}
    if not isinstance(records, list) or not records:
        return {"ready_for_training": False, "errors": ["Dataset must be a nonempty list"]}
    for sid, source in sources.items():
        prefix = f"source {sid!r}"
        if not isinstance(sid, str) or not sid or not isinstance(source, dict):
            errors.append(f"{prefix}: invalid source entry")
            continue
        for field in ("title", "license", "source_family_id"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                errors.append(f"{prefix}: {field} is required")
        if require_review and (source.get("review_status") != "reviewed" or
                               not isinstance(source.get("reviewer"), str) or not source["reviewer"].strip()):
            errors.append(f"{prefix}: explicit source review and reviewer are required")
        digest, relative = source.get("sha256"), source.get("text_path")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{prefix}: invalid SHA256")
            continue
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            errors.append(f"{prefix}: a relative snapshot path is required")
            continue
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            errors.append(f"{prefix}: snapshot path escapes corpus root")
            continue
        try:
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("snapshot exceeds 8 MiB")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("snapshot SHA256 mismatch")
            text = raw.decode("utf-8")
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"{prefix}: {error}")
            continue
        if current_sources is not None:
            current = current_sources.get(sid)
            if not isinstance(current, dict) or any(source.get(k) != current.get(k) for k in
                                                    ("sha256", "text_path", "source_family_id", "passages")):
                errors.append(f"{prefix}: manifest does not match current indexed revision")
        texts[sid] = text
        entries = source.get("passages")
        if not isinstance(entries, list) or not entries:
            errors.append(f"{prefix}: passage manifest is missing")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"{prefix}: invalid passage entry")
                continue
            pid, start, end = entry.get("passage_id"), entry.get("start"), entry.get("end")
            if not isinstance(pid, str) or not pid or (sid, pid) in passages:
                errors.append(f"{prefix}: invalid or duplicate passage ID")
                continue
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or text[start:end] != entry.get("text"):
                errors.append(f"{prefix}: passage text/offset mismatch")
                continue
            passages[(sid, pid)] = entry
    seen_ids, seen_texts, referenced_sources, label_counts = set(), {}, set(), {}
    for i, row in enumerate(records):
        prefix = f"record {i + 1}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        if any(not isinstance(row.get(field), str) or not row[field].strip()
               for field in ("id", "case_id", "source_id", "source_revision", "text")):
            errors.append(f"{prefix}: id, case_id, source_id, source_revision and text are required")
            continue
        sid = row["source_id"]
        referenced_sources.add(sid)
        if row["id"] in seen_ids:
            errors.append(f"{prefix}: duplicate example ID")
        seen_ids.add(row["id"])
        normal = " ".join(row["text"].casefold().split())
        if normal in seen_texts:
            errors.append(f"{prefix}: duplicate example text (also {seen_texts[normal]})")
        seen_texts[normal] = row["id"]
        source = sources.get(sid)
        if sid not in texts or not isinstance(source, dict) or row["source_revision"] != source.get("sha256"):
            errors.append(f"{prefix}: source is missing, invalid or stale")
        if require_review and (row.get("reviewed") is not True or
                               not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip()):
            errors.append(f"{prefix}: annotation review and reviewer are required")
        labels = row.get("labels")
        if not isinstance(labels, dict) or not labels or not all(isinstance(k, str) and k and
                                                                 isinstance(v, str) and v for k, v in labels.items()):
            errors.append(f"{prefix}: invalid categorical labels")
        else:
            for key, value in labels.items():
                tag = f"{key}={value}"
                label_counts[tag] = label_counts.get(tag, 0) + 1
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}: passage evidence is required")
            continue
        for entry in evidence:
            if not isinstance(entry, dict) or not isinstance(entry.get("passage_id"), str):
                errors.append(f"{prefix}: malformed evidence")
                continue
            passage = passages.get((sid, entry["passage_id"]))
            quote = entry.get("quote")
            if entry.get("source_id") != sid or entry.get("source_revision") != row["source_revision"] or passage is None:
                errors.append(f"{prefix}: evidence points to a missing or different source revision")
            elif not isinstance(quote, str) or not quote.strip() or quote not in passage["text"]:
                errors.append(f"{prefix}: evidence quote is absent from the source passage")
    used = [sources[s] for s in referenced_sources if s in sources and isinstance(sources[s], dict)]
    independent_hashes = {s.get("sha256") for s in used if isinstance(s.get("sha256"), str)}
    independent_families = {s.get("source_family_id") for s in used if isinstance(s.get("source_family_id"), str)}
    if require_review and min(len(independent_hashes), len(independent_families)) < 3:
        errors.append("Reviewed training requires at least three distinct source families and content hashes; one book is a demo, not unseen-source evaluation")
    return {"ready_for_training": not errors, "experimental": not require_review,
            "records": len(records), "referenced_sources": len(referenced_sources),
            "distinct_source_hashes": len(independent_hashes), "source_families": len(independent_families),
            "label_counts": label_counts, "errors": errors,
            "limitations": ["Exact text support does not establish label correctness or scientific truth.",
                            "Declared review and permission fields are not independently authenticated.",
                            "Source families still require human grouping; near-duplicate editions may evade exact hashes."]}
