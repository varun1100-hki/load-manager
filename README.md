# Inverter Load Manager

FastAPI + SQLite backend, single-page Next.js (React) frontend. Inverter limit: 800W.

## Run

Backend:
```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Frontend (new terminal):
```
cd frontend
npm install
npm run dev        # http://localhost:3000
```
Set `NEXT_PUBLIC_API_URL` if the backend is not on `http://localhost:8000`.

## Layout
- `backend/main.py` – routes only; maps domain errors to HTTP codes.
- `backend/load_manager.py` – register / delete / ON / OFF rules and auto-shed.
- `backend/restore.py` – auto-restore (shed -> on).
- `backend/db.py`, `backend/schema.sql` – SQLite connection and schema.
- `frontend/app/page.js` – the whole screen.

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/appliances` | Full picture: appliances with state, `load`, `remaining`, `capacity` |
| POST | `/appliances` | Register (201). Wattage above 800W is refused (409) since it could never run |
| DELETE | `/appliances/{id}` | Delete, then restore if capacity freed |
| POST | `/appliances/{id}/on` | Request ON (auto-shed if needed) |
| POST | `/appliances/{id}/off` | Request OFF (then auto-restore) |

Mutating calls return `{ events: [...], capacity, load, remaining, appliances }`.
`events` lists everything the system did ("Fan shed to make room for Fridge").
Errors: `404` unknown appliance, `409` request rejected, `422` invalid input. The body is
`{"detail": {"reason": "..."}}` with a plain-language explanation.

## How the rules are kept
- **Never over 800W, even for a moment:** each request runs in one SQLite transaction
  opened with `BEGIN IMMEDIATE`, so requests are serialized, and all changes (sheds + the
  turn-on) commit together or not at all.
- **Rejection changes nothing:** feasibility is checked *before* any write. Only appliances with a
  strictly lower priority are ever candidates, so equal/higher priority is never shed.
- **Three states in one column:** `state` is `on | off | shed` (CHECK constraint). `shed_at`
  stores when an appliance was shed. Because both are stored, not computed, a restart
  restores the exact picture.
- **Shed vs off:** switching OFF a shed appliance sets it to `off`, so it stops waiting.
  Restore only ever looks at `shed` rows, so `off` appliances never come back on their own.

## Restore order and why
Shed appliances are restored by **priority (1 first), then the one shed longest ago**, and an
appliance that doesn't fit is **skipped**, so the next one that fits can still use the free watts.

Why:
- Important things (fridge) should come back before unimportant ones.
- Among equals, oldest-shed-first is fair: whoever has waited longest goes first.
- Skipping instead of stopping avoids leaving watts idle just because one large appliance
  is waiting. In the walkthrough, Iron (700W) stays shed with 500W free, and nothing else is blocked.

Trade-off: a small low-priority appliance can take watts that a large higher-priority one is
waiting for (the large one can be starved while small ones keep fitting). The alternative, strict
priority (stop at the first that doesn't fit), avoids that but wastes capacity. For a home inverter
I judged using the available power the better default. Switching to strict is a one-line change
(`continue` -> `break`) in `restore.py`.
