@echo off
rem Share this copy of the app through a temporary public link: builds the latest web client, starts
rem the API and opens a Cloudflare tunnel (deploy\tunnel.py). Ctrl+C or closing the window stops it.
cd /d "%~dp0.."
where uv >nul 2>nul
if errorlevel 1 (
  echo Error: uv not found. Install it from https://docs.astral.sh/uv/
  pause
  exit /b 1
)
uv run --project backend python deploy\tunnel.py %*
pause
