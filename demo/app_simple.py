"""
Simple Whisper Demo - No FastAPI required
Works with basic Python libraries
"""

import os
import json
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import cgi
import mimetypes

# Try to import whisper
try:
    from faster_whisper import WhisperModel
    USING_FASTER_WHISPER = True
    print("Using faster-whisper")
except ImportError:
    try:
        import whisper
        USING_FASTER_WHISPER = False
        print("Using openai-whisper")
    except ImportError:
        print("ERROR: No whisper library found!")
        print("Install with: pip install openai-whisper")
        exit(1)

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_FILE = "results.json"
DEMO_PASSWORD = "whisper2025"
WHISPER_MODEL = "tiny"

# Load existing results
if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, 'r') as f:
        results = json.load(f)
else:
    results = {}

# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Whisper MOWD - Audio Transcription Demo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            background: white; 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 800px;
            margin: 0 auto;
        }
        h1 { 
            color: #333; 
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.2em;
        }
        .upload-form { 
            margin: 30px 0;
            text-align: center;
        }
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            cursor: pointer;
            background: #f0f0f0;
            padding: 15px 30px;
            border-radius: 10px;
            margin: 20px 0;
            transition: all 0.3s;
        }
        .file-input-wrapper:hover {
            background: #e0e0e0;
        }
        input[type="file"] { 
            position: absolute;
            left: -9999px;
        }
        .file-label {
            display: block;
            font-size: 16px;
            color: #555;
        }
        .file-name {
            margin-top: 10px;
            font-size: 14px;
            color: #666;
            min-height: 20px;
        }
        button { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 15px 40px; 
            border: none; 
            border-radius: 30px; 
            cursor: pointer; 
            font-size: 18px;
            font-weight: 600;
            transition: transform 0.2s;
            margin: 20px 0;
        }
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .result { 
            margin-top: 30px; 
            padding: 30px; 
            background: #f8f9fa; 
            border-radius: 15px;
            border: 2px solid #e9ecef;
        }
        .result h2 {
            color: #333;
            margin-bottom: 20px;
        }
        .result-meta {
            background: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #666;
        }
        .result-text {
            background: white;
            padding: 20px;
            border-radius: 10px;
            line-height: 1.8;
            font-size: 16px;
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        .result-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .result-actions button {
            padding: 10px 25px;
            font-size: 14px;
        }
        .info { 
            background: #fff3cd; 
            padding: 20px; 
            border-radius: 10px; 
            margin: 20px 0;
            border: 1px solid #ffeaa7;
        }
        .info h3 {
            margin-bottom: 10px;
            color: #856404;
        }
        .info ul {
            margin-left: 20px;
            color: #856404;
        }
        .loading {
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
        }
        footer {
            text-align: center;
            margin-top: 40px;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Whisper MOWD</h1>
        <p class="subtitle">Educational Audio Transcription Demo</p>
        
        <div class="info">
            <h3>Demo Limitations:</h3>
            <ul>
                <li>Maximum file size: 50MB</li>
                <li>Supported formats: MP3, WAV</li>
                <li>Processing time: ~30 seconds per minute of audio</li>
                <li>Using Whisper {model_size} model</li>
            </ul>
        </div>
        
        {content}
        
        <footer>
            <p>This is a demo version. Contact us for enterprise features including batch processing, API access, and cloud storage.</p>
        </footer>
    </div>
    
    <script>
        function updateFileName() {
            const fileInput = document.getElementById('audioFile');
            const fileName = document.getElementById('fileName');
            const submitBtn = document.getElementById('submitBtn');
            
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                fileName.textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(2) + ' MB)';
                submitBtn.disabled = false;
            } else {
                fileName.textContent = '';
                submitBtn.disabled = true;
            }
        }
        
        function showLoading() {
            document.getElementById('uploadForm').style.display = 'none';
            document.getElementById('loadingDiv').style.display = 'block';
            return true;
        }
        
        function copyText() {
            const text = document.getElementById('resultText').innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert('Text copied to clipboard!');
            });
        }
        
        function downloadText() {
            const text = document.getElementById('resultText').innerText;
            const blob = new Blob([text], {type: 'text/plain'});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'transcription.txt';
            a.click();
            window.URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>"""

# Load Whisper model
print(f"Loading Whisper model: {WHISPER_MODEL}")
if USING_FASTER_WHISPER:
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
else:
    model = whisper.load_model(WHISPER_MODEL)
print("Model loaded!")

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Check for result
            query = parse_qs(urlparse(self.path).query)
            result_content = ""
            
            if 'result' in query:
                job_id = query['result'][0]
                if job_id in results:
                    result_content = f'''
                    <div class="result">
                        <h2>✅ Transcription Complete</h2>
                        <div class="result-meta">
                            <strong>File:</strong> {results[job_id]['filename']}<br>
                            <strong>Processed:</strong> {results[job_id]['timestamp']}
                        </div>
                        <div class="result-text" id="resultText">
                            {results[job_id]['text']}
                        </div>
                        <div class="result-actions">
                            <button onclick="copyText()">📋 Copy Text</button>
                            <button onclick="downloadText()">💾 Download</button>
                            <a href="/"><button>🔄 New Upload</button></a>
                        </div>
                    </div>
                    '''
            
            # Upload form
            upload_form = '''
            <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data" class="upload-form" onsubmit="return showLoading()">
                <h2>Upload Audio File</h2>
                <div class="file-input-wrapper">
                    <label for="audioFile" class="file-label">
                        📁 Choose Audio File
                    </label>
                    <input type="file" id="audioFile" name="audio" accept=".mp3,.wav" required onchange="updateFileName()">
                    <div class="file-name" id="fileName"></div>
                </div>
                <br>
                <button type="submit" id="submitBtn" disabled>🎯 Transcribe Audio</button>
            </form>
            
            <div id="loadingDiv" class="loading" style="display: none;">
                <div class="spinner"></div>
                <h3>Processing your audio file...</h3>
                <p>This may take 30-60 seconds depending on file length.</p>
            </div>
            '''
            
            content = result_content or upload_form
            self.wfile.write(HTML_TEMPLATE.format(content=content, model_size=WHISPER_MODEL).encode())
    
    def do_POST(self):
        if self.path == '/upload':
            # Parse the form data
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            # Get the uploaded file
            if 'audio' not in form:
                self.send_error(400, "No file uploaded")
                return
            
            fileitem = form['audio']
            
            # Check if file was uploaded
            if not fileitem.filename:
                self.send_error(400, "No file selected")
                return
            
            # Check file extension
            if not fileitem.filename.lower().endswith(('.mp3', '.wav')):
                self.send_error(400, "Only MP3 and WAV files allowed")
                return
            
            # Generate job ID
            job_id = hashlib.md5(f"{fileitem.filename}{datetime.now()}".encode()).hexdigest()[:8]
            
            # Save file
            filename = f"{job_id}_{os.path.basename(fileitem.filename)}"
            filepath = UPLOAD_DIR / filename
            
            with open(filepath, 'wb') as f:
                f.write(fileitem.file.read())
            
            # Process with Whisper
            print(f"Processing: {filename}")
            
            try:
                if USING_FASTER_WHISPER:
                    segments, info = model.transcribe(str(filepath), beam_size=5)
                    text = " ".join([segment.text.strip() for segment in segments])
                else:
                    result = model.transcribe(str(filepath))
                    text = result["text"].strip()
                
                # Save result
                results[job_id] = {
                    'filename': fileitem.filename,
                    'text': text,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Save to file
                with open(RESULTS_FILE, 'w') as f:
                    json.dump(results, f)
                
                print(f"Transcription complete for {filename}")
                
                # Redirect to results
                self.send_response(303)
                self.send_header('Location', f'/?result={job_id}')
                self.end_headers()
                
            except Exception as e:
                print(f"Error: {e}")
                self.send_error(500, f"Processing error: {str(e)}")
            
            finally:
                # Clean up file
                if filepath.exists():
                    filepath.unlink()

def run_server(port=8000):
    server = HTTPServer(('', port), SimpleHandler)
    print(f"\nServer running at http://localhost:{port}")
    print("Press Ctrl+C to stop\n")
    server.serve_forever()

if __name__ == "__main__":
    run_server()