# Start both the backend API server and the frontend dev server.
# Usage:
#   .\scripts\dev.ps1            # Start both servers
#   .\scripts\dev.ps1 api        # Start only the backend API server
#   .\scripts\dev.ps1 ui         # Start only the frontend dev server
#
# Alternatively use:
#   make dev        (requires GNU make + uv)
#   cd frontend && npm run dev  (frontend only)
#   osintote serve                            (backend only)

param(
    [ValidateSet("api", "ui", "both")]
    [string]$Mode = "both"
)

$ErrorActionPreference = "Stop"

$BackendHost = "127.0.0.1"
$BackendPort = 8000
$FrontendPort = 5173

$BackendProcess = $null
$FrontendProcess = $null

function Cleanup {
    if ($null -ne $BackendProcess -and -not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
        $BackendProcess.WaitForExit(1000)
    }
    if ($null -ne $FrontendProcess -and -not $FrontendProcess.HasExited) {
        Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
        $FrontendProcess.WaitForExit(1000)
    }
}

try {
    Register-EngineEvent -SourceIdentifier "PowerShell.Exiting" -Action { Cleanup } | Out-Null
    [ConsoleEvent]::Register({ Cleanup }) | Out-Null

    function Start-Backend {
        Write-Host "Starting backend API server at http://${BackendHost}:${BackendPort}..." -ForegroundColor Cyan
        Write-Host "  API docs: http://${BackendHost}:${BackendPort}/api/docs" -ForegroundColor DarkCyan
        Write-Host ""

        $BackendProcess = Start-Process uv -ArgumentList @(
            "run", "uvicorn", "osintote.api.app:app",
            "--reload",
            "--host", $BackendHost,
            "--port", $BackendPort
        ) -NoNewWindow -PassThru -RedirectStandardOutput "$($env:TEMP)\osintote-backend.log" -RedirectStandardError "$($env:TEMP)\osintote-backend.log"

        Write-Host "  Backend PID: $($BackendProcess.Id)" -ForegroundColor Green
    }

    function Start-Frontend {
        Write-Host "Starting frontend dev server at http://localhost:${FrontendPort}..." -ForegroundColor Cyan
        Write-Host ""

        $FrontendProcess = Start-Process uv -ArgumentList @(
            "-C", "frontend", "run", "dev"
        ) -NoNewWindow -PassThru -RedirectStandardOutput "$($env:TEMP)\osintote-frontend.log" -RedirectStandardError "$($env:TEMP)\osintote-frontend.log"

        Write-Host "  Frontend PID: $($FrontendProcess.Id)" -ForegroundColor Green
    }

    switch ($Mode) {
        "api" {
            Start-Backend
            Write-Host "Backend running. Press Ctrl+C to stop." -ForegroundColor Yellow
            $BackendProcess.WaitForExit()
        }
        "ui" {
            Start-Frontend
            Write-Host "Frontend running. Press Ctrl+C to stop." -ForegroundColor Yellow
            $FrontendProcess.WaitForExit()
        }
        "both" {
            Start-Backend
            Start-Frontend

            Write-Host ""
            Write-Host "========================================" -ForegroundColor DarkYellow
            Write-Host "  OSINTote dev server" -ForegroundColor DarkYellow
            Write-Host "  Backend:  http://${BackendHost}:${BackendPort}" -ForegroundColor DarkYellow
            Write-Host "  Frontend: http://localhost:${FrontendPort}" -ForegroundColor DarkYellow
            Write-Host "  API docs: http://${BackendHost}:${BackendPort}/api/docs" -ForegroundColor DarkYellow
            Write-Host "========================================" -ForegroundColor DarkYellow
            Write-Host ""
            Write-Host "Press Ctrl+C to stop all servers." -ForegroundColor Yellow
            Write-Host ""

            # Wait for either process to exit
            $allProcesses = @()
            if ($BackendProcess -and -not $BackendProcess.HasExited) { $allProcesses += $BackendProcess }
            if ($FrontendProcess -and -not $FrontendProcess.HasExited) { $allProcesses += $FrontendProcess }

            while ($allProcesses.Count -gt 0) {
                $done = @()
                foreach ($p in $allProcesses) {
                    if ($p.HasExited) {
                        $done += $p
                    }
                }
                foreach ($d in $done) {
                    $allProcesses = $allProcesses | Where-Object { $_ -ne $d }
                }
                Start-Sleep -Milliseconds 500
            }
        }
        default {
            Write-Host "Usage: .\scripts\dev.ps1 [api|ui|both]" -ForegroundColor Red
            Write-Host ""
            Write-Host "  api   - Start the backend API server only" -ForegroundColor White
            Write-Host "  ui    - Start the frontend dev server only" -ForegroundColor White
            Write-Host "  both  - Start both servers (default)" -ForegroundColor White
            exit 1
        }
    }
}
finally {
    Cleanup
}
