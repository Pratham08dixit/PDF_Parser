from img2table.document import Image as Img2TableImage
# pdf_parser.py
"""
Hybrid PDF parser:
- Rule-based extraction for text & tables (pdfplumber, camelot, fitz)
- OCR pass for scanned PDFs (pytesseract, easyocr)
- LLM fallback for complex docs (placeholder function)
- Produces hierarchical JSON per requirements
"""

import os
import json
from typing import List, Dict, Any, Optional
from collections import defaultdict

import pdfplumber
import fitz  # PyMuPDF
import camelot
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd

from utils import detect_language, pil_image_to_text, save_bytes_to_file
from config import OUTPUT_DIR, LLM_PROVIDER

# ---------- Helpers ----------
def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def _simple_text_clean(s: str) -> str:
    return " ".join(line.strip() for line in s.splitlines() if line.strip())

# ---------- Core Parser Class ----------
class HybridPDFParser:
    def __init__(self, pdf_path: str, output_dir: str = OUTPUT_DIR, ocr_langs: List[str] = ["eng"]):
        self.pdf_path = pdf_path
        self.output_dir = _ensure_dir(output_dir)
        self.ocr_langs = ocr_langs
        self.base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        self.assets_dir = _ensure_dir(os.path.join(self.output_dir, self.base_name + "_assets"))

    # ---------- Detection ----------
    def is_scanned_pdf(self, sample_pages=2) -> bool:
        """Detect scanned PDF by checking if pdfplumber returns little/no text on first pages."""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                non_empty = 0
                pages_to_check = min(sample_pages, len(pdf.pages))
                for i in range(pages_to_check):
                    text = pdf.pages[i].extract_text() or ""
                    if len(text.strip()) > 50:
                        non_empty += 1
                # if none or only a tiny fraction have text, assume scanned
                return non_empty == 0
        except Exception:
            # fallback: use PyMuPDF text extraction
            doc = fitz.open(self.pdf_path)
            text_count = 0
            for i in range(min(sample_pages, len(doc))):
                text = doc[i].get_text("text") or ""
                if len(text.strip()) > 50:
                    text_count += 1
            doc.close()
            return text_count == 0

    # ---------- Rule-based extraction ----------

    def rule_based_extract(self) -> Dict[str, Any]:
        pages_json = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                page_obj = {"page_number": i, "content": []}
                # text
                raw_text = page.extract_text() or ""
                text = _simple_text_clean(raw_text)
                if text:
                    paragraphs = [p for p in text.split("\n\n") if p.strip()]
                    for p in paragraphs:
                        page_obj["content"].append({
                            "type": "paragraph",
                            "section": None,
                            "sub_section": None,
                            "text": p.strip()
                        })
                # tables using pdfplumber
                pdfplumber_tables = []
                try:
                    tables = page.extract_tables()
                    for t in tables:
                        if t:
                            pdfplumber_tables.append(t)
                            page_obj["content"].append({
                                "type": "table",
                                "section": None,
                                "description": "Extracted by pdfplumber",
                                "table_data": t
                            })
                except Exception:
                    pass

                # tables using camelot for this page
                try:
                    camelot_tables = camelot.read_pdf(self.pdf_path, pages=str(i))
                    for t in camelot_tables:
                        # Avoid duplicate tables by comparing with pdfplumber tables
                        table_data = t.df.values.tolist()
                        if table_data not in pdfplumber_tables:
                            page_obj["content"].append({
                                "type": "table",
                                "section": None,
                                "description": "Extracted by camelot",
                                "table_data": table_data
                            })
                except Exception:
                    pass

                pages_json.append(page_obj)

        # Extract images using PyMuPDF
        imgs = self.extract_images()
        for img_meta in imgs:
            pnum = img_meta["page"]
            fname = os.path.basename(img_meta["path"]).lower()
            img_path = img_meta["path"]
            img2table_img = Img2TableImage(img_path)
            # Try to extract tables from image (without TesseractOCR)
            table_result = img2table_img.extract_tables(implicit_rows=True)
            if table_result and table_result.get("tables"):
                for tbl in table_result["tables"]:
                    pages_json[pnum - 1]["content"].append({
                        "type": "table",
                        "section": None,
                        "description": "Extracted from image using img2table",
                        "table_data": tbl["values"]
                    })
            # If not a table, treat as chart if filename matches
            img_type = "image"
            if any(x in fname for x in ["chart", "graph", "plot"]):
                img_type = "chart"
            pages_json[pnum - 1]["content"].append({
                "type": img_type,
                "section": None,
                "description": img_meta.get("description"),
                "image_path": img_path
            })

        return {"pages": pages_json}

    def extract_images(self) -> List[Dict[str, Any]]:
        """Extract images from PDF pages (PyMuPDF) and write to assets dir."""
        results = []
        doc = fitz.open(self.pdf_path)
        for i in range(len(doc)):
            page = doc[i]
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image.get("ext", "png")
                image_name = f"page_{i+1}_img_{img_index}.{ext}"
                path = os.path.join(self.assets_dir, image_name)
                save_bytes_to_file(image_bytes, path)
                results.append({"page": i+1, "path": path, "description": None})
        doc.close()
        return results

    # ---------- OCR path ----------
    def ocr_extract(self) -> Dict[str, Any]:
        """
        Convert each page to image (pdf2image) and OCR using pytesseract / easyocr.
        Returns pages JSON similar structure.
        """
        pages_json = []
        pil_pages = convert_from_path(self.pdf_path)
        for i, pil_img in enumerate(pil_pages, start=1):
            page_obj = {"page_number": i, "content": []}
            # full-page OCR (use first language available)
            ocr_text = None
            for lang in self.ocr_langs:
                try:
                    ocr_text = pil_image_to_text(pil_img, lang=lang)
                except Exception:
                    ocr_text = pil_image_to_text(pil_img)
                if ocr_text and len(ocr_text.strip()) > 10:
                    break
            if ocr_text:
                txt = _simple_text_clean(ocr_text)
                paragraphs = [p for p in txt.split("\n\n") if p.strip()]
                for p in paragraphs:
                    page_obj["content"].append({
                        "type": "paragraph",
                        "section": None,
                        "sub_section": None,
                        "text": p.strip()
                    })
            # save page image asset
            img_path = os.path.join(self.assets_dir, f"page_{i}.png")
            pil_img.save(img_path)
            page_obj["content"].append({
                "type": "image",
                "section": None,
                "description": "page_snapshot",
                "image_path": img_path
            })
            pages_json.append(page_obj)
        return {"pages": pages_json}

    # ---------- LLM Fallback ----------
    def call_gemini_for_structure(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM (Gemini/OpenAI) to refine raw extracted content into hierarchical JSON.
        """
        from llm_client import call_llm_for_json

        # Load prompts
        with open("prompts/system.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        with open("prompts/reasoning.txt", "r", encoding="utf-8") as f:
            reasoning_prompt = f.read()

        # Prepare user content (compact)
        user_content = json.dumps(raw_payload, ensure_ascii=False, indent=2)

        # Call LLM
        structured = call_llm_for_json(system_prompt, reasoning_prompt, user_content)
        return structured


    # ---------- Main orchestrator ----------

    def parse(self) -> Dict[str, Any]:
        """Main entry point. Returns final JSON structure."""
        try:
            scanned = self.is_scanned_pdf()
            if scanned:
                # If scanned, use OCR only
                return self.ocr_extract()
            else:
                # Always try rule-based extraction first
                parsed = self.rule_based_extract()

                # Check if rule-based extraction missed key content
                pages = parsed.get("pages", [])
                has_text = any(
                    any(c["type"] == "paragraph" and c.get("text") for c in p["content"]) for p in pages
                )
                has_table = any(
                    any(c["type"] == "table" and c.get("table_data") for c in p["content"]) for p in pages
                )
                has_image = any(
                    any(c["type"] == "image" and c.get("image_path") for c in p["content"]) for p in pages
                )

                # If any key content is missing, use LLM fallback
                if not (has_text and has_table and has_image):
                    payload = {"pages": parsed["pages"], "assets_dir": self.assets_dir}
                    try:
                        structured = self.call_gemini_for_structure(payload)
                        if structured:
                            return structured
                    except Exception:
                        pass
                return parsed
        except Exception as e:
            return {"error": str(e)}

    # ---------- Utilities ----------
    def export_json(self, json_obj: Dict[str, Any], out_name: Optional[str] = None) -> str:
        if not out_name:
            out_name = f"{self.base_name}_parsed.json"
        path = os.path.join(self.output_dir, out_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=2)
        return path
