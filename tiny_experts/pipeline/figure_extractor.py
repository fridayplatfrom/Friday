import os
import re
import json
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import io

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

class FigureExtractor:
    """
    Automated Textbook Figure & Diagnostic Plate Extractor.
    Extracts embedded photographic plates, microscopic diagrams, and symptom figures from PDF books,
    matches page captions ('Figure X', 'Plate Y', 'Fig. Z'), and catalogs them for visual reference.
    """

    CAPTION_PATTERNS = [
        re.compile(r"(?:Figure|Fig\.|Plate)\s+([0-9]+[A-Za-z0-9\.\-_]*)\s*[:\.]\s*([^\n\r]+)", re.IGNORECASE),
        re.compile(r"(?:Photo|Diagram)\s+([0-9]+[A-Za-z0-9\.\-_]*)\s*[:\.]\s*([^\n\r]+)", re.IGNORECASE)
    ]

    DISEASE_KEYWORDS = {
        "Early Blight": ["early blight", "alternaria solani", "concentric ring", "target spot", "bullseye"],
        "Late Blight": ["late blight", "phytophthora infestans", "water-soaked", "sporangia", "white mold"],
        "Powdery Mildew": ["powdery mildew", "podosphaera", "erysiphe", "white powder", "conidiophore"],
        "Downy Mildew": ["downy mildew", "pseudoperonospora", "downy felt", "sporangiophore"],
        "Bacterial Canker": ["bacterial canker", "clavibacter", "bird's eye", "stem canker"],
        "Bacterial Wilt": ["bacterial wilt", "ralstonia", "vascular browning", "bacterial stream"],
        "Citrus Canker": ["citrus canker", "xanthomonas citri", "corky lesion", "crater-like"],
        "Rice Bacterial Leaf Blight": ["bacterial leaf blight", "kresek", "xanthomonas oryzae", "wavy margin"],
        "Tomato Yellow Leaf Curl": ["tylcv", "yellow leaf curl", "begomovirus", "leaf cupping"],
        "Tobacco Mosaic Virus": ["tmv", "tobacco mosaic", "mottling", "mosaic pattern"],
        "Sugarcane Red Rot": ["red rot", "colletotrichum falcatum", "red discoloration", "white cross bands"],
        "Blossom End Rot": ["blossom end rot", "calcium deficiency", "water-soaked blossom", "black sunken leathery"],
        "Root-Knot Nematode": ["root-knot", "meloidogyne", "root gall", "nurse cells", "giant cells"]
    }

    def __init__(self, figures_dir: Optional[str] = None):
        if figures_dir is None:
            primary = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "sources", "books", "pathology", "figures"
            )
            legacy = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "books", "pathology", "figures"
            )
            self.figures_dir = primary if os.path.exists(primary) else legacy
        else:
            self.figures_dir = figures_dir
        os.makedirs(self.figures_dir, exist_ok=True)
        self.catalog_path = os.path.join(self.figures_dir, "figure_catalog.json")

    def load_catalog(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.catalog_path):
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_catalog(self, catalog: List[Dict[str, Any]]) -> None:
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

    def extract_from_pdf(self, pdf_path: str, book_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Parses a PDF file, extracts embedded images with associated figure captions,
        and logs them in the figure catalog.
        """
        if not HAS_PYPDF:
            return {"status": "error", "message": "pypdf library not available."}
        if not os.path.exists(pdf_path):
            return {"status": "error", "message": f"File not found: {pdf_path}"}

        source_title = book_title or os.path.basename(pdf_path)
        extracted_figures = []
        catalog = self.load_catalog()

        try:
            reader = pypdf.PdfReader(pdf_path)
            total_pages = len(reader.pages)

            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                # Find captions on the page
                captions_found = []
                for pat in self.CAPTION_PATTERNS:
                    for match in pat.finditer(page_text):
                        captions_found.append({
                            "figure_id": match.group(1).strip(),
                            "caption": match.group(2).strip()
                        })

                # Check embedded images
                images = getattr(page, "images", [])
                for img_idx, img_file in enumerate(images):
                    try:
                        img_bytes = img_file.data
                        img_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_p{page_idx+1}_img{img_idx+1}.png"
                        out_path = os.path.join(self.figures_dir, img_name)
                        
                        # Save image
                        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        pil_img.save(out_path, format="PNG")

                        # Match with caption if available
                        caption_text = ""
                        fig_num = f"Fig {page_idx+1}.{img_idx+1}"
                        if captions_found:
                            matched_cap = captions_found[min(img_idx, len(captions_found)-1)]
                            caption_text = matched_cap["caption"]
                            fig_num = f"Figure {matched_cap['figure_id']}"
                        else:
                            # Use nearby sentence as caption
                            lines = [line.strip() for line in page_text.splitlines() if len(line.strip()) > 20]
                            if lines:
                                caption_text = lines[0]

                        # Detect related disease
                        detected_disease = "Unclassified Pathology"
                        for dis, keywords in self.DISEASE_KEYWORDS.items():
                            if any(kw in (caption_text + " " + page_text).lower() for kw in keywords):
                                detected_disease = dis
                                break

                        fig_record = {
                            "id": f"fig_{len(catalog) + len(extracted_figures) + 1:04d}",
                            "book_title": source_title,
                            "page": page_idx + 1,
                            "figure_label": fig_num,
                            "caption": caption_text,
                            "disease": detected_disease,
                            "filename": img_name,
                            "relative_path": os.path.relpath(out_path, os.path.dirname(os.path.dirname(os.path.dirname(self.figures_dir)))),
                            "dimensions": f"{pil_img.width}x{pil_img.height}"
                        }
                        extracted_figures.append(fig_record)
                    except Exception as e:
                        continue

            # Update catalog
            catalog.extend(extracted_figures)
            self.save_catalog(catalog)

            return {
                "status": "success",
                "book_title": source_title,
                "total_pages": total_pages,
                "figures_extracted": len(extracted_figures),
                "catalog_total": len(catalog),
                "extracted_figures": extracted_figures
            }
        except Exception as e:
            return {"status": "error", "message": f"Extraction failed: {str(e)}"}

    def generate_reference_plate(
        self,
        disease_name: str,
        pathogen_name: str,
        book_citation: str,
        plate_label: str,
        diagnostic_hallmark: str,
        color_scheme: str = "green"
    ) -> str:
        """
        Generates a synthetic schematic; NOT a reproduced book figure, clinical image or verified citation.
        """
        width, height = 400, 400
        colors = {
            "green": ((30, 80, 40), (180, 220, 160)),
            "yellow": ((80, 70, 20), (240, 230, 160)),
            "brown": ((70, 40, 25), (210, 170, 140)),
            "white": ((60, 60, 70), (220, 220, 230)),
            "red": ((90, 25, 25), (230, 160, 160))
        }
        bg_col, fg_col = colors.get(color_scheme, ((40, 60, 40), (200, 220, 200)))

        img = Image.new("RGB", (width, height), color=bg_col)
        draw = ImageDraw.Draw(img)

        # Draw structural leaf outline and lesion zone
        draw.polygon([(200, 40), (340, 180), (280, 320), (200, 370), (120, 320), (60, 180)], outline=fg_col, width=3)
        draw.line([(200, 40), (200, 370)], fill=fg_col, width=2) # Central vein
        draw.line([(200, 140), (280, 190)], fill=fg_col, width=1)
        draw.line([(200, 220), (260, 270)], fill=fg_col, width=1)
        draw.line([(200, 140), (120, 190)], fill=fg_col, width=1)
        draw.line([(200, 220), (140, 270)], fill=fg_col, width=1)

        # Draw diagnostic lesion zone
        if "Blight" in disease_name or "target" in diagnostic_hallmark.lower():
            # Concentric rings
            for r in [45, 35, 25, 15, 6]:
                draw.ellipse([(180-r, 190-r), (180+r, 190+r)], outline=(220, 180, 50) if r == 45 else (40, 20, 10), width=2)
        elif "Mildew" in disease_name:
            # Powdery stippling
            for dx in range(-40, 40, 8):
                for dy in range(-40, 40, 8):
                    if (dx*dx + dy*dy) < 1400:
                        draw.point((200+dx, 190+dy), fill=(245, 245, 250))
        elif "Canker" in disease_name or "Spot" in disease_name:
            # Crateriform raised spot
            draw.ellipse([(170, 170), (230, 230)], outline=(255, 215, 0), width=3)
            draw.ellipse([(180, 180), (220, 220)], fill=(70, 35, 10), outline=(20, 10, 5), width=2)
        elif "Red Rot" in disease_name:
            # Internal red pith with white bands
            draw.rectangle([(170, 120), (230, 260)], fill=(160, 25, 25), outline=(240, 240, 240), width=2)
            draw.line([(170, 180), (230, 180)], fill=(255, 255, 255), width=4)
        else:
            # Necrotic patch
            draw.ellipse([(165, 165), (235, 225)], fill=(50, 30, 20), outline=(200, 160, 40), width=2)

        # Header Plate Banner
        draw.rectangle([(0, 0), (400, 32)], fill=(20, 25, 30))
        draw.text((10, 8), f"SCHEMATIC (NOT SOURCE ART) | {disease_name.upper()}", fill=(240, 240, 240))

        # Footer Textbook Citation Banner
        draw.rectangle([(0, 355), (400, 400)], fill=(15, 20, 25))
        draw.text((10, 360), f"Pathogen: {pathogen_name}", fill=(180, 220, 255))
        draw.text((10, 376), "Synthetic diagram. Not verified to any book.", fill=(170, 170, 170))

        # Save plate
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', disease_name.lower())
        filename = f"plate_{safe_name}.png"
        out_path = os.path.join(self.figures_dir, filename)
        img.save(out_path, format="PNG")

        # Update catalog
        catalog = self.load_catalog()
        # Avoid duplicate
        catalog = [c for c in catalog if c.get("disease") != disease_name]
        catalog.append({
            "id": f"plate_{safe_name}",
            "book_title": None,
            "page": None,
            "figure_label": "synthetic schematic",
            "legacy_attribution_unverified": {"claimed_book": book_citation, "claimed_plate": plate_label},
            "verification_status": "unverified",
            "review_status": "unreviewed",
            "image_type": "synthetic_illustration",
            "caption": f"{disease_name} - {diagnostic_hallmark}",
            "disease": disease_name,
            "filename": filename,
            "relative_path": os.path.join("tiny_experts", "data", "sources", "books", "pathology", "figures", filename),
            "dimensions": "400x400"
        })
        self.save_catalog(catalog)
        return out_path
