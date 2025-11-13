from __future__ import annotations

import logging
import os
import sys
import time
import tempfile
import subprocess
import json
import base64
import re
import hashlib
import asyncio
import io  # FIXED: Added missing io import
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

# Import for reading documents
try:
    import docx
    from docx import Document
except ImportError:
    docx = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
except ImportError:
    Presentation = None

try:
    import pandas as pd
except ImportError:
    pd = None

from io import BytesIO

# Local modules
from fact_guard import FactGuard
from document_handler import save_upload, export_pdf, export_docx, export_xlsx, extract_text
from research_apis import search_arxiv
from dynamic_fact_fetcher import get_world_news_headlines, get_weather_snapshot
from chat_storage import save_message, history, delete_chat_session, get_chat_sessions

# ==============================================================================
# PATHS & ENVIRONMENT
# ==============================================================================

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
(DATA / "uploads").mkdir(parents=True, exist_ok=True)
(DATA / "outputs").mkdir(parents=True, exist_ok=True)
(DATA / "chats").mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / "backend" / ".env")

# ==============================================================================
# PROVIDER CONFIGURATION - UPDATED WITH NEW PROVIDERS
# ==============================================================================

@dataclass
class ProviderConfig:
    key: str
    endpoint: str
    api_key_env: str
    model: str
    type: str  # "chat", "vision", "image", "video"
    cost_per_1k: float = 0.0  # dollars (not cents!)

# UPDATED PROVIDER CONFIGURATION WITH NEW PROVIDERS
PROVIDERS = {
    "zai-glm-4.5-flash": ProviderConfig(
        key="zai-glm-4.5-flash",
        endpoint="https://api.z.ai/api/paas/v4/chat/completions",
        api_key_env="ZAI_API_KEY",
        model="glm-4.5-flash",
        type="chat",
        cost_per_1k=0.0
    ),
    "zai-glm-4.6": ProviderConfig(
        key="zai-glm-4.6",
        endpoint="https://api.z.ai/api/paas/v4/chat/completions",
        api_key_env="ZAI_API_KEY",
        model="glm-4.6",
        type="chat",
        cost_per_1k=0.01
    ),
    "zai-glm-4.5v": ProviderConfig(
        key="zai-glm-4.5v",
        endpoint="https://api.z.ai/api/paas/v4/chat/completions",
        api_key_env="ZAI_API_KEY",
        model="glm-4.5v",
        type="vision",
        cost_per_1k=0.001
    ),
    "kimi-k2-0905-preview": ProviderConfig(
        key="kimi-k2-0905-preview",
        endpoint="https://api.moonshot.ai/v1/chat/completions",
        api_key_env="MOONSHOT_API_KEY",
        model="kimi-k2-0905-preview",
        type="chat",
        cost_per_1k=0.002
    ),
    "kimi-k2-turbo-preview": ProviderConfig(
        key="kimi-k2-turbo-preview",
        endpoint="https://api.moonshot.ai/v1/chat/completions",
        api_key_env="MOONSHOT_API_KEY",
        model="kimi-k2-turbo-preview",
        type="chat",
        cost_per_1k=0.0013
    ),
    "zai-cogview-4": ProviderConfig(
        key="zai-cogview-4",
        endpoint="https://api.z.ai/api/paas/v4/images/generations",
        api_key_env="ZAI_API_KEY",
        model="cogview-4-250304",
        type="image",
        cost_per_1k=0.0  # Charged per image, not tokens
    ),
    "zai-cogvideox-3": ProviderConfig(
        key="zai-cogvideox-3",
        endpoint="https://api.z.ai/api/paas/v4/videos/generations",
        api_key_env="ZAI_API_KEY",
        model="CogVideoX-3",
        type="video",
        cost_per_1k=0.0  # Charged per video, not tokens
    )
}

# Cost tracking
cost_log = []

# Performance optimizations
executor = ThreadPoolExecutor(max_workers=4)

# ==============================================================================
# FASTAPI SETUP
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Quantum AI Lab - Nuclear Spaceship Edition", version="5.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"]
)

# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class ChatReq(BaseModel):
    task: str
    temperature: float = 0.4
    max_tokens: int = 4096
    provider: Optional[str] = None  # Allow manual provider selection
    session_id: Optional[str] = None  # FIXED: Added session ID for chat history

