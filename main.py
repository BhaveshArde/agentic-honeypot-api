from fastapi import FastAPI, Request, Header, HTTPException
import time
import re
import google.generativeai as genai

# ================= CONFIG =================
API_KEY = "hackathon-secret-key"   # send this to judges
GEMINI_API_KEY = "PASTE_YOUR_GEMINI_KEY_HERE"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

app = FastAPI()
sessions = {}  # session memory
# =========================================


# ---------- Scam Detection ----------
def detect_scam(message: str) -> bool:
    keywords = ["upi", "account", "otp", "refund", "click", "verify", "urgent"]
    keyword_match = any(k in message.lower() for k in keywords)

    prompt = f"""
Is the following message a scam?
Reply only YES or NO.

Message:
{message}
"""
    try:
        ai_result = model.generate_content(prompt).text.upper()
        ai_match = "YES" in ai_result
    except:
        ai_match = False

    return keyword_match or ai_match


# ---------- Honeypot AI Agent ----------
def honeypot_agent(message, history):
    prompt = f"""
You are a real Indian person.
You think this message is important.
You are confused but cooperative.

RULES:
- Never accuse
- Never say scam
- Sound human
- Ask innocent questions
- Slowly extract:
  - UPI ID
  - Bank account
  - Payment link

Conversation history:
{history}

Scammer message:
{message}

Reply like a normal human:
"""
    response = model.generate_content(prompt)
    return response.text.strip()


# ---------- Intelligence Extraction ----------
def extract_intelligence(text):
    return {
        "upi_ids": re.findall(r"[a-zA-Z0-9.\-_]+@[a-zA-Z]+", text),
        "bank_accounts": re.findall(r"\b\d{9,18}\b", text),
        "phishing_urls": re.findall(r"https?://[^\s]+", text)
    }


# ---------- MAIN API ----------
@app.post("/scam-hook")
async def scam_hook(
    request: Request,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    data = await request.json()
    session_id = data.get("session_id", "default")
    message = data.get("message", "")

    if session_id not in sessions:
        sessions[session_id] = []

    start_time = time.time()

    sessions[session_id].append(f"Scammer: {message}")

    scam_detected = detect_scam(message)

    agent_reply = ""
    if scam_detected:
        agent_reply = honeypot_agent(message, sessions[session_id])
        sessions[session_id].append(f"User: {agent_reply}")

    intel = extract_intelligence(message)

    return {
        "scam_detected": scam_detected,
        "confidence": 0.95 if scam_detected else 0.1,
        "conversation_turns": len(sessions[session_id]),
        "engagement_duration_sec": int(time.time() - start_time),
        "extracted_intelligence": intel,
        "agent_response": agent_reply
    }


@app.get("/")
def home():
    return {"status": "Agentic Honeypot API Running"}