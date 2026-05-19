@echo off
setlocal

cd /d "%~dp0"
set "ROOT=%~dp0"

echo Starting CHU backend and frontend...
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5000

start "CHU Backend" cmd /k "cd /d ""%ROOT%Backend"" && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
start "CHU Frontend" cmd /k "cd /d ""%ROOT%Frontend"" && set BACKEND_URL=http://127.0.0.1:8000&& python app.py"

endlocal