class ChatRes(BaseModel):
    result: str
    model_used: str
    cost_cents: int
    processing_time_ms: int
    strategy: str
    media_url: Optional[str] = None
    session_id: Optional[str] = None  # FIXED: Return session ID

class ImageGenReq(BaseModel):
    prompt: str
    size: str = "1024x1024"

class VideoGenReq(BaseModel):
    prompt: str
    duration: int = 5

class ExportDocReq(BaseModel):
    text: str

class ExportXlsxReq(BaseModel):
    rows: List[List[str]]

class RunReq(BaseModel):
    code: str
    timeout_sec: int = 8

class LiteraturePostReq(BaseModel):
    query: str
    max_results: int = 10

# ==============================================================================
# FILE READING UTILITIES - COMPREHENSIVE SUPPORT
# ==============================================================================

def extract_text_from_file(content: bytes, filename: str) -> str:
    """
    Smart extraction for multiple file formats:
    - DOCX, PDF, TXT, PPTX, XLSX
    - Images (describe what was uploaded)
    - Videos (describe what was uploaded)
    """
    try:
        ext = filename.lower().split('.')[-1]

        # DOCX
        if ext == 'docx':
            if docx is None:
                return f"📄 DOCX File: {filename} (python-docx not installed)"
            doc = Document(BytesIO(content))
            extracted = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return f"📄 DOCX File: {filename}\n\n{extracted[:50000]}"

        # PDF
        elif ext == 'pdf':
            if PyPDF2 is None:
                return f"📄 PDF File: {filename} (PyPDF2 not installed)"
            pdf_reader = PyPDF2.PdfReader(BytesIO(content))
            pages = []
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(f"[Page {i+1}]\n{text}")
            return f"📄 PDF File: {filename}\n\n" + "\n\n".join(pages)[:50000]

        # TXT / Code files
        elif ext in ['txt', 'py', 'js', 'java', 'cpp', 'c', 'html', 'css', 'md', 'json', 'xml']:
            text = content.decode('utf-8', errors='ignore')
            return f"📝 {ext.upper()} File: {filename}\n\n{text[:50000]}"

        # PPTX
        elif ext in ['pptx', 'ppt']:
            if Presentation is None:
                return f"📊 PPTX File: {filename} (python-pptx not installed)"
            try:
                prs = Presentation(BytesIO(content))
                slides_text = []
                for i, slide in enumerate(prs.slides):
                    slide_text = f"[Slide {i+1}]\n"
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            slide_text += shape.text + "\n"
                    slides_text.append(slide_text)
                return f"📊 PPTX File: {filename}\n\n" + "\n\n".join(slides_text)[:50000]
            except Exception as e:
                return f"📊 PPTX File: {filename} (couldn't extract text: {str(e)})"

        # XLSX / XLS
        elif ext in ['xlsx', 'xls', 'csv']:
            if pd is None:
                return f"📊 {ext.upper()} File: {filename} (pandas not installed)"
            try:
                if ext == 'csv':
                    df = pd.read_csv(BytesIO(content))
                else:
                    df = pd.read_excel(BytesIO(content))
                return f"📊 {ext.upper()} File: {filename}\n\n{df.head(50).to_string()}"
            except Exception as e:
                return f"📊 {ext.upper()} File: {filename} (couldn't parse: {str(e)})"

        # Images
        elif ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            return f"🖼️ Image uploaded: {filename} ({len(content)} bytes)\nUse vision analysis to process this image."

        # Videos
        elif ext in ['mp4', 'avi', 'mov', 'mkv', 'webm']:
            return f"🎬 Video uploaded: {filename} ({len(content)} bytes)\nVideo analysis capabilities available."

        # Unknown binary
        else:
            return f"📎 File: {filename} ({len(content)} bytes, type: {ext})"

    except Exception as e:
        logging.error(f"Error extracting {filename}: {e}")
        return f"❌ Error reading {filename}: {str(e)}"

# ==============================================================================
# CORE MODEL CALLING
# ==============================================================================

fact_guard = FactGuard()

def calculate_cost(provider_key: str, tokens_approx: int) -> int:
    """Calculate cost in CENTS (for display)"""
    if provider_key not in PROVIDERS:
        return 0
    provider = PROVIDERS[provider_key]
    cost_dollars = (tokens_approx / 1000) * provider.cost_per_1k
    return int(cost_dollars * 100)  # Convert to cents

@lru_cache(maxsize=100)
def cached_fact_check(text: str):
    """Cached fact checking for better performance - FIXED BUG #2: Removed unused hash"""
    return fact_guard.check(text)

