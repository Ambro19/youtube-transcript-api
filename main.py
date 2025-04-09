# ✅ STEP 1: UPDATE FastAPI BACKEND (CLOUD) with Auth
# File: main.py (in transcript_api)

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from passlib.hash import bcrypt
import sqlite3
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# DATABASE SETUP
# ----------------------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class AuthRequest(BaseModel):
    username: str
    password: str

class TranscriptRequest(BaseModel):
    video_id: str

@app.post("/register")
def register(data: AuthRequest):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (data.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = bcrypt.hash(data.password)
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (data.username, hashed_password))
    conn.commit()
    conn.close()
    return {"message": "Registration successful"}

@app.post("/login")
def login(data: AuthRequest):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (data.username,))
    row = c.fetchone()
    conn.close()
    if row and bcrypt.verify(data.password, row[0]):
        return {"message": "Login successful"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/transcript")
def get_transcript(data: TranscriptRequest):
    try:
        #transcript = YouTubeTranscriptApi.get_transcript(data.video_id, languages=['en'])
        transcript = requests.post()
        full_text = " ".join([seg.get("text", "") for seg in transcript])
        return {"transcript": full_text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


