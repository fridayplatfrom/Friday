import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiny_experts.pipeline.harvester import ScientificDataHarvester
from tiny_experts.pipeline.knowledge_store import KnowledgeStore

def main():
    parser = argparse.ArgumentParser(description="Harvest and ingest scientific data into the Tiny Expert AI System.")
    parser.add_argument("species", nargs="?", default="Lavender", help="Name of the plant, bird, insect, or animal to harvest")
    args = parser.parse_args()

    print(f"\n[HARVESTER] Querying open scientific knowledge base for: '{args.species}'...")
    record = ScientificDataHarvester.harvest(args.species)

    if not record:
        print(f"[ERROR] Could not find or parse open records for '{args.species}'. Please check spelling.\n")
        return

    # Save to local knowledge store
    KnowledgeStore.save(record, search_alias=args.species)

    print(f"[SUCCESS] Ingested and validated '{record.common_name}' into Tiny Expert System!\n")
    print("=" * 60)
    print(f"Common Name:     {record.common_name}")
    print(f"Scientific Name: {record.scientific_name}")
    print(f"Category:        {record.category.upper()}")
    print(f"Habitat:         {record.habitat}")
    print(f"Hazard Level:    {record.hazard_level}")
    print(f"Toxin Notes:     {record.toxin_notes}")
    print(f"Summary:         {record.summary}")
    print("=" * 60)
    print("\nAll micro-experts now have instant access to this record on local CPU.\n")

if __name__ == "__main__":
    main()
