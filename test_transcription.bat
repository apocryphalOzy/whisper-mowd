@echo off
echo Testing Whisper transcription...
cd /d "C:\Users\jerem\Documents\projects\whisper"

REM Activate virtual environment
call Scripts\activate.bat

REM Test with an existing audio file
echo.
echo Testing with audio file: whisper-mowd\data\audio\20250429_112153_saqt.mp3
echo Output will be saved to: test_output\
echo.

python whisper-mowd\src\cli.py --audio whisper-mowd\data\audio\20250429_112153_saqt.mp3 --output test_output --summarizer none --model base

echo.
echo Test completed! Check the test_output folder for results.
pause