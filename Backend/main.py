from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import requests
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
import fitz  # PyMuPDF
import re
import io
import easyocr
from PIL import Image
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# CONFIG
# ==========================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "scb10x/llama3.2-typhoon2-1b-instruct:latest"

# Initialize OCR reader once (important for performance)
reader = easyocr.Reader(['th', 'en'], gpu=False)


# ==========================
# TEXT CLEANING
# ==========================

def clean_text(text: str) -> str:
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    text = re.sub(r'[^a-zA-Z0-9ก-๙\s\.\,\:\;\-\(\)]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ==========================
# OCR LOGIC
# ==========================

import numpy as np

def ocr_image(image: Image.Image) -> str:
    image_np = np.array(image)

    results = reader.readtext(
        image_np,
        detail=0,
        paragraph=True
    )

    text = " ".join(results)
    return clean_text(text)


def ocr_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    all_text = []

    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))
        text = ocr_image(image)
        if text:
            all_text.append(text)

    return "\n".join(all_text)


# ==========================
# OCR ENDPOINT
# ==========================

@app.post("/OCR")
async def ocr(file: UploadFile = File(...)):

    contents = await file.read()

    try:
        # ====== 1. OCR ======
        if file.content_type == "application/pdf":
            extracted_text = ocr_pdf(contents)

        elif file.content_type.startswith("image/"):
            image = Image.open(io.BytesIO(contents))
            extracted_text = ocr_image(image)

        else:
            return {"error": "Unsupported file type"}

        if not extracted_text:
            return {"error": "No text detected"}

        # ====== 2. Summarize ======
        prompt = f"""
You must ONLY use the information provided below.
Do NOT add outside knowledge.

Summarize the following content in bullet points in simple language:

=== CONTENT START ===
{extracted_text[:500]}
=== CONTENT END ===
"""

        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }

        res = requests.post(OLLAMA_URL, json=payload)
        res.raise_for_status()
        data = res.json()

        return {
            "summary": data["response"]
        }

    except Exception as e:
        return {"error": str(e)}


# ==========================
# SUMMARIZE ENDPOINT
# ==========================

@app.post("/summarize")
async def summarize(file: UploadFile = File(...)):

    contents = await file.read()
    pdf_stream = io.BytesIO(contents)

    reader_pdf = PdfReader(pdf_stream)

    all_text = []

    for page in reader_pdf.pages:
        text = page.extract_text()
        if text:
            cleaned = clean_text(text)
            all_text.append(cleaned)

    pdf_text = "\n".join(all_text)

    prompt = f"""
You must ONLY use the information provided below.
Do NOT add outside knowledge.
If the information is insufficient, say "Not enough information".

Summarize the following content in bullet points in simple language:

=== CONTENT START ===
{pdf_text[:2000]}
=== CONTENT END ===
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:
        res = requests.post(OLLAMA_URL, json=payload)
        res.raise_for_status()
        data = res.json()

        return {
            "summary": data["response"]
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": str(e)
        }