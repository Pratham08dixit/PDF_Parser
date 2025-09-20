# utils.py
import io
import os
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

from PIL import Image

import easyocr

def detect_language(text: str):
    try:
        return detect(text)
    except Exception:
        return "unknown"

def pil_image_to_text(img: Image.Image, lang="eng"):
    """
    OCR a PIL image with easyocr. `lang` should correspond to installed easyocr lang packs.
    """
    reader = easyocr.Reader([lang])
    result = reader.readtext(np.array(img), detail=0)
    return "\n".join(result)

def save_bytes_to_file(b: bytes, path: str):
    with open(path, "wb") as f:
        f.write(b)
    return path
