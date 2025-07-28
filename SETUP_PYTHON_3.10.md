# Setup Guide for Whisper MOWD with Python 3.10

## Problem Summary

The current Python 3.13 installation has compatibility issues with key dependencies:
- `tiktoken` has circular import issues
- `whisper` fails to load due to tiktoken dependency
- Some packages like `pkg_resources` are deprecated in Python 3.13

## Solution: Install Python 3.10

### Step 1: Download Python 3.10

1. Go to: https://www.python.org/downloads/release/python-31011/
2. Download: **Windows installer (64-bit)** 
   - Direct link: https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe

### Step 2: Install Python 3.10

1. Run the installer
2. **IMPORTANT**: Check "Add Python 3.10 to PATH"
3. Choose "Customize installation"
4. Install to: `C:\Python310` (or your preferred location)
5. Complete the installation

### Step 3: Create New Virtual Environment

Run these commands in PowerShell or Command Prompt:

```batch
cd C:\Users\jerem\Documents\projects\whisper

# Create new virtual environment with Python 3.10
C:\Python310\python.exe -m venv whisper_env_py310

# Activate the new environment
whisper_env_py310\Scripts\activate

# Verify Python version
python --version
# Should show: Python 3.10.11
```

### Step 4: Install Dependencies

```batch
# Upgrade pip
python -m pip install --upgrade pip

# Install core dependencies
pip install openai-whisper
pip install python-dotenv
pip install tqdm
pip install ffmpeg-python

# For the demo
pip install fastapi uvicorn python-multipart jinja2

# Optional: For AWS features
pip install boto3
```

### Step 5: Test the Installation

Create and run this test script:

```batch
python test_environment.py
```

All packages should now show "[OK]" status.

### Step 6: Run the Demo

```batch
cd demo
python app_minimal.py
```

Open browser to: http://localhost:8000

## Alternative: Use Docker

If you prefer not to install another Python version, the project includes Docker support:

```batch
cd demo
docker-compose up
```

## Batch File for Easy Setup

Save this as `setup_py310.bat`:

```batch
@echo off
echo Setting up Whisper MOWD with Python 3.10...
echo.

REM Check if Python 3.10 is installed
py -3.10 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10 not found!
    echo Please install Python 3.10 from:
    echo https://www.python.org/downloads/release/python-31011/
    pause
    exit /b 1
)

echo Creating virtual environment with Python 3.10...
py -3.10 -m venv whisper_env_py310

echo Activating environment...
call whisper_env_py310\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install openai-whisper
pip install fastapi uvicorn python-multipart jinja2
pip install python-dotenv tqdm ffmpeg-python

echo.
echo Setup complete! 
echo To run the demo:
echo   1. whisper_env_py310\Scripts\activate
echo   2. cd demo
echo   3. python app_minimal.py
echo.
pause
```

## Troubleshooting

1. **"py -3.10 not found"**: Make sure Python 3.10 is installed and added to PATH
2. **DLL errors**: Install Visual C++ Redistributables from Microsoft
3. **ffmpeg not found**: Download ffmpeg from https://ffmpeg.org/download.html and add to PATH