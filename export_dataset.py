"""Export unreviewed response candidates; this command does not train a model."""

import argparse
import os

from tiny_experts.pipeline.dataset_exporter import ScientificDatasetExporter


def main():
    parser = argparse.ArgumentParser(description="Export programmatic expert responses for independent review.")
    parser.add_argument("--format", "-f", choices=["alpaca", "sharegpt"], default="alpaca",
                        help="Instruction/response exchange format, not a classifier dataset")
    parser.add_argument("--output", "-o", default=os.path.join("data", "training", "candidate_responses.jsonl"),
                        help="Output JSONL path")
    args = parser.parse_args()
    result = ScientificDatasetExporter().export_to_jsonl(args.output, args.format)
    print(f"[OK] Exported {result['total_samples']} unreviewed response candidates to {result['filepath']}.")
    print(f"  Format: {result['format']} | Size: {result['file_size_kb']} KB")
    print("Review and label each example before training. These responses are not verified facts")
    print("and cannot be passed directly to the domain classifier training scripts.")


if __name__ == "__main__":
    main()
