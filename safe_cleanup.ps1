# safe_cleanup_heavy.ps1
# Put this file in the project root folder next to docker-compose.yml.
# It removes only safe generated/heavy files.
# It DOES NOT remove Neo4j database data, uploaded documents, .env, source code, or configuration files.

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "=== Safe heavy cleanup ===" -ForegroundColor Cyan
Write-Host ""

if (!(Test-Path (Join-Path $ProjectRoot "docker-compose.yml"))) {
    Write-Host "ERROR: docker-compose.yml not found." -ForegroundColor Red
    Write-Host "Put this script in the project root folder." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

function Remove-PathIfExists {
    param (
        [string]$RelativePath
    )

    $FullPath = Join-Path $ProjectRoot $RelativePath

    if (Test-Path $FullPath) {
        Write-Host "Removing: $RelativePath" -ForegroundColor Yellow
        Remove-Item $FullPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Project root:" -ForegroundColor Cyan
Write-Host $ProjectRoot -ForegroundColor Yellow
Write-Host ""

Write-Host "This cleanup WILL NOT touch:" -ForegroundColor Green
Write-Host "  neo4j/data" -ForegroundColor DarkGray
Write-Host "  backend/uploads" -ForegroundColor DarkGray
Write-Host "  .env" -ForegroundColor DarkGray
Write-Host "  source code" -ForegroundColor DarkGray
Write-Host ""

# React / frontend generated dependencies
Remove-PathIfExists "rag-ui\node_modules"
Remove-PathIfExists "rag-ui\dist"
Remove-PathIfExists "rag-ui\build"

# Common caches
Remove-PathIfExists ".pytest_cache"
Remove-PathIfExists ".mypy_cache"
Remove-PathIfExists ".ruff_cache"
Remove-PathIfExists ".parcel-cache"
Remove-PathIfExists ".next"
Remove-PathIfExists ".turbo"

# Backend / parser generated caches
Remove-PathIfExists "backend\.pytest_cache"
Remove-PathIfExists "backend\.mypy_cache"
Remove-PathIfExists "backend\.ruff_cache"

Remove-PathIfExists "neo4j\parser_service\.pytest_cache"
Remove-PathIfExists "neo4j\parser_service\.mypy_cache"
Remove-PathIfExists "neo4j\parser_service\.ruff_cache"

# Parser output is generated from PDF parsing, not the Neo4j database.
# If you want to keep parser intermediate files, comment the next line.
Remove-PathIfExists "neo4j\parser_service\parser\output"

# Remove all __pycache__ folders
Write-Host "Removing Python __pycache__ folders..." -ForegroundColor Cyan
Get-ChildItem $ProjectRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Remove compiled Python files
Write-Host "Removing compiled Python files..." -ForegroundColor Cyan
Get-ChildItem $ProjectRoot -Recurse -Force -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

# Remove log files, but not Neo4j database
Write-Host "Removing log files..." -ForegroundColor Cyan
Get-ChildItem $ProjectRoot -Recurse -Force -File -Include "*.log" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "DONE." -ForegroundColor Green
Write-Host "Safe cleanup finished." -ForegroundColor Green
Write-Host ""
Write-Host "Not removed:" -ForegroundColor Cyan
Write-Host "  neo4j/data" -ForegroundColor DarkGray
Write-Host "  backend/uploads" -ForegroundColor DarkGray
Write-Host "  .env" -ForegroundColor DarkGray
Write-Host "  docker-compose.yml" -ForegroundColor DarkGray
Write-Host "  backend / neo4j / rag-ui source code" -ForegroundColor DarkGray
Write-Host ""
Read-Host "Press Enter to close"
