CAPACITY = 800


def current_load(conn):
    return conn.execute(
        "SELECT COALESCE(SUM(wattage), 0) FROM appliances WHERE state = 'on'"
    ).fetchone()[0]


def restore_shed(conn):
    """Restore order: priority 1 first, then the one shed longest ago (then id).
    An appliance that doesn't fit is skipped (not a blocker), so spare watts are
    used by the next one that fits. Load only grows during the loop, so a single
    pass is enough. Returns a list of human-readable events."""
    events = []
    load = current_load(conn)
    shed = conn.execute(
        "SELECT * FROM appliances WHERE state = 'shed' ORDER BY priority, shed_at, id"
    ).fetchall()
    for a in shed:
        if load + a["wattage"] <= CAPACITY:
            conn.execute(
                "UPDATE appliances SET state = 'on', shed_at = NULL WHERE id = ?",
                (a["id"],),
            )
            load += a["wattage"]
            events.append(f"{a['name']} restored automatically ({a['wattage']}W)")
    return events
