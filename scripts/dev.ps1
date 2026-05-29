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

$script:BackendHost = "127.0.0.1"
$script:BackendPort = 8000
$script:FrontendPort = 5173

# Process handles — script scope so functions can modify them
$script:BackendProcess = $null
$script:FrontendProcess = $null
$script:CleanupDone = $false

function Cleanup {
    if ($script:CleanupDone) { return }
    $script:CleanupDone = $true
    Write-Host "`nShutting down servers..." -ForegroundColor Yellow

    if ($null -ne $script:BackendProcess -and -not $script:BackendProcess.HasExited) {
        Stop-Process -Id $script:BackendProcess.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
    if ($null -ne $script:FrontendProcess -and -not $script:FrontendProcess.HasExited) {
        Stop-Process -Id $script:FrontendProcess.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
    Write-Host "Done." -ForegroundColor Green
}

try {
    function Start-Backend {
        Write-Host "Starting backend API server at http://${script:BackendHost}:${script:BackendPort}..." -ForegroundColor Cyan
        Write-Host "  API docs: http://${script:BackendHost}:${script:BackendPort}/api/docs" -ForegroundColor DarkCyan
        Write-Host ""

        $script:BackendProcess = Start-Process uv -ArgumentList @(
            "run", "uvicorn", "osintote.api.app:app",
            "--reload",
            "--host", $script:BackendHost,
            "--port", $script:BackendPort
        ) -NoNewWindow -PassThru

        Write-Host "  Backend PID: $($script:BackendProcess.Id)" -ForegroundColor Green
    }

    function Start-Frontend {
        Write-Host "Starting frontend dev server at http://localhost:${script:FrontendPort}..." -ForegroundColor Cyan
        Write-Host ""

        $script:FrontendProcess = Start-Process uv -ArgumentList @(
            "-C", "frontend", "run", "dev"
        ) -NoNewWindow -PassThru

        Write-Host "  Frontend PID: $($script:FrontendProcess.Id)" -ForegroundColor Green
    }

    switch ($Mode) {
        "api" {
            Start-Backend
            Write-Host "Backend running. Press Ctrl+C to stop." -ForegroundColor Yellow
            $script:BackendProcess.WaitForExit()
        }
        "ui" {
            Start-Frontend
            Write-Host "Frontend running. Press Ctrl+C to stop." -ForegroundColor Yellow
            $script:FrontendProcess.WaitForExit()
        }
        "both" {
            Start-Backend
            Start-Frontend

            Write-Host ""
            Write-Host "========================================" -ForegroundColor DarkYellow
            Write-Host "  OSINTote dev server" -ForegroundColor DarkYellow
            Write-Host "  Backend:  http://${script:BackendHost}:${script:BackendPort}" -ForegroundColor DarkYellow
            Write-Host "  Frontend: http://localhost:${script:FrontendPort}" -ForegroundColor DarkYellow
            Write-Host "  API docs: http://${script:BackendHost}:${script:BackendPort}/api/docs" -ForegroundColor DarkYellow
            Write-Host "========================================" -ForegroundColor DarkYellow
            Write-Host ""
            Write-Host "Press Ctrl+C to stop all servers." -ForegroundColor Yellow
            Write-Host ""

            # Poll loop — wait for either process to exit
            while ($script:BackendProcess -and -not $script:BackendProcess.HasExited -and
                   $script:FrontendProcess -and -not $script:FrontendProcess.HasExited) {
                Start-Sleep -Milliseconds 1000
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
