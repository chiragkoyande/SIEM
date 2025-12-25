@echo off
echo Starting SentinelWatch SIEM Server...
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause

