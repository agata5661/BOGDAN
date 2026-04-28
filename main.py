from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import os

app = FastAPI()

@app.get("/")
def root():
    return {"hello":"działa"}

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
    return {"success":"Google connected", "code": code}
