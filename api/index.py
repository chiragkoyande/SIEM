import sys
import os


# This stops the "ModuleNotFoundError: backend" error
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import api
sys.modules['backend'] = api
# ------------------------------------------------------

from fastapi import FastAPI
from api.app.models.database import init_db
from api.app.api.routes import router

app = FastAPI()

# Database setup
try:
    init_db()
except Exception as e:
    print(f"Database Warning: {e}")

app.include_router(router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "SentinelWatch SIEM"}