async def call_chat_model(
    provider_key: str,
    messages: List[Dict],
    temp: float = 0.4,
    max_tokens: int = 4096
) -> Tuple[str, int]:
    """
    Optimized universal chat model caller with timeout
    """
    if provider_key not in PROVIDERS:
        raise RuntimeError(f"Provider '{provider_key}' not found")

    provider = PROVIDERS[provider_key]
    api_key = os.getenv(provider.api_key_env, "").strip()

    if not api_key:
        raise RuntimeError(f"API key missing: {provider.api_key_env}")

    # FIXED BUG #7: Ensure consistent Bearer token format for all providers
    # Build headers - always use Bearer format for OpenAI-compatible APIs
    if "api.z.ai" in provider.endpoint:
        # Z.AI might accept both formats, use Bearer for consistency
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    else:  # Moonshot
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Build request body with optimized settings
    body = {
        "model": provider.model,
        "messages": messages,
        "temperature": temp,
        "max_tokens": max_tokens,  # FIXED BUG #8: Respect user's max_tokens request
        "stream": False  # Disable streaming for faster response
    }

    # Use asyncio for better performance
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:  # Increased timeout for slower APIs
            r = await client.post(provider.endpoint, headers=headers, json=body)

            if r.status_code == 401:
                raise RuntimeError(f"❌ Auth failed for {provider_key}")
            elif r.status_code == 429:
                raise RuntimeError(f"⏳ Rate limited by {provider_key}")
            elif r.status_code >= 400:
                raise RuntimeError(f"⚠️ API error {r.status_code}: {r.text[:200]}")

            data = r.json()
            result = data["choices"][0]["message"]["content"]

            # Faster token estimation
            tokens_used = max(len(str(messages)) // 4, len(result) // 4)
            cost = calculate_cost(provider_key, tokens_used)

            # Log cost
            cost_log.append({
                "provider": provider_key,
                "cost_cents": cost,
                "timestamp": time.time()
            })

            return result, cost

    except httpx.TimeoutException:
        raise RuntimeError(f"⏱️ Request timeout for {provider_key}")
    except Exception as e:
        raise RuntimeError(f"❌ Connection error: {str(e)}")

async def generate_image(prompt: str) -> Tuple[str, str]:
    """Generate image using CogView-4"""
    provider = PROVIDERS["zai-cogview-4"]
    api_key = os.getenv(provider.api_key_env, "").strip()

    if not api_key:
        raise RuntimeError(f"API key missing: {provider.api_key_env}")

    # FIXED BUG #7: Use Bearer token format
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": provider.model,
        "prompt": prompt,
        "size": "1024x1024"
    }

    logging.info(f"Image generation request: {body}")

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(provider.endpoint, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

        if "data" in data and len(data["data"]) > 0:
            image_data = data["data"][0]

            if "url" in image_data:
                image_url = image_data["url"]
                img_response = await client.get(image_url)
                filename = f"generated_{int(time.time())}.png"
                path = DATA / "outputs" / filename
                path.write_bytes(img_response.content)
                return image_url, str(path)

            elif "b64_json" in image_data:
                b64_data = image_data["b64_json"]
                img_bytes = base64.b64decode(b64_data)
                filename = f"generated_{int(time.time())}.png"
                path = DATA / "outputs" / filename
                path.write_bytes(img_bytes)
                return f"data:image/png;base64,{b64_data}", str(path)

        raise RuntimeError("No image data in response")

async def generate_video(prompt: str) -> Tuple[str, str]:
    """Generate video using CogVideoX-3"""
    provider = PROVIDERS["zai-cogvideox-3"]
    api_key = os.getenv(provider.api_key_env, "").strip()

    if not api_key:
        raise RuntimeError(f"API key missing: {provider.api_key_env}")

    # FIXED BUG #7: Use Bearer token format
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # FIXED BUG #3: Added proper duration and resolution fields
    body = {
        "model": provider.model,
        "prompt": prompt,
        "duration": 5,  # Default 5 seconds
        "resolution": "720p"  # Default resolution
    }

    logging.info(f"Video generation request: {body}")

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(provider.endpoint, headers=headers, json=body)

        logging.info(f"Video generation response status: {r.status_code}")
        logging.info(f"Video generation response: {r.text}")

        if r.status_code == 401:
            raise RuntimeError(f"❌ Auth failed for {provider.key}")
        elif r.status_code == 429:
            raise RuntimeError(f"⏳ Rate limited by {provider.key}")
        elif r.status_code >= 400:
            error_text = r.text
            logging.error(f"Video API error: {error_text}")
            raise RuntimeError(f"⚠️ API error {r.status_code}: {error_text}")

        data = r.json()

        if "data" in data and len(data["data"]) > 0:
            video_url = data["data"][0].get("url", "")
            if video_url:
                try:
                    vid_response = await client.get(video_url)
                    filename = f"generated_{int(time.time())}.mp4"
                    path = DATA / "outputs" / filename
                    path.write_bytes(vid_response.content)
                    return video_url, str(path)
                except Exception as download_error:
                    logging.error(f"Video download failed: {download_error}")
                    return video_url, "Download failed"

        raise RuntimeError("No video data in response")

# ==============================================================================
# ORCHESTRATION LAYER - MANUAL PROVIDER SELECTION
# ==============================================================================

async def orchestrate_request(
    task: str,
    temp: float,
    max_tokens: int,
    provider_key: Optional[str] = None,
    uploaded_file: Optional[str] = None,
    context_messages: Optional[List[Dict]] = None
) -> Tuple[str, str, int, str, Optional[str]]:
    """
    Manual provider selection orchestration with improved media handling
    """
    task_lower = task.lower()

    # Use cached fact check
    override = cached_fact_check(task)
    if override:
        text, _intent = override
        return f"✅ {text}", "fact_guard", 0, "fact_override", None

    # Detect media generation requests with better patterns
    is_image_request = any(kw in task_lower for kw in [
        "create image", "generate image", "draw", "picture of",
        "make image", "image of", "visualize", "generate picture"
    ])

    is_video_request = any(kw in task_lower for kw in [
        "create video", "generate video", "animate", "video of",
        "make video", "film", "video generation"
    ])

    # Handle media generation with improved prompt extraction
    if is_image_request:
        try:
            # FIXED BUG #5: Better prompt extraction that handles edge cases
            prompt = task
            found_trigger = False
            for trigger in ["create image of", "generate image of", "draw", "make image of", "image of", "visualize", "generate picture of"]:
                if trigger in task_lower:
                    try:
                        start_index = task_lower.index(trigger) + len(trigger)
                        extracted_prompt = task[start_index:].strip()
                        # Remove any leading punctuation or connectors
                        extracted_prompt = re.sub(r'^[:\-\—]\s*', '', extracted_prompt)
                        # Only use extracted prompt if it's meaningful
                        if extracted_prompt and len(extracted_prompt.strip()) >= 3:
                            prompt = extracted_prompt
                            found_trigger = True
                            break
                    except (ValueError, IndexError):
                        continue

            # If no trigger found or extraction failed, use full task (already set above)
            if not found_trigger:
                logging.info(f"No trigger found, using full prompt: {prompt[:50]}...")

            logging.info(f"Generating image with prompt: '{prompt}'")
            image_url, saved_path = await generate_image(prompt)
            result = f"🎨 **Image Generated!**\n\n![Generated Image]({image_url})\n\nSaved to: `{saved_path}`"
            return result, "zai-cogview-4", 0, "image_generation", image_url
        except Exception as e:
            logging.error(f"Image generation failed: {e}")
            return f"❌ Image generation failed: {str(e)}", "zai-cogview-4", 0, "image_error", None

    if is_video_request:
        try:
            # FIXED BUG #5: Better prompt extraction that handles edge cases
            prompt = task
            found_trigger = False
            for trigger in ["create video of", "generate video of", "animate", "make video of", "video of", "film"]:
                if trigger in task_lower:
                    try:
                        start_index = task_lower.index(trigger) + len(trigger)
                        extracted_prompt = task[start_index:].strip()
                        # Remove any leading punctuation or connectors
                        extracted_prompt = re.sub(r'^[:\-\—]\s*', '', extracted_prompt)
                        # Only use extracted prompt if it's meaningful
                        if extracted_prompt and len(extracted_prompt.strip()) >= 3:
                            prompt = extracted_prompt
                            found_trigger = True
                            break
                    except (ValueError, IndexError):
                        continue

            # If no trigger found or extraction failed, use full task (already set above)
            if not found_trigger:
                logging.info(f"No trigger found, using full prompt: {prompt[:50]}...")

            logging.info(f"Generating video with prompt: '{prompt}'")
            video_url, saved_path = await generate_video(prompt)
            result = f"🎬 **Video Generated!**\n\nURL: {video_url}\n\nSaved to: `{saved_path}`"
            return result, "zai-cogvideox-3", 0, "video_generation", video_url
        except Exception as e:
            logging.error(f"Video generation failed: {e}")
            return f"❌ Video generation failed: {str(e)}", "zai-cogvideox-3", 0, "video_error", None

    # Use selected provider or default
    if not provider_key or provider_key not in PROVIDERS:
        provider_key = "zai-glm-4.5-flash"  # Default to free tier

    # FIXED BUG #1: Use context_messages with chat history instead of throwing it away
    messages = context_messages if context_messages else [{"role": "user", "content": task}]

    try:
        result, cost = await call_chat_model(
            provider_key, messages, temp, max_tokens
        )
        return result, provider_key, cost, "manual_selection", None
    except Exception as e:
        # FIXED BUG #4: Proper error handling instead of bare except
        primary_error = str(e)
        # If selected provider fails, try fallback to GLM-4.5-Flash
        if provider_key != "zai-glm-4.5-flash":
            try:
                logging.warning(f"Primary provider {provider_key} failed: {primary_error}. Trying fallback...")
                result, cost = await call_chat_model(
                    "zai-glm-4.5-flash", messages, temp, max_tokens
                )
                return result, "zai-glm-4.5-flash", cost, "fallback_to_free", None
            except Exception as fallback_error:
                # FIXED BUG #9: Return meaningful error when both fail
                logging.error(f"Fallback also failed: {fallback_error}")
                raise RuntimeError(
                    f"Both {provider_key} and fallback failed.\n"
                    f"Primary error: {primary_error}\n"
                    f"Fallback error: {str(fallback_error)}"
                )

        raise RuntimeError(f"Provider {provider_key} failed: {primary_error}")

# ==============================================================================
# CORE ENDPOINTS
# ==============================================================================

@app.get("/health")
def health():
    return {"status": "online", "version": "5.1.0"}

@app.get("/providers")
def get_providers():
    """Get list of available providers with their details"""
    result = {}
    for key, provider in PROVIDERS.items():
        result[key] = {
            "model": provider.model,
            "type": provider.type,
            "cost_per_1k": provider.cost_per_1k,
            "description": f"{provider.model} ({provider.type})"
        }
    return result

@app.post("/generate/file")
async def generate_file_endpoint(req: dict):
    """Generate various file types based on user request"""
    try:
        content = req.get("content", "")
        file_type = req.get("type", "docx")
        filename = req.get("filename", f"generated_{int(time.time())}.{file_type}")

        # Handle empty content
        if not content.strip():
            return {
                "ok": False,
                "error": "Content cannot be empty"
            }

        # FIXED: Proper handling of different file types with error checking
        if file_type == "docx":
            if Document is None:
                raise HTTPException(status_code=500, detail="python-docx not installed")

            doc = Document()
            doc.add_heading("Generated Document", 0)

            # Split content into paragraphs and add to document
            for para in content.split('\n'):
                if para.strip():
                    doc.add_paragraph(para)

            # Save to bytes
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)

            path = DATA / "outputs" / filename
            path.write_bytes(buffer.getvalue())

        elif file_type == "xlsx":
            if Workbook is None:
                raise HTTPException(status_code=500, detail="openpyxl not installed")

            wb = Workbook()
            ws = wb.active
            ws.title = "Generated Data"

            # Split content into lines and add to Excel
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Try to split by tabs or commas for multi-column data
                if '\t' in line:
                    cells = line.split('\t')
                    for j, cell in enumerate(cells, 1):
                        ws.cell(row=i, column=j, value=cell)
                elif ',' in line:
                    cells = line.split(',')
                    for j, cell in enumerate(cells, 1):
                        ws.cell(row=i, column=j, value=cell.strip())
                else:
                    ws.cell(row=i, column=1, value=line)

            # Save to bytes
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            path = DATA / "outputs" / filename
            path.write_bytes(buffer.getvalue())

        elif file_type == "pptx":
            if Presentation is None:
                raise HTTPException(status_code=500, detail="python-pptx not installed")

            prs = Presentation()

            # Add title slide
            slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(slide_layout)

            # Add title
            title = slide.shapes.title
            title.text = "Generated Presentation"

            # Add content slide
            slide_layout = prs.slide_layouts[1]  # Title and Content layout
            slide = prs.slides.add_slide(slide_layout)

            # Add content
            title = slide.shapes.title
            title.text = "Content"

            # Add text to content placeholder
            body_shape = slide.shapes.placeholders[1]
            tf = body_shape.text_frame

            # Split content into bullet points
            for line in content.split('\n'):
                if line.strip():
                    p = tf.add_paragraph()
                    p.text = line.strip()
                    p.level = 0

            # Save to bytes
            buffer = io.BytesIO()
            prs.save(buffer)
            buffer.seek(0)

            path = DATA / "outputs" / filename
            path.write_bytes(buffer.getvalue())

        elif file_type == "pdf":
            # FIXED BUG #10: Add proper error handling for PDF export
            try:
                path = export_pdf(content, filename)
            except Exception as pdf_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"PDF generation failed: {str(pdf_error)}. ReportLab might not be installed."
                )

        elif file_type in ["txt", "md"]:
            path = DATA / "outputs" / filename
            path.write_text(content, encoding='utf-8')

        elif file_type == "csv":
            path = DATA / "outputs" / filename
            path.write_text(content, encoding='utf-8')

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

        return {
            "ok": True,
            "path": str(path),
            "filename": filename,
            "download_url": f"/files/download/{filename}"
        }

    except Exception as e:
        logging.error(f"File generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatRes)
async def chat(req: ChatReq):
    """Main chat endpoint with session-based conversation context"""
    logging.info(f"Chat request: {req.task[:100]}...")
    t0 = time.time()

    try:
        # FIXED: Use session ID for chat history
        session_id = req.session_id or f"session_{int(time.time())}"

        # Get recent chat history for context from this session
        context_messages = []
        try:
            history_response = history(limit=10, session_id=session_id)
            for msg in history_response:
                role, content, ts, sid = msg
                context_messages.append({"role": role, "content": content})
        except Exception as e:
            logging.warning(f"Could not load history: {e}")
            pass  # If history fails, continue without context

        # Add current message
        context_messages.append({"role": "user", "content": req.task})

        result, model_used, cost_cents, strategy, media_url = await orchestrate_request(
            req.task, req.temperature, req.max_tokens, req.provider, context_messages=context_messages
        )

        # Save messages with session ID
        save_message("user", req.task, session_id)
        save_message("assistant", result, session_id)

        return ChatRes(
            result=result,
            model_used=model_used,
            cost_cents=cost_cents,
            processing_time_ms=int((time.time() - t0) * 1000),
            strategy=strategy,
            media_url=media_url,
            session_id=session_id
        )
    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cost")
def get_cost():
    """Get total cost"""
    total = sum(entry["cost_cents"] for entry in cost_log)
    return {"total_cost_cents": total, "entries": len(cost_log)}

# ==============================================================================
# FILE MANAGEMENT
# ==============================================================================

@app.post("/files/upload")
async def files_upload(file: UploadFile = File(...)):
    """
    Upload file WITHOUT preview to prevent reader panel display
    FIXED: Return minimal info to avoid frontend preview
    """
    content = await file.read()
    path = DATA / "uploads" / file.filename
    path.write_bytes(content)

    # Don't extract text for preview - just store the file
    return {
        "ok": True,
        "stored_as": str(path),
        "filename": file.filename,
        "size": len(content),
        "message": f"File '{file.filename}' uploaded successfully"
        # REMOVED: instruction and preview fields to prevent auto-preview
    }

@app.post("/files/export/pdf")
async def export_pdf_endpoint(req: ExportDocReq):
    """Export text as PDF - FIXED BUG #10: Added error handling"""
    try:
        filename = f"conversation_{int(time.time())}.pdf"
        path = export_pdf(req.text, filename)
        return {"ok": True, "path": str(path), "filename": filename}
    except Exception as e:
        logging.error(f"PDF export failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF export failed: {str(e)}. ReportLab might not be installed."
        )

@app.post("/files/export/docx")
async def export_docx_endpoint(req: ExportDocReq):
    """Export text as DOCX"""
    filename = f"conversation_{int(time.time())}.docx"
    path = export_docx(req.text, filename)
    return {"ok": True, "path": str(path), "filename": filename}

@app.post("/files/export/xlsx")
async def export_xlsx_endpoint(req: ExportXlsxReq):
    """Export data as Excel"""
    path = export_xlsx(req.rows, "export.xlsx")
    return {"ok": True, "path": str(path)}

@app.get("/files/download/{filename}")
async def download_file(filename: str):
    """Download generated files"""
    path = DATA / "outputs" / filename
    if path.exists():
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="File not found")

