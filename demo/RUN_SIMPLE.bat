@echo off
echo ===================================
echo Whisper Simple Demo (No FastAPI)
echo ===================================
echo.

echo Installing Whisper...
"C:\Users\jerem\Documents\projects\whisper\Scripts\pip.exe" install openai-whisper

echo.
echo Starting simple demo server...
echo.
echo Once started, open your browser to: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

cd "C:\Users\jerem\Documents\projects\whisper\demo"
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" app_simple.py

pause