# Test completo de todas las features nuevas
param([int]$Port = 18001)

$ErrorActionPreference = "Stop"
$API_URL = "http://127.0.0.1:$Port"

Write-Host ""
Write-Host "Testing All Features - Pokedex Arcana" -ForegroundColor Cyan
Write-Host ""

Write-Host "Test 1: Team Builder" -ForegroundColor Yellow
try {
  $response = Invoke-RestMethod -Method Post -Uri "$API_URL/teams/build" `
    -ContentType "application/json" `
    -Body '{"anchor_pokemon":"garchomp","format":"OU","team_size":6}' `
    -TimeoutSec 30
  Write-Host "  PASS: Team built" -ForegroundColor Green
  Write-Host "  Members: $($response.team.Length)"
} catch {
  Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Test 2: Compare Pokemon" -ForegroundColor Yellow
try {
  $response = Invoke-RestMethod -Method Post -Uri "$API_URL/compare/" `
    -ContentType "application/json" `
    -Body '["charizard","blastoise"]' `
    -TimeoutSec 30
  Write-Host "  PASS: Comparison ok" -ForegroundColor Green
  Write-Host "  Winner: $($response.winner)"
} catch {
  Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
}

$SAVED_TEAM_ID = $null
Write-Host "Test 3: Save Team" -ForegroundColor Yellow
try {
  $saveBody = @{
    name = "Test OU Team"
    format = "OU"
    members = @(
      @{
        pokemon = "garchomp"
        sprite = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/445.png"
        types = @("dragon", "ground")
        ability = "rough-skin"
      }
    )
  } | ConvertTo-Json -Depth 10

  $response = Invoke-RestMethod -Method Post -Uri "$API_URL/saved-teams/" `
    -ContentType "application/json" `
    -Body $saveBody `
    -TimeoutSec 30
  $SAVED_TEAM_ID = $response.id
  Write-Host "  PASS: Team saved ($SAVED_TEAM_ID)" -ForegroundColor Green
} catch {
  Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Test 4: List Teams" -ForegroundColor Yellow
try {
  $response = Invoke-RestMethod -Method Get -Uri "$API_URL/saved-teams/" -TimeoutSec 30
  Write-Host "  PASS: Teams listed ($($response.Length))" -ForegroundColor Green
} catch {
  Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Test 5: Export Team" -ForegroundColor Yellow
try {
  if ($SAVED_TEAM_ID) {
    $response = Invoke-RestMethod -Method Post -Uri "$API_URL/saved-teams/$SAVED_TEAM_ID/export" -TimeoutSec 30
    Write-Host "  PASS: Export ok ($($response.format))" -ForegroundColor Green
  } else {
    Write-Host "  SKIP: Team ID missing" -ForegroundColor Yellow
  }
} catch {
  Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
