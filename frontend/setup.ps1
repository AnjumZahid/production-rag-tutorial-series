$ErrorActionPreference = "Stop"

Write-Host "Setting up Knowledge Chat frontend..." -ForegroundColor Cyan

if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.example" ".env.local"
    Write-Host "Created .env.local from .env.example" -ForegroundColor Green
}

npm install
npm run typecheck
npm run build

Write-Host "Frontend setup completed successfully." -ForegroundColor Green
Write-Host "Run: npm run dev" -ForegroundColor Yellow
Write-Host "Open: http://localhost:3000" -ForegroundColor Yellow
