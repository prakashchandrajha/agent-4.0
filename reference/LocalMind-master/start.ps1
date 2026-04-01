# save as start.ps1
cd C:\Users\ankur\.qoder\localmind
.\.venv\Scripts\Activate.ps1

Write-Host "Starting backend..." -ForegroundColor Cyan
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\ankur\.qoder\localmind'; .\.venv\Scripts\Activate.ps1; python -m uvicorn backend.main:app --reload" -PassThru

Write-Host "Waiting for backend to be ready..." -ForegroundColor Yellow
do {
    Start-Sleep -Seconds 2
    try { $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -ErrorAction Stop }
    catch { $r = $null }
} while ($r.StatusCode -ne 200)

Write-Host "Backend ready! Starting frontend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\ankur\.qoder\localmind\frontend'; npm run dev"