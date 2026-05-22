from fastapi import Request
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
from openai import OpenAI
import os
import requests

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOKEN = None
PAGE_TOKEN = None

# =========================
# KONFIG
# =========================

PROMPT = """
Klasyfikuj email do jednej kategorii:

Pilne
Rachunki
Zakupy
Reklamy
Praca
Do_odpisania
Przesyłki
Trading
ChatGPT

Zasady:
- reklamy, promocje, newslettery → Reklamy
- reklamy NIGDY nie mogą trafić do Do_odpisania

- jeśli mail wymaga odpowiedzi → Do_odpisania

- InPost, DPD, DHL, UPS, FedEx → Przesyłki

- pilne, deadline → Pilne

- faktura, rachunek, płatność → Rachunki

- zamówienie, allegro, temu, payu → Zakupy

- trading, krypto, fibonacci → Trading

- SRK, OLX, praca → Praca

- ChatGPT, OpenAI, Railway, GitHub → ChatGPT

Zwróć tylko nazwę kategorii.
"""

LABEL_MAP = {
    "Pilne": "Pilne",
    "Rachunki": "Rachunki",
    "Zakupy": "Zakupy",
    "Reklamy": "Reklamy",
    "Praca": "Praca",
    "Do_odpisania": "Do odpisania",
    "Przesyłki": "Przesyłki",
    "Trading": "Trading",
    "ChatGPT": "ChatGPT",
}

# =========================
# PODSTAWY
# =========================

@app.get("/", response_class=HTMLResponse)
def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/auth/google")
def auth_google():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar"
        "&access_type=offline"
        "&prompt=consent"
    )
    return RedirectResponse(url)

@app.get("/oauth/callback")
def callback(code: str):
    global TOKEN

    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
            "grant_type": "authorization_code"
        }
    )

    TOKEN = r.json()
    return {"success": True, "message": "Google connected"}

# =========================
# FUNKCJA AI
# =========================

def classify_and_label(m_id, snippet, headers, existing_labels):
    try:
        ai = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": snippet}
            ]
        )

        category = ai.choices[0].message.content.strip()

    except Exception as e:
        return {
            "mail": snippet,
            "error": str(e)
        }

    label_name = LABEL_MAP.get(category)
    label_id = existing_labels.get(label_name)

    applied = False

    if label_id:
        requests.post(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m_id}/modify",
            headers=headers,
            json={"addLabelIds": [label_id]}
        )
        applied = True

    return {
        "mail": snippet,
        "category": category,
        "label_name": label_name,
        "label_applied": applied
    }

# =========================
# SORTOWANIE
# =========================

@app.get("/sort-all-mails-ai")
def sort_all_mails_ai():
    global PAGE_TOKEN

    if not TOKEN or "access_token" not in TOKEN:
        return {"error": "Brak logowania Google"}

    access_token = TOKEN["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    labels_resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/labels",
        headers=headers
    ).json()

    existing_labels = {
        l["name"]: l["id"] for l in labels_resp.get("labels", [])
    }

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=5"

    if PAGE_TOKEN:
        url += f"&pageToken={PAGE_TOKEN}"

    mails = requests.get(url, headers=headers).json()

    PAGE_TOKEN = mails.get("nextPageToken")

    results = []

    for m in mails.get("messages", []):
        msg = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
            headers=headers
        ).json()

        snippet = msg.get("snippet", "")

        # 🔥 TU BYŁ BŁĄD — JUŻ NAPRAWIONE
        if not snippet or len(snippet.strip()) < 10:
            continue

        result = classify_and_label(
            m["id"], snippet, headers, existing_labels
        )

        results.append(result)

    return {
        "processed": len(results),
        "done": PAGE_TOKEN is None,
        "results": results
    }

@app.get("/run-agent")
def run_agent():
    return sort_all_mails_ai()

@app.post("/assistant")
async def assistant(request: Request):

    data = await request.json()

    text = data.get("message", "")

    return {
        "message": f"Otrzymałem polecenie: {text}"
    }
