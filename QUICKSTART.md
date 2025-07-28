# Whisper MOWD - Quick Start Guide

## Setup Instructions

### 1. Environment Setup

**Option A: Using Batch Script (Windows CMD)**
```cmd
setup_env.bat
```

**Option B: Using PowerShell**
```powershell
# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then run:
.\setup_env.ps1
```

**Option C: Manual Setup**
```cmd
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r whisper-mowd\requirements.txt
```

### 2. Configure Environment

1. Edit `whisper-mowd\.env` file
2. Add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```
3. For Windows, update the TEMP_DIR:
   ```
   TEMP_DIR=C:\Temp\mowd-whisper
   ```

### 3. Test Basic Functionality

```cmd
# Activate virtual environment first
venv\Scripts\activate

# Test with a sample audio file
python whisper-mowd\src\cli.py --audio path\to\your\audio.mp3 --output output\

# Test without summarization
python whisper-mowd\src\cli.py --audio path\to\your\audio.mp3 --summarizer none
```

### 4. Common Commands

**Basic Transcription:**
```cmd
python whisper-mowd\src\cli.py --audio lecture.mp3
```

**With Custom Model Size:**
```cmd
python whisper-mowd\src\cli.py --audio lecture.mp3 --model small
```

**Batch Processing:**
```cmd
python whisper-mowd\scripts\process_batch.py --directory audio_folder\ --output output\
```

## Troubleshooting

### FFmpeg Not Found
- Download from: https://ffmpeg.org/download.html
- Add to PATH or place in project directory

### Module Import Errors
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r whisper-mowd\requirements.txt`

### OpenAI API Errors
- Verify API key in .env file
- Check API key has sufficient credits

### Permission Errors
- Run as administrator if needed
- Check file/folder permissions

## Next Steps

1. Review security features in `docs/`
2. Set up AWS credentials for cloud storage
3. Configure monitoring and logging
4. Deploy to staging environment

For detailed documentation, see the README.md file.