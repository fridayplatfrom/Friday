"""Offline gate for reviewed categorical expert training data.

This checks record structure and declared provenance; it cannot independently
verify book content or reviewer identity.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


def audit(records, sources, min_sources=2, min_cases=2):
    errors = []
    seen_ids, seen_texts, source_ids = set(), set(), set()
    cases = collections.defaultdict(set)
    for n, r in enumerate(records, 1):
        prefix = f"record {n}"
        if not isinstance(r, dict):
            errors.append(f"{prefix}: not an object")
            continue
        identifier = r.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen_ids:
            errors.append(f"{prefix}: missing/duplicate id")
        seen_ids.add(identifier)
        txt = r.get("text")
        if not isinstance(txt, str) or not txt.strip():
            errors.append(f"{prefix}: missing text")
        else:
            fingerprint = hashlib.sha256(" ".join(txt.casefold().split()).encode()).hexdigest()
            if fingerprint in seen_texts:
                errors.append(f"{prefix}: duplicate text")
            seen_texts.add(fingerprint)
        sid, cid = r.get("source_id"), r.get("case_id")
        if not isinstance(sid, str) or not sid or not isinstance(cid, str) or not cid:
            errors.append(f"{prefix}: source_id and case_id required")
            continue
        source_ids.add(sid)
        src = sources.get(sid)
        if not isinstance(src, dict):
            errors.append(f"{prefix}: source not in manifest")
            continue
        if src.get("review_status") != "reviewed":
            errors.append(f"{prefix}: source not reviewed")
        if not isinstance(src.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", src["sha256"]):
            errors.append(f"{prefix}: missing/invalid source sha256")
        if not isinstance(src.get("license"), str) or not src["license"].strip():
            errors.append(f"{prefix}: source license/permission missing")
        if not isinstance(src.get("title"), str) or not src["title"].strip():
            errors.append(f"{prefix}: source title missing")
        if r.get("reviewed") is not True or not isinstance(r.get("reviewer"), str) or not r["reviewer"].strip():
            errors.append(f"{prefix}: reviewer approval missing")
        labels = r.get("labels")
        if not isinstance(labels, dict) or not labels:
            errors.append(f"{prefix}: labels missing")
        else:
            for task, value in labels.items():
                if not isinstance(task, str) or not task or not isinstance(value, str) or not value:
                    errors.append(f"{prefix}: invalid label")
                else:
                    cases[(task, value)].add((sid, cid))
        evidence = r.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(e, dict) or e.get("source_id") != sid or
            not isinstance(e.get("passage_id"), str) or not e.get("passage_id")
            for e in evidence
        ):
            errors.append(f"{prefix}: missing/mismatched passage evidence")
    if len(source_ids) < min_sources:
        errors.append(f"need {min_sources} independent source IDs; got {len(source_ids)}")
    for key, groups in cases.items():
        if len(groups) < min_cases:
            errors.append(f"{key}: need {min_cases} distinct source cases; got {len(groups)}")
    if not records:
        errors.append("empty dataset")
    return {
        "ready_for_manual_training_review": not errors,
        "records": len(records),
        "sources": len(source_ids),
        "case_counts": {"=".join(k): len(v) for k, v in sorted(cases.items())},
        "errors": errors,
        "limitation": "This gate checks declared IDs, labels, rights and reviewer fields only. Verify source files, evidence spans and reviewer identity separately."
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--sources", required=True, type=Path)
    p.add_argument("--min-sources", type=int, default=2)
    p.add_argument("--min-cases-per-label", type=int, default=2)
    args = p.parse_args(argv)
    if args.min_sources < 1 or args.min_cases_per_label < 1:
        p.error("minimums must be positive")
    with args.data.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    if not isinstance(sources, dict):
        p.error("sources must be a JSON object keyed by source_id")
    report = audit(records, sources, args.min_sources, args.min_cases_per_label)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ready_for_manual_training_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
