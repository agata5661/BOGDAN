
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from openai import OpenAI
import os
import requests

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOKEN = None
PAGE_TOKEN = None

@app.get("/")
def root():
    return {"agent": "dziala"}

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

@app.get("/gmail")
def gmail():
    access_token = TOKEN["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers=headers
    )

    return r.json()

@app.get("/calendar")
def calendar():
    access_token = TOKEN["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    r = requests.get(
        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
        headers=headers
    )

    return r.json()

@app.get("/sort-mails-ai")
def sort_mails_ai():
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
        label["name"]: label["id"]
        for label in labels_resp.get("labels", [])
    }

    mails = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=5",
        headers=headers
    ).json()

    results = []

    for m in mails.get("messages", []):
        msg = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
            headers=headers
        ).json()

        snippet = msg.get("snippet", "")

        ai = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
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
- jeśli email jest reklamą, promocją, newsletterem, ofertą marketingową, rabatem, kampanią, mailingiem → Reklamy
- reklamy/promocje/newslettery NIGDY nie mogą trafić do Do_odpisania
- Do_odpisania wybieraj tylko, jeśli mail jest od realnej osoby i wyraźnie oczekuje odpowiedzi

- InPost, DPD, DHL, UPS, FedEx, GLS, Orlen Paczka, Poczta Polska, kurier, paczkomat, tracking, numer przesyłki, dostawa, odbiór paczki → Przesyłki

- pilne, awarie, ważne info, deadline, termin → Pilne

- faktura, faktury, invoice, rachunek, rachunki, płatność, płatności, rozliczenia, opłata, paragon, paragony, e-paragon, eparagon → Rachunki
- e-paragon z Allegro, faktura z Allegro → Rachunki

- zamówienia, zakupy, allegro, temu, amazon, eobuwie, pyszne.pl, pyszne, sklep, koszyk, payu, stripe, paypal → Zakupy
- UWAGA: jeśli mail z Allegro zawiera fakturę lub paragon → Rachunki (ma pierwszeństwo nad Zakupy)

- giełda, krypto, trading, broker, forex, akcje, fibonacci → Trading

- SRK, Spółka Restrukturyzacji Kopalń, mail od a.mirga@srk.com.pl, OLX, olx.pl → Praca
- rekrutacja, praca, oferta pracy, klient, projekt, ogłoszenie, aplikacja, CV → Praca

- ChatGPT, OpenAI, Open AI, Railway, GitHub, Bithub, API key, deploy, deployment, build failed, crash, logs, tokeny, billing OpenAI → ChatGPT

Zwróć tylko nazwę kategorii.
"""
                },
                {
                    "role": "user",
                    "content": snippet
                }
            ]
        )

        category = ai.choices[0].message.content.strip()

        label_map = {
            "Ważne": "Ważne",
            "Rachunki": "Rachunki",
            "Zakupy": "Zakupy",
            "Reklamy": "Reklamy",
            "Praca": "Praca",
            "Do_odpisania": "Do odpisania",
            "Przesyłki": "Przesyłki",
            "Trading": "Trading",
            "ChatGPT": "ChatGPT",
        }

        label_name = label_map.get(category)
        label_id = existing_labels.get(label_name)

        label_applied = False

        if label_id:
            modify_resp = requests.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}/modify",
                headers=headers,
                json={
                    "addLabelIds": [label_id]
                }
            )

            if modify_resp.status_code in [200, 204]:
                label_applied = True

        results.append({
            "mail": snippet,
            "category": category,
            "label_name": label_name,
            "label_applied": label_applied
        })

    return results

@app.get("/sort-all-mails-ai")
def sort_all_mails_ai():
    global PAGE_TOKEN

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
        label["name"]: label["id"]
        for label in labels_resp.get("labels", [])
    }

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=5&q=-in:trash -in:spam"

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

        ai = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
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
- InPost, DPD, DHL, UPS, FedEx, GLS, Orlen Paczka, Poczta Polska, kurier, paczkomat, tracking, numer przesyłki, dostawa, odbiór paczki → Przesyłki
- reklamy, promocje, newslettery → Reklamy
- pilne, awarie, ważne info → Ważne
- faktury, płatności, rozliczenia → Rachunki
- zamówienia, zakupy, paragony → Zakupy
- giełda, krypto, trading, broker, forex, akcje → Trading
- rekrutacja, praca, oferta pracy, klient, projekt → Praca
- wiadomość wymaga odpowiedzi → Do_odpisania

Zwróć tylko nazwę kategorii.
"""
                },
                {
                    "role": "user",
                    "content": snippet
                }
            ]
        )

        category = ai.choices[0].message.content.strip()

        label_map = {
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

        label_name = label_map.get(category)
        label_id = existing_labels.get(label_name)

        label_applied = False

        if label_id:
            modify_resp = requests.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}/modify",
                headers=headers,
                json={
                    "addLabelIds": [label_id]
                }
            )

            if modify_resp.status_code in [200, 204]:
                label_applied = True

        results.append({
            "category": category,
            "label_name": label_name,
            "label_applied": label_applied,
            "mail": snippet
        })

    return {
        "processed": len(results),
        "done": PAGE_TOKEN is None,
        "next_page_exists": PAGE_TOKEN is not None,
        "results": results
    }

@app.get("/run-agent")
def run_agent():
    return sort_all_mails_ai()
