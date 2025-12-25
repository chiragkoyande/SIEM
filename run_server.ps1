# SentinelWatch SIEM Server Startup Script
Write-Host "Starting SentinelWatch SIEM Server..." -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Dashboard: http://localhost:8000/" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

