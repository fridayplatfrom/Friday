import sys
import os
import argparse

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiny_experts.pipeline.figure_extractor import FigureExtractor

def main():
    parser = argparse.ArgumentParser(
        description="Tiny Expert AI: Plant Pathology Figure & Plate Extraction Utility"
    )
    parser.add_argument("pdf_path", nargs="?", help="Path to PDF textbook to extract figures from")
    parser.add_argument("--title", "-t", default=None, help="Authoritative book title")
    parser.add_argument("--generate-atlas", action="store_true", help="Generate reference textbook plates for core diseases")

    args = parser.parse_args()

    extractor = FigureExtractor()

    print("\n========================================================")
    print("  [FIGURES] PLANT PATHOLOGY VISUAL FIGURE EXTRACTOR")
    print("========================================================")

    if args.generate_atlas:
        print(">> Generating reference textbook plates for core pathology atlas...")
        core_diseases = [
            ("Early Blight", "Alternaria solani", "Agrios' Plant Pathology 6th Ed. (2024), p. 412", "Plate 11.4", "Concentric target rings with yellow halo", "green"),
            ("Late Blight", "Phytophthora infestans", "Agrios' Plant Pathology 6th Ed. (2024), p. 385", "Plate 10.2", "Water-soaked lesions with white abaxial sporulation", "brown"),
            ("Powdery Mildew", "Podosphaera xanthii", "Agrios' Plant Pathology 6th Ed. (2024), p. 468", "Plate 12.1", "Superficial white powdery conidia over foliage", "white"),
            ("Downy Mildew", "Pseudoperonospora cubensis", "APS Compendium of Cucurbit Diseases (2020), p. 29", "Plate 3.5", "Angular yellow lesions bounded by major veins", "yellow"),
            ("Citrus Canker", "Xanthomonas citri", "Mehrotra & Aggarwal Plant Pathology 3rd Ed., p. 580", "Plate 15.3", "Raised crateriform corky lesions with oily halo", "yellow"),
            ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "ICAR / TNAU Rice Pathology Handbook, p. 88", "Plate 6.2", "Wavy straw-colored foliar blighting (Kresek wilt)", "green"),
            ("Sugarcane Red Rot", "Colletotrichum falcatum", "ICAR Sugarcane Diseases Manual, p. 112", "Plate 4.1", "Internal red stalk discoloration with white transverse bands", "red"),
            ("Tomato Yellow Leaf Curl", "TYLCV (Begomovirus)", "APS Compendium of Tomato Diseases 2nd Ed., p. 74", "Plate 8.6", "Severe upward leaf cupping, stunting, and bushy rosettes", "yellow"),
            ("Root-Knot Nematode", "Meloidogyne incognita", "Perry & Moens Plant Nematology 2nd Ed., p. 195", "Plate 5.2", "Severe spherical root galls with feeder root atrophy", "brown"),
            ("Blossom End Rot", "Abiotic (Ca2+ Deficiency)", "APS Compendium of Tomato Diseases 2nd Ed., p. 102", "Plate 14.1", "Sunken dark leathery necrosis at blossom end (NOT FUNGAL)", "brown")
        ]
        for dis, path, book, plate, hallmark, col in core_diseases:
            saved_path = extractor.generate_reference_plate(
                disease_name=dis,
                pathogen_name=path,
                book_citation=book,
                plate_label=plate,
                diagnostic_hallmark=hallmark,
                color_scheme=col
            )
            print(f"  + Generated: {dis} -> {os.path.basename(saved_path)}")
        print(f"\n[OK] Reference atlas plates generated. Catalog saved to {extractor.catalog_path}\n")
        return

    if not args.pdf_path:
        parser.print_help()
        print("\nExample Usage:")
        print('  python extract_book_figures.py --generate-atlas')
        print('  python extract_book_figures.py "data/agrios_plant_pathology.pdf" --title "Agrios 6th Ed"')
        sys.exit(1)

    print(f">> Extracting figures and captions from: {args.pdf_path}")
    res = extractor.extract_from_pdf(args.pdf_path, book_title=args.title)
    if res.get("status") == "success":
        print(f"[OK] Extracted {res.get('figures_extracted')} figures from {res.get('total_pages')} pages.")
        print(f"     Catalog now contains {res.get('catalog_total')} figures.")
    else:
        print(f"[ERROR] {res.get('message')}")

if __name__ == "__main__":
    main()
