"""
TOOLBOX — FastAPI Backend
Запуск: uvicorn main:app --reload
"""

import hashlib
import json
import csv
import io
import re
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="TOOLBOX API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "toolbox.db"

# ─── Database ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snippets (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                title     TEXT    NOT NULL,
                content   TEXT    NOT NULL,
                language  TEXT    DEFAULT 'text',
                created_at TEXT   DEFAULT (datetime('now')),
                updated_at TEXT   DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

init_db()

# ─── Pydantic models ──────────────────────────────────────────────────────────
class HashRequest(BaseModel):
    text: str
    algorithms: List[str] = ["md5", "sha1", "sha256", "sha512"]

class DiffRequest(BaseModel):
    textA: str
    textB: str

class ConvertJsonCsvRequest(BaseModel):
    data: list

class ConvertCsvJsonRequest(BaseModel):
    csv: str

class SnippetCreate(BaseModel):
    title: Optional[str] = None
    content: str
    language: str = "text"

class SnippetUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None

# ─── /api/health ─────────────────────────────────────────────────────────────
import time
_start = time.time()

@app.get("/api/health")
def health():
    return {"status": "ok", "uptime": round(time.time() - _start, 1), "backend": "FastAPI + SQLite"}

# ─── /api/hash ───────────────────────────────────────────────────────────────
@app.post("/api/hash")
def compute_hashes(req: HashRequest):
    result = {}
    data = req.text.encode("utf-8")
    supported = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
        "sha224": hashlib.sha224,
        "sha384": hashlib.sha384,
        "sha3_256": hashlib.sha3_256,
        "sha3_512": hashlib.sha3_512,
        "blake2b": hashlib.blake2b,
    }
    for algo in req.algorithms:
        if algo in supported:
            result[algo] = supported[algo](data).hexdigest()
        else:
            result[algo] = "unsupported"
    return result

# ─── /api/diff ───────────────────────────────────────────────────────────────
def compute_lcs(a: list, b: list) -> list:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    lcs = []
    i, j = m, n
    while i > 0 and j > 0:
        if a[i-1] == b[j-1]:
            lcs.append((i-1, j-1))
            i -= 1; j -= 1
        elif dp[i-1][j] > dp[i][j-1]:
            i -= 1
        else:
            j -= 1
    return list(reversed(lcs))

def build_diff(a: list, b: list, lcs: list) -> list:
    result = []
    ai = bi = li = 0
    while li < len(lcs):
        la, lb = lcs[li]
        while ai < la:
            result.append({"type": "remove", "lineA": ai + 1, "lineB": None, "text": a[ai]})
            ai += 1
        while bi < lb:
            result.append({"type": "add", "lineA": None, "lineB": bi + 1, "text": b[bi]})
            bi += 1
        result.append({"type": "equal", "lineA": ai + 1, "lineB": bi + 1, "text": a[ai]})
        ai += 1; bi += 1; li += 1
    while ai < len(a):
        result.append({"type": "remove", "lineA": ai + 1, "lineB": None, "text": a[ai]})
        ai += 1
    while bi < len(b):
        result.append({"type": "add", "lineA": None, "lineB": bi + 1, "text": b[bi]})
        bi += 1
    return result

@app.post("/api/diff")
def diff_texts(req: DiffRequest):
    lines_a = req.textA.split("\n")
    lines_b = req.textB.split("\n")
    lcs  = compute_lcs(lines_a, lines_b)
    diff = build_diff(lines_a, lines_b, lcs)
    stats = {
        "added":   sum(1 for d in diff if d["type"] == "add"),
        "removed": sum(1 for d in diff if d["type"] == "remove"),
        "equal":   sum(1 for d in diff if d["type"] == "equal"),
    }
    return {"diff": diff, "stats": stats}

# ─── /api/convert ────────────────────────────────────────────────────────────
@app.post("/api/convert/json-csv")
def json_to_csv(req: ConvertJsonCsvRequest):
    if not isinstance(req.data, list):
        raise HTTPException(400, "Expected a JSON array")
    keys = list(dict.fromkeys(k for row in req.data for k in row.keys()))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(req.data)
    return {"csv": output.getvalue()}

