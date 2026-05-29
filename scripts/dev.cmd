@echo off
REM Launcher for Windows — calls the PowerShell dev script.
REM Usage:
REM   scripts\dev.cmd              ^ - Start both servers
REM   scripts\dev.cmd api          ^ - Start only the backend API server
REM   scripts\dev.cmd ui           ^ - Start only the frontend dev server
REM
REM Alternatively use:
REM   make dev        (requires GNU make + uv)
REM   cd frontend ^& npm run dev  (frontend only)
REM   osintote serve                            (backend only)

set SCRIPT_DIR=%~dp0
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%dev.ps1" %*
