# streamlit_app.py
import streamlit as st
import json
import os
from pdf_parser import HybridPDFParser
from config import OUTPUT_DIR

st.set_page_config(layout="wide", page_title="Hybrid PDF Parser")

st.title("PDF Parser — Gives Structured JSON")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
col1, col2 = st.columns([1, 2])

if uploaded_file:
    tmp_path = os.path.join(OUTPUT_DIR, uploaded_file.name)
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    ocr_lang = ["eng"]  # Default OCR language

    if st.button("Parse PDF"):
        with st.spinner("Parsing..."):
            parser = HybridPDFParser(tmp_path, output_dir=OUTPUT_DIR, ocr_langs=ocr_lang)
            result = parser.parse()  # Let parser decide automatically

        if "error" in result:
            st.error(f"Parsing error: {result['error']}")
        else:
            st.success("Parsing complete")
            st.subheader("Parsed JSON (preview)")
            st.json(result)
            # Save JSON to outputs and provide download link
            out_path = parser.export_json(result)
            with open(out_path, "rb") as f:
                data = f.read()
            st.download_button("Download JSON", data, file_name=os.path.basename(out_path), mime="application/json")
            st.write("Assets saved to:", os.path.join(OUTPUT_DIR, parser.base_name + "_assets"))
            # show first images (if any)
            try:
                assets_dir = os.path.join(OUTPUT_DIR, parser.base_name + "_assets")
                imgs = [f for f in os.listdir(assets_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
                if imgs:
                    st.subheader("Extracted images (sample)")
                    for im in imgs[:6]:
                        st.image(os.path.join(assets_dir, im), caption=im, use_column_width=True)
            except Exception:
                pass