@app.post("/api/convert/csv-json")
def csv_to_json(req: ConvertCsvJsonRequest):
    reader = csv.DictReader(io.StringIO(req.csv.strip()))
    rows = [dict(row) for row in reader]
    return {"json": rows}

@app.post("/api/convert/file")
async def convert_file(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    name = file.filename or ""
    ext  = Path(name).suffix.lower()

    if ext == ".json":
        try:
            data = json.loads(text)
            if not isinstance(data, list):
                return {"result": text, "type": "json", "note": "Not an array"}
            keys = list(dict.fromkeys(k for row in data for k in row.keys()))
            out  = io.StringIO()
            csv.DictWriter(out, fieldnames=keys, extrasaction="ignore").writeheader()
            csv.DictWriter(out, fieldnames=keys, extrasaction="ignore").writerows(data)
            # redo properly
            out2 = io.StringIO()
            w = csv.DictWriter(out2, fieldnames=keys, extrasaction="ignore")
            w.writeheader(); w.writerows(data)
            return {"result": out2.getvalue(), "type": "csv", "filename": name.replace(".json", ".csv")}
        except Exception as e:
            raise HTTPException(400, str(e))

    elif ext == ".csv":
        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = [dict(r) for r in reader]
            return {"result": json.dumps(rows, ensure_ascii=False, indent=2), "type": "json", "filename": name.replace(".csv", ".json")}
        except Exception as e:
            raise HTTPException(400, str(e))

    elif ext in (".md", ".markdown"):
        return {"result": text, "type": "markdown", "filename": name}

    return {"result": text, "type": "text"}

# ─── /api/snippets ───────────────────────────────────────────────────────────
@app.post("/api/snippets")
def create_snippet(body: SnippetCreate):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO snippets (title, content, language) VALUES (?, ?, ?)",
            (body.title or f"Сниппет", body.content, body.language)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM snippets WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@app.get("/api/snippets")
def list_snippets():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM snippets ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

@app.get("/api/snippets/{snippet_id}")
def get_snippet(snippet_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM snippets WHERE id=?", (snippet_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return dict(row)

@app.put("/api/snippets/{snippet_id}")
def update_snippet(snippet_id: int, body: SnippetUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM snippets WHERE id=?", (snippet_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        fields = {k: v for k, v in body.dict().items() if v is not None}
        fields["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE snippets SET {set_clause} WHERE id=?", (*fields.values(), snippet_id))
        conn.commit()
        updated = conn.execute("SELECT * FROM snippets WHERE id=?", (snippet_id,)).fetchone()
    return dict(updated)

@app.delete("/api/snippets/{snippet_id}")
def delete_snippet(snippet_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM snippets WHERE id=?", (snippet_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        conn.execute("DELETE FROM snippets WHERE id=?", (snippet_id,))
        conn.commit()
    return {"ok": True}

# ─── /api/text/* ─────────────────────────────────────────────────────────────
class TextRequest(BaseModel):
    text: str

class ReplaceRequest(BaseModel):
    text: str
    find: str
    replace: str
    is_regex: bool = False

@app.post("/api/text/stats")
def text_stats(req: TextRequest):
    t = req.text
    words = len(t.split()) if t.strip() else 0
    return {
        "chars": len(t),
        "chars_no_spaces": len(t.replace(" ", "").replace("\n", "").replace("\t", "")),
        "words": words,
        "lines": len(t.splitlines()) if t else 0,
        "sentences": len(re.findall(r"[.!?]+", t)),
        "reading_minutes": max(1, round(words / 200)),
        "paragraphs": len([p for p in t.split("\n\n") if p.strip()]),
    }

@app.post("/api/text/replace")
def text_replace(req: ReplaceRequest):
    try:
        if req.is_regex:
            result = re.sub(req.find, req.replace, req.text)
        else:
            result = req.text.replace(req.find, req.replace)
        return {"result": result}
    except re.error as e:
        raise HTTPException(400, f"Regex error: {e}")

# ─── Static / SPA ────────────────────────────────────────────────────────────
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>TOOLBOX</h1><p>Положи index.html в папку static/</p>"

# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
