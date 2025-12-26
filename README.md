# SentinelWatch SIEM

SentinelWatch is a lightweight **SIEM (Security Information and Event Management)** demo built with **FastAPI** (backend) and a simple **HTML + Tailwind + Chart.js** dashboard (frontend).

## Features

- **Log ingestion**
  - Single log ingestion via REST
  - Bulk ingestion
  - Upload a `.log` / `.txt` file
- **Alerting & dashboard**
  - Dashboard stats
  - Recent alerts table
  - Alert details modal
  - Acknowledge / resolve alerts
  - Add notes to alerts
- **Exports**
  - Export alerts as **CSV** (and JSON via API)
- **CV endpoints (added)**
  - View CV in browser
  - Download CV as a file

## Project Structure

- `main.py` - FastAPI app entrypoint
- `backend/` - API, database models, ingestion & alerting logic
- `frontend/` - Static dashboard UI
  - `index.html`
  - `assets/dashboard.js`
## web photos 
![Dashboard Screenshot](images/dashboard.png)
![Dashboard Screenshot](images/dashboard2.png)
![Dashboard Screenshot](images/dashboard3.png)
![Dashboard Screenshot](images/dashboard4.png)
## Requirements

- Python 3.10+ (recommended)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the App

### Option A: Run via Python

```bash
python main.py
```



## API Endpoints

### Dashboard

- `GET /api/dashboard/stats`

### Logs

- `POST /api/logs/single`
- `POST /api/logs/bulk`
- `POST /api/logs/upload`
- `GET /api/logs`
- `GET /api/logs/{log_id}`

### Alerts

- `GET /api/alerts`
- `GET /api/alerts/{alert_id}`
- `POST /api/alerts/{alert_id}/acknowledge`
- `POST /api/alerts/{alert_id}/resolve`
- `PUT /api/alerts/{alert_id}/notes?notes=...`

### Export (CSV)

- `GET /api/alerts/export?format=csv`

The dashboard "Export CSV" button uses this endpoint.

## Notes

- This is a demo-style SIEM project. For production use, restrict CORS origins and secure endpoints.
