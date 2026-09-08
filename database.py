import sqlite3
from datetime import date

class Database:
    def __init__(self,path):
        self.path=path; self._init()
    def _connect(self):
        con=sqlite3.connect(self.path); con.row_factory=sqlite3.Row; return con
    def _init(self):
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS events(
                pokedata_id TEXT PRIMARY KEY,type TEXT NOT NULL,name TEXT NOT NULL,date TEXT NOT NULL,
                city TEXT NOT NULL,region TEXT NOT NULL,address TEXT,organizer TEXT,url TEXT,
                source_message_id TEXT,updated_at TEXT NOT NULL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS attendance(
                event_id TEXT NOT NULL,user_id TEXT NOT NULL,user_name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN('yes','maybe','no')),updated_at TEXT NOT NULL,
                PRIMARY KEY(event_id,user_id),FOREIGN KEY(event_id) REFERENCES events(pokedata_id))""")
            con.commit()
    def upsert_event(self,e):
        with self._connect() as con:
            old=con.execute("SELECT * FROM events WHERE pokedata_id=?",(e["pokedata_id"],)).fetchone()
            con.execute("""INSERT INTO events
                (pokedata_id,type,name,date,city,region,address,organizer,url,source_message_id,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(pokedata_id) DO UPDATE SET type=excluded.type,name=excluded.name,date=excluded.date,
                city=excluded.city,region=excluded.region,address=excluded.address,organizer=excluded.organizer,
                url=excluded.url,source_message_id=excluded.source_message_id,updated_at=excluded.updated_at""",
                (e["pokedata_id"],e["type"],e["name"],e["date"],e["city"],e["region"],e["address"],e["organizer"],e["url"],e["source_message_id"]))
            con.commit(); new=con.execute("SELECT * FROM events WHERE pokedata_id=?",(e["pokedata_id"],)).fetchone()
        return old is None or dict(old)!=dict(new)
    def get_all_events(self):
        with self._connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM events ORDER BY date,city,name")]
    def get_upcoming(self,limit=15,regions=None):
        today=date.today().isoformat()
        with self._connect() as con:
            if regions:
                marks=",".join("?" for _ in regions)
                rows=con.execute(f"SELECT * FROM events WHERE date>=? AND lower(region) IN({marks}) ORDER BY date,city,name LIMIT ?",[today,*regions,limit]).fetchall()
            else:
                rows=con.execute("SELECT * FROM events WHERE date>=? ORDER BY date,city,name LIMIT ?",(today,limit)).fetchall()
            return [dict(r) for r in rows]
    def set_attendance(self,event_id,user_id,user_name,status):
        if status not in {"yes","maybe","no"}: raise ValueError("Stato non valido")
        with self._connect() as con:
            con.execute("""INSERT INTO attendance(event_id,user_id,user_name,status,updated_at)
                VALUES(?,?,?,?,datetime('now'))
                ON CONFLICT(event_id,user_id) DO UPDATE SET user_name=excluded.user_name,status=excluded.status,updated_at=excluded.updated_at""",
                (event_id,str(user_id),user_name,status)); con.commit()
    def get_attendance_counts(self,event_id):
        out={"yes":0,"maybe":0,"no":0}
        with self._connect() as con:
            for r in con.execute("SELECT status,COUNT(*) n FROM attendance WHERE event_id=? GROUP BY status",(event_id,)):
                out[r["status"]]=r["n"]
        return out
    def get_attendees(self,event_id,status):
        with self._connect() as con:
            return [r["user_name"] for r in con.execute(
                "SELECT user_name FROM attendance WHERE event_id=? AND status=? ORDER BY user_name COLLATE NOCASE",(event_id,status))]
