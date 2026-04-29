from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import os
import requests

app = FastAPI()

TOKEN=None

@app.get("/")
def root():
    return {"agent":"dziala"}

@app.get("/auth/google")
def auth_google():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    url=(
      "https://accounts.google.com/o/oauth2/v2/auth"
      f"?client_id={client_id}"
      f"&redirect_uri={redirect_uri}"
      "&response_type=code"
      "&scope=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar"
      "&access_type=offline"
      "&prompt=consent"
    )
    return RedirectResponse(url)

@app.get("/oauth/callback")
def callback(code:str):
    global TOKEN

    r=requests.post(
      "https://oauth2.googleapis.com/token",
      data={
        "code":code,
        "client_id":os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret":os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri":os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type":"authorization_code"
      }
    )

    TOKEN=r.json()
    return TOKEN

@app.get("/gmail")
def gmail():
    access_token=TOKEN["access_token"]

    headers={
      "Authorization":f"Bearer {access_token}"
    }

    r=requests.get(
      "https://gmail.googleapis.com/gmail/v1/users/me/messages",
      headers=headers
    )

    return r.json()

@app.get("/calendar")
def calendar():
    access_token=TOKEN["access_token"]

    headers={
      "Authorization":f"Bearer {access_token}"
    }

    r=requests.get(
      "https://www.googleapis.com/calendar/v3/users/me/calendarList",
      headers=headers
    )

    return r.json()
