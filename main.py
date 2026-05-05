from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from openai import OpenAI
import os
import requests

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOKEN = None
PAGE_TOKEN = None

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
- jeśli email jest reklamą, promocją, newsletterem, ofertą marketingową, rabatem, kampanią, mailingiem → Reklamy
- reklamy/promocje/newslettery NIGDY nie mogą trafić do Do_odpisania
- Do_odpisania wybieraj tylko, jeśli mail jest od realnej osoby i wyraźnie oczekuje odpowiedzi
- Do_odpisania wybieraj jeśli wiadomość zawiera pytanie, prośbę lub wymaga odpowiedzi

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

@app.get("/")
def root():
    return {"agent": "dziala"}

@app.get("/auth/google")
def
