@echo off
echo Running Whisper MOWD CLI...
cd /d "C:\Users\jerem\Documents\projects\whisper"

REM Activate virtual environment
call Scripts\activate.bat

REM Run the CLI with passed arguments
python whisper-mowd\src\cli.py %*

echo.
echo Process completed.
pause