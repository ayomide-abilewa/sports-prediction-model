@echo off
echo ===================================================
echo Starting AI Football Probability Engine & Dashboard
echo ===================================================

echo [1/2] Starting FastAPI Backend on http://localhost:8000 ...
start "Football Engine Backend" cmd /k ".\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

echo [2/2] Starting Next.js Frontend Dashboard on http://localhost:3000 ...
cd frontend
start "Football Engine Frontend" cmd /k "npm.cmd run dev"

echo ===================================================
echo Done! Opening dashboard in your browser...
echo Dashboard: http://localhost:3000
echo API Docs:  http://localhost:8000/docs
echo ===================================================
timeout /t 3 >nul
start http://localhost:3000
