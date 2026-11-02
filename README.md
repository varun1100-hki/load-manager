# Inverter Load Manager

FastAPI + SQLite backend, single-page Next.js (React) frontend. Inverter limit: 800W.

## Run




backend 
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

frontend

npm install
npm run dev