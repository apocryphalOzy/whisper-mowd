@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo Whisper MOWD - Automated Setup Script
echo ============================================================
echo.

REM Check for Python 3.10 or 3.11
set PYTHON_CMD=
set PYTHON_VERSION=

REM Try Python 3.10
py -3.10 --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=py -3.10
    set PYTHON_VERSION=3.10
    echo [OK] Found Python 3.10
    goto :setup
)

REM Try Python 3.11
py -3.11 --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=py -3.11
    set PYTHON_VERSION=3.11
    echo [OK] Found Python 3.11
    goto :setup
)

REM Check if regular python is 3.10 or 3.11
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
if "!PY_VER:~0,4!"=="3.10" (
    set PYTHON_CMD=python
    set PYTHON_VERSION=3.10
    echo [OK] Found Python 3.10
    goto :setup
)
if "!PY_VER:~0,4!"=="3.11" (
    set PYTHON_CMD=python
    set PYTHON_VERSION=3.11
    echo [OK] Found Python 3.11
    goto :setup
)

REM No compatible Python found
echo [ERROR] Python 3.10 or 3.11 not found!
echo.
echo Current Python version: !PY_VER!
echo.
echo This project requires Python 3.10 or 3.11 for compatibility.
echo Python 3.13 has known issues with the required dependencies.
echo.
echo Please download and install Python 3.10 from:
echo https://www.python.org/downloads/release/python-31011/
echo.
echo Make sure to:
echo 1. Check "Add Python to PATH" during installation
echo 2. Install for all users
echo 3. After installation, run this script again
echo.
pause
exit /b 1

:setup
echo.
echo Using Python !PYTHON_VERSION! for setup...
echo.

REM Create virtual environment
echo Creating virtual environment...
!PYTHON_CMD! -m venv whisper_env_compatible

REM Activate virtual environment
echo Activating virtual environment...
call whisper_env_compatible\Scripts\activate.bat

REM Verify we're in the venv
where python
python --version

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install core dependencies
echo.
echo Installing core dependencies...
pip install openai-whisper
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install openai-whisper
    pause
    exit /b 1
)

echo Installing additional packages...
pip install python-dotenv tqdm ffmpeg-python

REM Install demo dependencies
echo.
echo Installing demo dependencies...
pip install fastapi uvicorn python-multipart jinja2

REM Test the installation
echo.
echo Testing installation...
python -c "import whisper; print('[OK] Whisper imported successfully')"
if !errorlevel! neq 0 (
    echo [ERROR] Whisper import test failed
    pause
    exit /b 1
)

REM Create run script
echo.
echo Creating run script...
echo @echo off > run_demo.bat
echo call whisper_env_compatible\Scripts\activate.bat >> run_demo.bat
echo cd demo >> run_demo.bat
echo python app_minimal.py >> run_demo.bat
echo pause >> run_demo.bat

echo.
echo ============================================================
echo Setup completed successfully!
echo ============================================================
echo.
echo To run the demo:
echo   Option 1: Double-click run_demo.bat
echo   Option 2: Run these commands:
echo     - whisper_env_compatible\Scripts\activate
echo     - cd demo
echo     - python app_minimal.py
echo.
echo The demo will start at: http://localhost:8000
echo.
pause