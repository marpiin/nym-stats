-- One row per successful reading. UNIQUE (node_id, day) rejects a second
-- reading of the same node on the same UTC day.
CREATE TABLE IF NOT EXISTS reading (
    node_id            INTEGER NOT NULL,
    taken_at           TEXT    NOT NULL,  -- ISO 8601, UTC
    day                TEXT    NOT NULL CHECK (day = substr(taken_at, 1, 10)),
    operator_nym       REAL    NOT NULL,  -- pledge plus compounded operator rewards
    pledge_nym         REAL    NOT NULL,
    delegates_nym      REAL    NOT NULL,
    profit_margin      REAL    NOT NULL,  -- fraction, 0.2 = 20 %
    operating_cost_nym REAL    NOT NULL,  -- per rewarding interval
    performance        REAL,              -- 0 to 1
    uptime_percent     INTEGER,
    uptime_date        TEXT,
    UNIQUE (node_id, day)
);

-- Every fetch, successful or not, so alerts can count consecutive failures.
CREATE TABLE IF NOT EXISTS fetch_attempt (
    id           INTEGER PRIMARY KEY,
    node_id      INTEGER NOT NULL,
    attempted_at TEXT    NOT NULL,  -- ISO 8601, UTC
    error        TEXT               -- NULL when the fetch succeeded
);
