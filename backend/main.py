from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import load_manager as lm
from db import init_db, transaction

app = FastAPI(title="Inverter Load Manager")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


class NewAppliance(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    wattage: int = Field(gt=0)
    priority: int = Field(ge=1)


def run(action, *args):
    """Run a rule inside one transaction; map domain errors to HTTP codes.
    Returns the events plus the fresh full picture."""
    try:
        with transaction() as conn:
            events = action(conn, *args)
            return {"events": events, **lm.snapshot(conn)}
    except lm.NotFound as e:
        raise HTTPException(404, detail={"reason": str(e)})
    except lm.Rejected as e:
        raise HTTPException(409, detail={"reason": e.reason})


@app.get("/appliances")
def get_all():
    with transaction() as conn:
        return lm.snapshot(conn)


@app.post("/appliances", status_code=201)
def create(body: NewAppliance):
    def action(conn):
        new_id = lm.register(conn, body.name.strip(), body.wattage, body.priority)
        return [f"{body.name.strip()} registered (id {new_id})"]
    return run(action)


@app.delete("/appliances/{appliance_id}")
def remove(appliance_id: int):
    return run(lm.delete, appliance_id)


@app.post("/appliances/{appliance_id}/on")
def on(appliance_id: int):
    return run(lm.turn_on, appliance_id)


@app.post("/appliances/{appliance_id}/off")
def off(appliance_id: int):
    return run(lm.turn_off, appliance_id)