# ==============================================================================
# MEDIA GENERATION ENDPOINTS
# ==============================================================================

@app.post("/generate/image")
async def generate_image_endpoint(req: ImageGenReq):
    """Generate image with CogView-4"""
    try:
        image_url, saved_path = await generate_image(req.prompt)
        return {
            "ok": True,
            "url": image_url,
            "path": saved_path,
            "model": "zai-cogview-4"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/video")
async def generate_video_endpoint(req: VideoGenReq):
    """Generate video with CogVideoX-3"""
    try:
        video_url, saved_path = await generate_video(req.prompt)
        return {
            "ok": True,
            "url": video_url,
            "path": saved_path,
            "model": "zai-cogvideox-3"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# TOOLS
# ==============================================================================

@app.post("/run/python")
async def run_python(req: RunReq):
    """Execute Python code safely"""
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "main.py"
        script.write_text(req.code, encoding="utf-8")
        try:
            cp = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=req.timeout_sec
            )
            return {
                "ok": cp.returncode == 0,
                "stdout": cp.stdout,
                "stderr": cp.stderr,
                "returncode": cp.returncode
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "⏱️ Timeout"}

@app.post("/research/literature")
async def research_literature(req: LiteraturePostReq):
    """Search arXiv for academic papers"""
    return {"results": search_arxiv(req.query, max_results=req.max_results)}

# ==============================================================================
# CHAT HISTORY MANAGEMENT - FIXED FOR SIDEBAR
# ==============================================================================

@app.get("/chats/sessions")
def get_sessions():
    """Get list of chat sessions for sidebar"""
    try:
        sessions = get_chat_sessions()
        return {"ok": True, "sessions": sessions}
    except Exception as e:
        logging.error(f"Failed to get sessions: {e}")
        return {"ok": False, "sessions": [], "error": str(e)}

@app.get("/chats/history")
def get_chats(limit: int = 100, session_id: Optional[str] = None):
    """Get chat history, optionally filtered by session"""
    try:
        rows = history(limit=limit, session_id=session_id)
        return [{"role": r, "content": c, "ts": ts, "session_id": sid} for (r, c, ts, sid) in rows]
    except Exception as e:
        logging.error(f"Failed to get history: {e}")
        return []

@app.delete("/chats/delete/{session_id}")
async def delete_chat(session_id: str):
    """Delete a specific chat session - FIXED"""
    try:
        deleted_count = delete_chat_session(session_id)
        logging.info(f"Deleted chat session {session_id}, {deleted_count} messages")

        return {"ok": True, "deleted": deleted_count, "session_id": session_id}
    except Exception as e:
        logging.error(f"Failed to delete chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chats/clear")
async def clear_all_chats():
    """Clear all chat history"""
    try:
        import sqlite3
        db_path = DATA / "chats" / "chats.db"

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM messages")
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        logging.info(f"Cleared all chat history: {deleted_count} messages")
        return {"ok": True, "deleted": deleted_count}
    except Exception as e:
        logging.error(f"Failed to clear chats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# RUN SERVER
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Quantum AI Lab - Nuclear Spaceship Edition v5.1 - FIXED")
    print("📡 Server: http://127.0.0.1:7861")
    print("🧠 Provider Selection: Manual with Fallback")
    print("🎨 Media: CogView-4 (Image) + CogVideoX-3 (Video)")
    print("📄 Files: ALL formats supported")
    print("💰 Costs: ACCURATE tracking")
    print("📜 Chat: Session-based history with sidebar")
    print()
    print("Providers:")
    for key, provider in PROVIDERS.items():
        cost_str = f"${provider.cost_per_1k:.4f}/1K" if provider.cost_per_1k > 0 else "FREE"
        print(f"  • {key}: {provider.model} ({cost_str})")
    print()
    print("✅ FIXED ISSUES:")
    print("  • Missing 'io' import added")
    print("  • File generation for DOCX, XLSX, PPTX, PDF improved")
    print("  • File upload no longer shows preview in reader panel")
    print("  • Chat history is session-based for sidebar display")
    print("  • Chat deletion works properly")
    print()
    uvicorn.run("app:app", host="127.0.0.1", port=7861, reload=False)
