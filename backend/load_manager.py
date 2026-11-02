
from datetime import datetime, timezone

from restore import CAPACITY, current_load, restore_shed


class NotFound(Exception):
    pass


class Rejected(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _get(conn, appliance_id):
    row = conn.execute("SELECT * FROM appliances WHERE id = ?", (appliance_id,)).fetchone()
    if row is None:
        raise NotFound(f"Appliance {appliance_id} does not exist")
    return row


def snapshot(conn):
    rows = conn.execute("SELECT * FROM appliances ORDER BY priority, id").fetchall()
    load = current_load(conn)
    return {
        "capacity": CAPACITY,
        "load": load,
        "remaining": CAPACITY - load,
        "appliances": [
            {k: r[k] for k in ("id", "name", "wattage", "priority", "state")} for r in rows
        ],
    }


def register(conn, name, wattage, priority):
    if wattage > CAPACITY:
        raise Rejected(f"{wattage}W is above the inverter limit of {CAPACITY}W; it could never run")
    cur = conn.execute(
        "INSERT INTO appliances (name, wattage, priority) VALUES (?, ?, ?)",
        (name, wattage, priority),
    )
    return cur.lastrowid


def delete(conn, appliance_id):
    a = _get(conn, appliance_id)
    conn.execute("DELETE FROM appliances WHERE id = ?", (appliance_id,))
    events = [f"{a['name']} deleted"]
    return events + restore_shed(conn)


def turn_on(conn, appliance_id):
    a = _get(conn, appliance_id)
    if a["state"] == "on":
        return [f"{a['name']} is already on"]

    load = current_load(conn)
    needed = load + a["wattage"] - CAPACITY  # watts that must be freed

    shed_events = []
    if needed > 0:
        
        candidates = conn.execute(
            "SELECT * FROM appliances WHERE state = 'on' AND priority > ? "
            "ORDER BY priority DESC, wattage DESC, id",
            (a["priority"],),
        ).fetchall()
        if sum(c["wattage"] for c in candidates) < needed:
            raise Rejected(
                f"Cannot turn on {a['name']} ({a['wattage']}W, priority {a['priority']}): "
                f"{CAPACITY - load}W free and everything of lower priority "
                f"would free only {sum(c['wattage'] for c in candidates)}W. Nothing was changed."
            )
        now = datetime.now(timezone.utc).isoformat()
        for c in candidates:
            if needed <= 0:
                break
            conn.execute(
                "UPDATE appliances SET state = 'shed', shed_at = ? WHERE id = ?",
                (now, c["id"]),
            )
            needed -= c["wattage"]
            shed_events.append(f"{c['name']} shed to make room for {a['name']}")

    conn.execute(
        "UPDATE appliances SET state = 'on', shed_at = NULL WHERE id = ?", (appliance_id,)
    )
    events = shed_events + [f"{a['name']} turned on"]
    if shed_events:
        events += restore_shed(conn)
    return events


def turn_off(conn, appliance_id):
    a = _get(conn, appliance_id)
    if a["state"] == "off":
        return [f"{a['name']} is already off"]
    was_shed = a["state"] == "shed"
    conn.execute(
        "UPDATE appliances SET state = 'off', shed_at = NULL WHERE id = ?", (appliance_id,)
    )
    msg = f"{a['name']} switched off" + (" (no longer waiting to be restored)" if was_shed else "")
    return [msg] + restore_shed(conn)
