@echo off
echo Starting KAVACH-AI Deepfake System...

echo Starting Backend...
start cmd /k "cd backend && ..\.venv\Scripts\activate.bat && uvicorn main:app --reload"

echo Starting Frontend...
start cmd /k "cd frontend && npm run dev"

echo Both servers are starting in separate windows.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
pause
