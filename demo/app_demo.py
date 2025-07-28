"""
Whisper MOWD Demo API
Simplified version for zero-cost deployment and market validation
"""

import os
import json
import sqlite3
import asyncio
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Try to import faster-whisper, fall back to openai-whisper
try:
    from faster_whisper import WhisperModel
    USING_FASTER_WHISPER = True
except ImportError:
    import whisper
    USING_FASTER_WHISPER = False

# Configuration
UPLOAD_DIR = Path("uploads")
DB_PATH = Path("demo.db")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DURATION_SECONDS = 300  # 5 minutes
MAX_UPLOADS_PER_IP = 10
CLEANUP_AFTER_HOURS = 24
WHISPER_MODEL = "tiny"  # Use tiny for demo (39MB)
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "whisper2025")

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)

# Initialize database
def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            ip_address TEXT,
            filename TEXT,
            file_size INTEGER,
            status TEXT,
            progress INTEGER DEFAULT 0,
            result_text TEXT,
            error TEXT,
            created_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            date TEXT,
            upload_count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# Whisper model (global to avoid reloading)
whisper_model = None

def load_whisper_model():
    """Load Whisper model once"""
    global whisper_model
    if whisper_model is None:
        print(f"Loading Whisper model: {WHISPER_MODEL}")
        if USING_FASTER_WHISPER:
            whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        else:
            whisper_model = whisper.load_model(WHISPER_MODEL)
        print("Model loaded successfully")
    return whisper_model

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    load_whisper_model()
    # Start cleanup task
    asyncio.create_task(cleanup_old_files())
    yield
    # Shutdown
    pass

# Create FastAPI app
app = FastAPI(
    title="Whisper MOWD Demo",
    description="Free audio transcription demo",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Simple auth check
async def check_demo_auth(request: Request):
    """Check if user has demo password in cookie"""
    demo_auth = request.cookies.get("demo_auth")
    if demo_auth != hashlib.sha256(DEMO_PASSWORD.encode()).hexdigest():
        raise HTTPException(status_code=401, detail="Demo authentication required")
    return True

# Rate limiting
async def check_rate_limit(request: Request):
    """Check if IP has exceeded daily limit"""
    client_ip = request.client.host
    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get or create usage record
    c.execute("""
        SELECT upload_count FROM usage_stats 
        WHERE ip_address = ? AND date = ?
    """, (client_ip, today))
    
    result = c.fetchone()
    if result and result[0] >= MAX_UPLOADS_PER_IP:
        conn.close()
        raise HTTPException(
            status_code=429, 
            detail=f"Daily limit of {MAX_UPLOADS_PER_IP} uploads exceeded"
        )
    
    conn.close()
    return client_ip

# Background task to cleanup old files
async def cleanup_old_files():
    """Remove files older than 24 hours"""
    while True:
        try:
            cutoff_time = datetime.now() - timedelta(hours=CLEANUP_AFTER_HOURS)
            
            # Find old jobs
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                SELECT id, filename FROM jobs 
                WHERE created_at < ?
            """, (cutoff_time,))
            
            old_jobs = c.fetchall()
            
            # Delete files and records
            for job_id, filename in old_jobs:
                file_path = UPLOAD_DIR / filename
                if file_path.exists():
                    file_path.unlink()
                
                c.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            
            conn.commit()
            conn.close()
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"Cleanup error: {e}")
            await asyncio.sleep(3600)

# Process audio with Whisper
async def process_audio(job_id: str, file_path: Path):
    """Process audio file with Whisper"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Update status
        c.execute("""
            UPDATE jobs SET status = 'processing', progress = 10 
            WHERE id = ?
        """, (job_id,))
        conn.commit()
        
        # Transcribe
        model = load_whisper_model()
        
        if USING_FASTER_WHISPER:
            # faster-whisper
            segments, info = model.transcribe(
                str(file_path),
                beam_size=5,
                language="en",
                condition_on_previous_text=False
            )
            
            # Combine segments
            result_text = " ".join([segment.text.strip() for segment in segments])
            
        else:
            # openai-whisper
            result = model.transcribe(str(file_path))
            result_text = result["text"].strip()
        
        # Update with result
        c.execute("""
            UPDATE jobs 
            SET status = 'completed', 
                progress = 100, 
                result_text = ?,
                completed_at = ?
            WHERE id = ?
        """, (result_text, datetime.now(), job_id))
        
    except Exception as e:
        # Update with error
        c.execute("""
            UPDATE jobs 
            SET status = 'failed', 
                error = ?,
                completed_at = ?
            WHERE id = ?
        """, (str(e), datetime.now(), job_id))
    
    finally:
        conn.commit()
        conn.close()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with upload form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/auth")
async def authenticate(password: str):
    """Simple password authentication"""
    if password == DEMO_PASSWORD:
        response = JSONResponse({"status": "authenticated"})
        # Set cookie
        auth_hash = hashlib.sha256(DEMO_PASSWORD.encode()).hexdigest()
        response.set_cookie(key="demo_auth", value=auth_hash, max_age=86400)
        return response
    else:
        raise HTTPException(status_code=401, detail="Invalid password")

@app.post("/upload")
async def upload_audio(
    request: Request,
    file: UploadFile = File(...),
    auth: bool = Depends(check_demo_auth),
    client_ip: str = Depends(check_rate_limit)
):
    """Upload audio file for transcription"""
    
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Max size is {MAX_FILE_SIZE // 1024 // 1024}MB"
        )
    
    # Validate file type
    if not file.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.flac')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Supported: MP3, WAV, M4A, MP4, OGG, FLAC"
        )
    
    # Generate job ID
    job_id = hashlib.sha256(f"{client_ip}{datetime.now()}".encode()).hexdigest()[:12]
    
    # Save file
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Create job record
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO jobs (id, ip_address, filename, file_size, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, client_ip, file_path.name, len(contents), "queued", datetime.now()))
    
    # Update usage stats
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        INSERT INTO usage_stats (ip_address, date, upload_count)
        VALUES (?, ?, 1)
        ON CONFLICT(ip_address, date) 
        DO UPDATE SET upload_count = upload_count + 1
    """, (client_ip, today))
    
    conn.commit()
    conn.close()
    
    # Start processing in background
    asyncio.create_task(process_audio(job_id, file_path))
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/status/{job_id}")
async def get_status(job_id: str, auth: bool = Depends(check_demo_auth)):
    """Get job status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT status, progress, error FROM jobs WHERE id = ?
    """, (job_id,))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status, progress, error = result
    
    return {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "error": error
    }

@app.get("/result/{job_id}")
async def get_result(job_id: str, auth: bool = Depends(check_demo_auth)):
    """Get transcription result"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT status, result_text, error, created_at, completed_at 
        FROM jobs WHERE id = ?
    """, (job_id,))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status, result_text, error, created_at, completed_at = result
    
    if status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Job not completed. Status: {status}"
        )
    
    # Calculate processing time
    if created_at and completed_at:
        created = datetime.fromisoformat(created_at)
        completed = datetime.fromisoformat(completed_at)
        processing_time = (completed - created).total_seconds()
    else:
        processing_time = None
    
    return {
        "job_id": job_id,
        "text": result_text,
        "processing_time": processing_time
    }

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": WHISPER_MODEL}

# Run the app
if __name__ == "__main__":
    # For development
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)