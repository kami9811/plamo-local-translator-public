"""Local SQLite state. User content stays under the configured data directory."""
from pathlib import Path
import json, sqlite3, threading

class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True,mode=0o700)
        self.path=directory/'state.sqlite3'; self.lock=threading.RLock()
        with self.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,data TEXT,PRIMARY KEY(kind,id)); CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,data TEXT);')
        self.path.chmod(0o600)
    def connect(self):return sqlite3.connect(self.path,timeout=30)
    def put(self,kind,id,data):
        with self.lock,self.connect() as db:db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)',(kind,id,json.dumps(data,ensure_ascii=False)))
    def get(self,kind,id):
        with self.lock,self.connect() as db:row=db.execute('SELECT data FROM records WHERE kind=? AND id=?',(kind,id)).fetchone()
        return json.loads(row[0]) if row else None
    def list(self,kind):
        with self.lock,self.connect() as db:rows=db.execute('SELECT data FROM records WHERE kind=? ORDER BY rowid DESC',(kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]
    def delete(self,kind,id):
        with self.lock,self.connect() as db:db.execute('DELETE FROM records WHERE kind=? AND id=?',(kind,id))
    def cache_get(self,key):
        with self.lock,self.connect() as db:row=db.execute('SELECT data FROM cache WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    def cache_put(self,key,value):
        with self.lock,self.connect() as db:
            db.execute('INSERT OR REPLACE INTO cache VALUES(?,?)',(key,json.dumps(value,ensure_ascii=False)))
            db.execute('DELETE FROM cache WHERE rowid NOT IN (SELECT rowid FROM cache ORDER BY rowid DESC LIMIT 2000)')
    def clear(self):
        with self.lock,self.connect() as db:db.executescript('DELETE FROM records;DELETE FROM cache;')
    def clear_cache(self):
        with self.lock,self.connect() as db:db.execute('DELETE FROM cache')
