
import sqlite3
from datetime import date

class Database:
    def __init__(self, path):
        self.path = path
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    pokedata_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    city TEXT NOT NULL,
                    region TEXT NOT NULL,
                    address TEXT,
                    organizer TEXT,
                    url TEXT,
                    source_message_id TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            con.commit()

    def upsert_event(self, e):
        with self._connect() as con:
            old = con.execute(
                "SELECT * FROM events WHERE pokedata_id = ?", (e["pokedata_id"],)
            ).fetchone()
            con.execute("""
                INSERT INTO events
                (pokedata_id,type,name,date,city,region,address,organizer,url,source_message_id,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(pokedata_id) DO UPDATE SET
                    type=excluded.type,
                    name=excluded.name,
                    date=excluded.date,
                    city=excluded.city,
                    region=excluded.region,
                    address=excluded.address,
                    organizer=excluded.organizer,
                    url=excluded.url,
                    source_message_id=excluded.source_message_id,
                    updated_at=excluded.updated_at
            """, (
                e["pokedata_id"], e["type"], e["name"], e["date"], e["city"],
                e["region"], e["address"], e["organizer"], e["url"],
                e["source_message_id"]
            ))
            con.commit()
            new = con.execute(
                "SELECT * FROM events WHERE pokedata_id = ?", (e["pokedata_id"],)
            ).fetchone()
        return old is None or dict(old) != dict(new)

    def get_all_events(self):
        with self._connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM events ORDER BY date, city, name"
            ).fetchall()]

    def get_upcoming(self, limit=15, regions=None):
        today = date.today().isoformat()
        with self._connect() as con:
            if regions:
                marks = ",".join("?" for _ in regions)
                args = [today] + list(regions) + [limit]
                rows = con.execute(
                    f"SELECT * FROM events WHERE date >= ? AND lower(region) IN ({marks}) ORDER BY date, city, name LIMIT ?",
                    args
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM events WHERE date >= ? ORDER BY date, city, name LIMIT ?",
                    (today, limit)
                ).fetchall()
            return [dict(r) for r in rows]
