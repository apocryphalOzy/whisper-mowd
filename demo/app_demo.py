"""
Whisper MOWD Demo API
Simplified version for zero-cost deployment and market validation
"""

import os
import sys
import json
import sqlite3
import asyncio
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# Add parent directory to path to import from main project
sys.path.insert(0, str(Path(__file__).parent.parent / 'whisper-mowd'))

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import AudioFileConverter from main project
from src.transcription.file_converter import AudioFileConverter

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
MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB
MAX_DURATION_SECONDS = 300  # 5 minutes
MAX_UPLOADS_PER_IP = 10
CLEANUP_AFTER_HOURS = 24
WHISPER_MODEL = "base"  # Use base for better accuracy while maintaining speed
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "whisper2025")

# Supported file extensions (from AudioFileConverter)
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.opus', '.amr', '.ac3', '.dts', 
                   '.ape', '.wv', '.tak', '.tta', '.aiff', '.au', '.ra', '.mka', '.m4b', '.spx',
                   '.aac', '.wma']
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.wmv', '.mpg', '.mpeg', 
                   '.3gp', '.3g2', '.m4v', '.f4v', '.f4p', '.ogv', '.asf', '.rm', '.rmvb', 
                   '.vob', '.ts', '.mts', '.m2ts', '.divx', '.xvid']
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS

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
            timestamped_text TEXT,
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
            upload_count INTEGER DEFAULT 0,
            UNIQUE(ip_address, date)
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
    
    # Track temporary files for cleanup
    temp_files = []
    
    try:
        # Update status
        c.execute("""
            UPDATE jobs SET status = 'processing', progress = 10 
            WHERE id = ?
        """, (job_id,))
        conn.commit()
        
        # Check if file needs conversion
        converter = AudioFileConverter(default_output_format="mp3")
        actual_audio_path = file_path
        
        if converter.needs_conversion(file_path):
            # Convert to MP3 for Whisper processing
            c.execute("""
                UPDATE jobs SET status = 'converting', progress = 20 
                WHERE id = ?
            """, (job_id,))
            conn.commit()
            
            converted_path = converter.convert_to_audio(str(file_path), "mp3")
            temp_files.append(converted_path)
            actual_audio_path = Path(converted_path)
        
        # Update progress
        c.execute("""
            UPDATE jobs SET status = 'transcribing', progress = 40 
            WHERE id = ?
        """, (job_id,))
        conn.commit()
        
        # Transcribe
        model = load_whisper_model()
        
        if USING_FASTER_WHISPER:
            # faster-whisper
            segments, info = model.transcribe(
                str(actual_audio_path),
                beam_size=5,
                language="en",
                condition_on_previous_text=False
            )
            
            # Combine segments with timestamps
            result_text = ""
            timestamped_text = ""
            for segment in segments:
                # Plain text
                result_text += segment.text.strip() + " "
                # Timestamped text
                start_time = int(segment.start)
                minutes = start_time // 60
                seconds = start_time % 60
                timestamp = f"[{minutes:02d}:{seconds:02d}]"
                timestamped_text += f"{timestamp} {segment.text.strip()}\n"
            
        else:
            # openai-whisper
            result = model.transcribe(str(actual_audio_path))
            result_text = result["text"].strip()
            
            # Create timestamped version
            timestamped_text = ""
            if "segments" in result:
                for segment in result["segments"]:
                    start_time = int(segment["start"])
                    minutes = start_time // 60
                    seconds = start_time % 60
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"
                    timestamped_text += f"{timestamp} {segment['text'].strip()}\n"
            else:
                timestamped_text = result_text
        
        # Update with result
        c.execute("""
            UPDATE jobs 
            SET status = 'completed', 
                progress = 100, 
                result_text = ?,
                timestamped_text = ?,
                completed_at = ?
            WHERE id = ?
        """, (result_text.strip(), timestamped_text, datetime.now(), job_id))
        
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
        
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"Failed to clean up temp file {temp_file}: {e}")

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with upload form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/auth")
async def authenticate(request: Request):
    """Simple password authentication"""
    body = await request.json()
    password = body.get('password', '')
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
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        # Create a user-friendly format list
        audio_formats = ', '.join([ext.upper()[1:] for ext in AUDIO_EXTENSIONS[:6]]) + "..."
        video_formats = ', '.join([ext.upper()[1:] for ext in VIDEO_EXTENSIONS[:6]]) + "..."
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Supported audio: {audio_formats} | Video: {video_formats} (45 formats total)"
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
        SELECT status, result_text, timestamped_text, error, created_at, completed_at 
        FROM jobs WHERE id = ?
    """, (job_id,))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status, result_text, timestamped_text, error, created_at, completed_at = result
    
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
        "timestamped_text": timestamped_text,
        "processing_time": processing_time
    }

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": WHISPER_MODEL}

# Admin page
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin dashboard - requires password in URL parameter"""
    password = request.query_params.get('password', '')
    
    if password != DEMO_PASSWORD:
        return HTMLResponse("Unauthorized", status_code=401)
    
    # Get recent jobs
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Recent jobs
    c.execute("""
        SELECT * FROM jobs 
        ORDER BY created_at DESC 
        LIMIT 20
    """)
    jobs = [dict(row) for row in c.fetchall()]
    
    # Usage stats
    c.execute("""
        SELECT date, SUM(upload_count) as total_uploads, COUNT(DISTINCT ip_address) as unique_ips
        FROM usage_stats 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 7
    """)
    usage_stats = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    # Create simple HTML response
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - Whisper MOWD</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 10px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #3498db; color: white; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .status-completed {{ color: #27ae60; font-weight: bold; }}
            .status-failed {{ color: #e74c3c; font-weight: bold; }}
            .status-processing {{ color: #f39c12; font-weight: bold; }}
            .security-notice {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔒 Admin Dashboard - Whisper MOWD</h1>
            
            <div class="security-notice">
                <strong>Security Notice:</strong> This admin interface demonstrates audit logging and access control. 
                In production, this would use role-based access control (RBAC) with AWS Cognito.
            </div>
            
            <h2>📊 Usage Statistics (Last 7 Days)</h2>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Total Uploads</th>
                    <th>Unique IPs</th>
                </tr>
    """
    
    for stat in usage_stats:
        html += f"""
                <tr>
                    <td>{stat['date']}</td>
                    <td>{stat['total_uploads']}</td>
                    <td>{stat['unique_ips']}</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h2>📝 Recent Transcription Jobs</h2>
            <table>
                <tr>
                    <th>Job ID</th>
                    <th>Status</th>
                    <th>Filename</th>
                    <th>IP Address</th>
                    <th>Created At</th>
                    <th>Completed At</th>
                </tr>
    """
    
    for job in jobs:
        status_class = f"status-{job['status']}"
        completed = job['completed_at'] or 'N/A'
        html += f"""
                <tr>
                    <td>{job['id'][:8]}...</td>
                    <td class="{status_class}">{job['status'].upper()}</td>
                    <td>{job['filename']}</td>
                    <td>{job['ip_address']}</td>
                    <td>{job['created_at'] or 'N/A'}</td>
                    <td>{completed}</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h2>🛡️ Security Features Demonstrated</h2>
            <ul>
                <li>✅ Access Control: Password-protected admin interface</li>
                <li>✅ Audit Logging: All operations tracked with IP and timestamp</li>
                <li>✅ Data Retention: Automatic cleanup after 24 hours</li>
                <li>✅ Rate Limiting: 10 uploads per IP per day</li>
                <li>✅ Input Validation: File size and type restrictions</li>
            </ul>
            
            <p style="margin-top: 40px; color: #666;">
                Access URL: <code>/admin?password=whisper2025</code>
            </p>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(html)

# Run the app
if __name__ == "__main__":
    # For development
    uvicorn.run(app, host="0.0.0.0", port=8000)