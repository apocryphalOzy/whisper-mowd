@echo off
echo =====================================
echo Whisper MOWD Minimal Demo
echo (Python 3.13+ Compatible)
echo =====================================
echo.

echo Installing Whisper...
"C:\Users\jerem\Documents\projects\whisper\Scripts\pip.exe" install openai-whisper

echo.
echo Starting minimal demo server...
echo.
echo Once started, open your browser to: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

cd "C:\Users\jerem\Documents\projects\whisper\demo"
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" app_minimal.py

pause