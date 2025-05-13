from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from passlib.hash import pbkdf2_sha256
import sqlite3
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import stripe
import requests

from fastapi.staticfiles import StaticFiles

app = FastAPI()  # ✅ Define app first

app.mount("/static", StaticFiles(directory="static"), name="static")  # ✅ Then use it


from dotenv import load_dotenv
load_dotenv()  # This loads all key=value pairs from `.env` into os.environ

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

DOMAIN = "https://youtube-transcript-api-3.onrender.com" 


from fastapi.staticfiles import StaticFiles

app = FastAPI()  # ✅ Define app first

app.mount("/static", StaticFiles(directory="static"), name="static")  # ✅ Then use it



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
            password TEXT NOT NULL,
            subscription TEXT DEFAULT 'inactive',
            expiry TEXT
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
    hashed_password = pbkdf2_sha256.hash(data.password)
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (data.username, hashed_password))
    conn.commit()
    conn.close()
    return {"message": "Registration successful"}

@app.post("/login")
def login(data: AuthRequest):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password, subscription, expiry FROM users WHERE username = ?", (data.username,))
    row = c.fetchone()
    conn.close()
    if row and pbkdf2_sha256.verify(data.password, row[0]):
        return {
            "message": "Login successful",
            "subscription": row[1],
            "expiry": row[2]
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/transcript")
def get_transcript(data: TranscriptRequest):
    
     # Simulate basic authorization (normally you'd use a JWT token here)
    username = data.video_id.split("|")[0]  # temporary hack for demo: pass "username|video_id"
    video_id = data.video_id.split("|")[1]

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT subscription, expiry FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if not row or row[0] != "active" or (row[1] and datetime.now() > datetime.fromisoformat(row[1])):
        raise HTTPException(status_code=403, detail="Your subscription has expired or is inactive.")

    # YouTube Video ID extraction logic...  
    if "/watch" in video_id and "v=" in video_id:
        video_id = video_id.split("v=")[-1].split("&")[0]

    try:
        transcript = YouTubeTranscriptApi.get_transcript(data.video_id, languages=['en'])
        full_text = " ".join([seg.get("text", "") for seg in transcript])
        return {"transcript": full_text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class SubscriptionRequest(BaseModel):
    username: str

@app.post("/subscribe")
def subscribe(data: SubscriptionRequest):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    expiry = (datetime.now() + timedelta(days=30)).isoformat()
    c.execute("""
        UPDATE users SET subscription = 'active', expiry = ?
        WHERE username = ?
    """, (expiry, data.username))
    conn.commit()
    conn.close()
    return {"message": f"Subscription activated until {expiry}"}

class StripeRequest(BaseModel):
    username: str

@app.post("/create-checkout-session")
def create_checkout_session(data: StripeRequest):
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "YouTubeTransDownloader Pro"},
                    "unit_amount": 785, #299,  # $2.99
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{DOMAIN}/static/success.html?username={data.username}",
            cancel_url=f"{DOMAIN}/static/cancel.html",
        )
        return {"url": checkout_session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            success_url = session["success_url"]
            username = success_url.split("username=")[-1]

            from datetime import datetime, timedelta
            expiry = (datetime.now() + timedelta(days=30)).isoformat()

            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("UPDATE users SET subscription = 'active', expiry = ? WHERE username = ?", (expiry, username))
            conn.commit()
            conn.close()
    except stripe.error.SignatureVerificationError as e:
        return JSONResponse(status_code=400, content={"error": "Invalid signature"})

    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return {"status": "success"}
