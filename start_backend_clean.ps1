# SCRIPT: Arranque limpio del backend con logs habilitados
param([int]$Port = 18001)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " POKEDEX ARCANA - Backend Clean Start " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# PASO 1: Limpieza
Write-Host "[1/4] Limpieza de procesos" -ForegroundColor Yellow
Write-Host "----------------------------------------`n" -ForegroundColor DarkGray

Get-Process | Where-Object { $_.ProcessName -like "*python*" } | ForEach-Object {
    Write-Host "  Terminando PID $($_.Id)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

$connections = netstat -ano | Select-String ":1800[01].*LISTENING"
if ($connections) {
    $pids = $connections | ForEach-Object {
        if ($_ -match "\s+(\d+)\s*$") { $matches[1] }
    } | Select-Object -Unique
    $pids | ForEach-Object { taskkill /PID $_ /F 2>$null | Out-Null }
}

Write-Host "  OK Puertos liberados`n" -ForegroundColor Green

# PASO 2: Configuracion
Write-Host "[2/4] Configuracion del entorno" -ForegroundColor Yellow
Write-Host "----------------------------------------`n" -ForegroundColor DarkGray

$PROJECT_ROOT = "C:\Users\jorge\pokeArca"
$API_DIR = "$PROJECT_ROOT\apps\api"

if (-not (Test-Path $API_DIR)) {
    Write-Host "  ERROR: $API_DIR no existe`n" -ForegroundColor Red
    exit 1
}

Set-Location $API_DIR

$env:PYTHONPATH = @(
    $PROJECT_ROOT,
    "$PROJECT_ROOT\packages\agents\src",
    "$PROJECT_ROOT\packages\infrastructure\src",
    "$PROJECT_ROOT\packages\shared\src",
    "$PROJECT_ROOT\packages\domain\src",
    "$API_DIR\src"
) -join ";"

Write-Host "  OK PYTHONPATH configurado" -ForegroundColor Green

$VENV = "$API_DIR\.venv\Scripts\Activate.ps1"
if (Test-Path $VENV) {
    & $VENV
    Write-Host "  OK Virtual environment activado" -ForegroundColor Green
}

$envFileCandidates = @("$PROJECT_ROOT\.env", "$API_DIR\.env")
$apiKeyFound = $false
foreach ($envFile in $envFileCandidates) {
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile -Raw
        if ($envContent -match "GROQ_API_KEY=(\S+)") {
            $apiKeyFound = $true
            break
        }
    }
}
if ($apiKeyFound) {
    Write-Host "  OK GROQ_API_KEY presente`n" -ForegroundColor Green
} else {
    Write-Host "  WARN GROQ_API_KEY no encontrada`n" -ForegroundColor Yellow
}

# PASO 3: Validacion
Write-Host "[3/4] Validacion de imports" -ForegroundColor Yellow
Write-Host "----------------------------------------`n" -ForegroundColor DarkGray

@"
import sys
sys.path.insert(0, r'$PROJECT_ROOT')
sys.path.insert(0, r'$PROJECT_ROOT\packages\agents\src')
sys.path.insert(0, r'$PROJECT_ROOT\packages\infrastructure\src')
sys.path.insert(0, r'$PROJECT_ROOT\packages\shared\src')
sys.path.insert(0, r'$PROJECT_ROOT\packages\domain\src')
sys.path.insert(0, r'$API_DIR\src')

try:
    from agents.orchestrator import Orchestrator
    from infrastructure.llm_client import LLMClient
    from agents.synthesizer import Synthesizer
    print('  OK Todos los imports OK')
except Exception as e:
    print(f'  ERROR imports: {e}')
    exit(1)
"@ | python

if ($LASTEXITCODE -ne 0) { exit 1 }

# PASO 4: Arranque
Write-Host "`n[4/4] ARRANCANDO BACKEND" -ForegroundColor Yellow
Write-Host "----------------------------------------`n" -ForegroundColor DarkGray
Write-Host "  Puerto: $Port" -ForegroundColor Cyan
Write-Host "  URL: http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host "  Presiona Ctrl+C para detener`n" -ForegroundColor Yellow

uvicorn src.api.main:app --reload --port $Port --log-level debug
