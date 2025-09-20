# Hybrid PDF Parser

This project is a Streamlit-based app for parsing PDFs using a hybrid approach:
- **Rule-based extraction**: Extracts text, tables, and images using pdfplumber, camelot, and PyMuPDF.
- **OCR for scanned PDFs**: Uses EasyOCR to extract text from scanned pages.
- **Chart/Table extraction from images**: Uses img2table to extract tables and chart-like data from images.
- **LLM fallback**: Optionally uses Gemini to structure output as hierarchical JSON if rule-based extraction is incomplete.

## Features
- Automatic detection of scanned PDFs and use of OCR.
- Robust extraction of tables, charts, and images.
- Outputs hierarchical JSON with document structure.
- Streamlit UI for easy PDF upload and result download.

## Requirements
- Python 3.8+
- All dependencies listed in `requirements.txt` (see below for install commands)
- [Tesseract](https://github.com/tesseract-ocr/tesseract/wiki) (optional, only if you use Tesseract-based OCR)

## Installation
1. Clone the repository:
   ```
   git clone <your-repo-url>
   cd pdf_parser
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   pip install opencv-contrib-python
   ```
3. (Optional) Install Tesseract if you want to use Tesseract-based OCR.

## Usage
1. Start the Streamlit app:
   ```
   streamlit run app.py
   ```
2. Upload a PDF and view/download the parsed JSON output.

## File Structure
- `app.py` — Streamlit app entry point
- `pdf_parser.py` — Main parser logic
- `utils.py` — Utility functions (OCR, language detection, etc.)
- `llm_client.py` — LLM API client
- `config.py` — Configuration
- `requirements.txt` — Python dependencies
- `outputs/` — Output files and assets
- `prompts/` — LLM prompt templates


