Write-Host "Starting Whisper MOWD Demo..." -ForegroundColor Green
Write-Host ""

# Set paths
$projectDir = "C:\Users\jerem\Documents\projects\whisper"
$pythonPath = "$projectDir\Scripts\python.exe"
$pipPath = "$projectDir\Scripts\pip.exe"

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
& $pipPath install -r "$projectDir\demo\requirements-demo.txt"

Write-Host ""
Write-Host "Starting demo server..." -ForegroundColor Green
Set-Location "$projectDir\demo"
& $pythonPath app_demo.py