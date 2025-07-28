"""
Minimal Whisper Demo - Works with Python 3.13+
No external web framework needed
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import io

# Try to import whisper
try:
    import whisper
    print("Using openai-whisper")
except ImportError:
    print("ERROR: Whisper not installed!")
    print("Install with: pip install openai-whisper")
    exit(1)

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
WHISPER_MODEL = "tiny"
PORT = 8000

# Simple HTML interface
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Whisper MOWD - Simple Demo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .upload-area {
            border: 2px dashed #ddd;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin: 20px 0;
            background: #fafafa;
        }
        .upload-area:hover {
            border-color: #667eea;
            background: #f5f5ff;
        }
        input[type="file"] {
            display: none;
        }
        .file-label {
            display: inline-block;
            padding: 12px 30px;
            background: #667eea;
            color: white;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        .file-label:hover {
            background: #5a67d8;
            transform: translateY(-2px);
        }
        .file-info {
            margin-top: 15px;
            color: #666;
        }
        .submit-btn {
            background: #48bb78;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            transition: all 0.3s;
        }
        .submit-btn:hover:not(:disabled) {
            background: #38a169;
            transform: translateY(-2px);
        }
        .submit-btn:disabled {
            background: #cbd5e0;
            cursor: not-allowed;
            transform: none;
        }
        .info-box {
            background: #fff5f5;
            border: 1px solid #feb2b2;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            color: #742a2a;
        }
        .result {
            background: #f0fff4;
            border: 1px solid #9ae6b4;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .result-text {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            line-height: 1.6;
            max-height: 400px;
            overflow-y: auto;
        }
        .loading {
            text-align: center;
            color: #667eea;
            font-size: 18px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Whisper MOWD</h1>
        <p class="subtitle">Audio Transcription Demo</p>
        
        <div class="info-box">
            <strong>Demo Limits:</strong> Max 25MB • MP3/WAV only • Using Whisper {model} model
        </div>
        
        {content}
    </div>

    <script>
        function selectFile() {
            document.getElementById('fileInput').click();
        }
        
        function fileSelected() {
            const fileInput = document.getElementById('fileInput');
            const fileInfo = document.getElementById('fileInfo');
            const submitBtn = document.getElementById('submitBtn');
            
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                fileInfo.textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(2) + ' MB)';
                submitBtn.disabled = false;
            }
        }
        
        function submitForm() {
            document.getElementById('uploadForm').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('uploadFormReal').submit();
        }
    </script>
</body>
</html>
"""

# Load Whisper model globally
print(f"Loading Whisper {WHISPER_MODEL} model...")
model = whisper.load_model(WHISPER_MODEL)
print("Model loaded successfully!")

class SimpleWhisperHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - show upload form"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        upload_form = '''
        <div id="uploadForm">
            <form id="uploadFormReal" action="/upload" method="post" enctype="multipart/form-data">
                <div class="upload-area" onclick="selectFile()">
                    <input type="file" id="fileInput" name="audio" accept=".mp3,.wav" onchange="fileSelected()" required>
                    <label class="file-label">Choose Audio File</label>
                    <div class="file-info" id="fileInfo">Click to select MP3 or WAV file</div>
                </div>
                <center>
                    <button type="button" class="submit-btn" id="submitBtn" onclick="submitForm()" disabled>
                        Transcribe Audio
                    </button>
                </center>
            </form>
        </div>
        
        <div id="loading" style="display: none;" class="loading">
            <p>⏳ Processing audio... This may take 30-60 seconds.</p>
        </div>
        '''
        
        html = HTML_PAGE.format(content=upload_form, model=WHISPER_MODEL)
        self.wfile.write(html.encode())
    
    def do_POST(self):
        """Handle POST requests - process upload"""
        if self.path == '/upload':
            # Parse multipart data manually
            content_length = int(self.headers['Content-Length'])
            content_type = self.headers['Content-Type']
            
            if 'multipart/form-data' not in content_type:
                self.send_error(400, "Expected multipart/form-data")
                return
            
            # Extract boundary
            boundary = content_type.split('boundary=')[1].encode()
            
            # Read the entire body
            body = self.rfile.read(content_length)
            
            # Split by boundary
            parts = body.split(b'--' + boundary)
            
            # Find the file part
            file_data = None
            filename = None
            
            for part in parts:
                if b'filename=' in part:
                    # Extract filename
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        headers = part[:header_end].decode('utf-8', errors='ignore')
                        if 'filename="' in headers:
                            filename = headers.split('filename="')[1].split('"')[0]
                            file_data = part[header_end + 4:-2]  # Skip \r\n\r\n and trailing \r\n
                            break
            
            if not file_data or not filename:
                self.send_error(400, "No file uploaded")
                return
            
            # Check file extension
            if not filename.lower().endswith(('.mp3', '.wav')):
                self.send_error(400, "Only MP3 and WAV files allowed")
                return
            
            # Save file temporarily
            temp_path = UPLOAD_DIR / f"temp_{hashlib.md5(file_data[:100]).hexdigest()}.mp3"
            temp_path.write_bytes(file_data)
            
            try:
                # Transcribe with Whisper
                print(f"Transcribing {filename}...")
                result = model.transcribe(str(temp_path))
                text = result["text"].strip()
                print("Transcription complete!")
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                result_html = f'''
                <div class="result">
                    <h3>✅ Transcription Complete!</h3>
                    <p><strong>File:</strong> {filename}</p>
                    <div class="result-text">{text}</div>
                    <center>
                        <button class="submit-btn" onclick="navigator.clipboard.writeText(document.querySelector('.result-text').innerText)">
                            Copy Text
                        </button>
                        <button class="submit-btn" onclick="location.href='/'">
                            New Upload
                        </button>
                    </center>
                </div>
                '''
                
                html = HTML_PAGE.format(content=result_html, model=WHISPER_MODEL)
                self.wfile.write(html.encode())
                
            except Exception as e:
                print(f"Error: {e}")
                self.send_error(500, f"Transcription error: {str(e)}")
            
            finally:
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()

def run_server():
    """Start the HTTP server"""
    server = HTTPServer(('', PORT), SimpleWhisperHandler)
    print(f"\n🚀 Server running at http://localhost:{PORT}")
    print("📝 Ready to transcribe audio files!")
    print("Press Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()

if __name__ == "__main__":
    run_server()