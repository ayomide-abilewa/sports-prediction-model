# PowerShell Launcher for Football Prediction Engine & Dashboard
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting AI Football Probability Engine & Dashboard" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Start Backend in separate window
Write-Host "[1/2] Starting FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

# 2. Start Frontend in separate window
Write-Host "[2/2] Starting Next.js Frontend Dashboard on http://localhost:3000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm.cmd run dev"

Start-Sleep -Seconds 3
Write-Host "Done! Opening http://localhost:3000 in your browser..." -ForegroundColor Yellow
Start-Process "http://localhost:3000"
