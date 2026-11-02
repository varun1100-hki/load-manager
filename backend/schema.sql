-- state: 'on' = running, 'off' = user switched it off, 'shed' = user wants it on, system paused it.
-- shed_at is set only while state = 'shed'; restore uses it as a tiebreaker (oldest shed first).
CREATE TABLE IF NOT EXISTS appliances (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL,
    wattage  INTEGER NOT NULL CHECK (wattage > 0),
    priority INTEGER NOT NULL CHECK (priority >= 1),
    state    TEXT    NOT NULL DEFAULT 'off' CHECK (state IN ('on', 'off', 'shed')),
    shed_at  TEXT
);
