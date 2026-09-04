@echo off
cd /d "%~dp0"
start "A股短线量化服务" cmd /k "python app.py --port 8765 --live"
timeout /t 8 /nobreak >nul
cloudflared.exe tunnel --no-autoupdate --url http://127.0.0.1:8765
pause
