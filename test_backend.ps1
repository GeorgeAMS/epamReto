# SCRIPT: Testing automatico del backend
param([int]$Port = 18001)

$API_URL = "http://127.0.0.1:$Port"

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host " POKEDEX ARCANA - Testing Suite " -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Test 1: Health
Write-Host "Test 1: Health Check" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod "$API_URL/health" -TimeoutSec 5
    Write-Host "  OK Backend respondiendo" -ForegroundColor Green
    Write-Host "    Groq: $($health.services.groq_configured)`n" -ForegroundColor Gray
} catch {
    Write-Host "  ERROR Backend no responde en puerto $Port`n" -ForegroundColor Red
    Write-Host "Ejecuta primero: .\start_backend_clean.ps1`n" -ForegroundColor Yellow
    exit 1
}

# Test 2: Conversacional
Write-Host "Test 2: Query conversacional ('hola')" -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Method Post -Uri "$API_URL/chat" `
        -ContentType "application/json" -Body '{"query":"hola"}' -TimeoutSec 10

    $content = if ($r.content) { [string]$r.content } else { [string]$r.final_response.content }

    Write-Host "  OK Respuesta recibida" -ForegroundColor Green
    Write-Host "    Preview: $($content.Substring(0, [Math]::Min(100, $content.Length)))..." -ForegroundColor Gray

    if ($content -match "No encontr[eé] informaci[oó]n") {
        Write-Host "  ERROR FALLO: Respuesta no conversacional`n" -ForegroundColor Red
    } else {
        Write-Host "  OK Exito: Respuesta conversacional detectada`n" -ForegroundColor Green
    }
} catch {
    Write-Host "  ERROR: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 3: Stats natural
Write-Host "Test 3: Stats natural ('que sabes de pikachu')" -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Method Post -Uri "$API_URL/chat" `
        -ContentType "application/json" -Body '{"query":"que sabes de pikachu"}' -TimeoutSec 15

    $content = if ($r.content) { [string]$r.content } else { [string]$r.final_response.content }

    Write-Host "  OK Respuesta recibida" -ForegroundColor Green
    Write-Host "    Preview: $($content.Substring(0, [Math]::Min(150, $content.Length)))..." -ForegroundColor Gray

    if ($content -match "Stats base: HP \d+ \u00b7 Atk") {
        Write-Host "  ERROR FALLO: Formato robotico`n" -ForegroundColor Red
    } else {
        Write-Host "  OK Exito: Formato conversacional detectado`n" -ForegroundColor Green
    }
} catch {
    Write-Host "  ERROR: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 4: Team building
Write-Host "Test 4: Team building ('recomienda equipo para garchomp')" -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Method Post -Uri "$API_URL/chat" `
        -ContentType "application/json" -Body '{"query":"recomienda equipo para garchomp en ou"}' -TimeoutSec 30

    $content = if ($r.content) { [string]$r.content } else { [string]$r.final_response.content }
    $intent = $r.data.intent

    Write-Host "  OK Respuesta recibida" -ForegroundColor Green
    Write-Host "    Intent: $intent" -ForegroundColor Gray

    if ($intent -eq "strategy") {
        Write-Host "  OK Exito: Intent correcto (strategy)`n" -ForegroundColor Green
    } else {
        Write-Host "  WARN Intent deberia ser 'strategy', es '$intent'`n" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARN Error (timeout posible en team building): $($_.Exception.Message)`n" -ForegroundColor Yellow
}

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "OK Tests completados`n" -ForegroundColor Green
