@echo off
echo Starting Whisper MOWD Demo...
echo.

REM Get the full path to the project
set PROJECT_DIR=C:\Users\jerem\Documents\projects\whisper

REM Use full paths to Python and pip from virtual environment
echo Installing requirements...
"%PROJECT_DIR%\Scripts\pip.exe" install -r "%PROJECT_DIR%\demo\requirements-demo.txt"

echo.
echo Starting demo server...
cd "%PROJECT_DIR%\demo"
"%PROJECT_DIR%\Scripts\python.exe" app_demo.py

pause