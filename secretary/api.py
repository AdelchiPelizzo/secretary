import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from secretary.google_auth import create_google_flow, save_google_credentials


logger = logging.getLogger("secretary")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

app = FastAPI()

google_flow = None

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "AI Secretary API",
        "environment": "local"
    }


class ExpectCallRequest(BaseModel):
    caller_number: str
    timestamp: int
    action: str


@app.post("/api/v1/call/expect")
def expect_call(request: ExpectCallRequest):
    logger.info(
        "Expected call received: caller_number=%s timestamp=%s action=%s",
        request.caller_number,
        request.timestamp,
        request.action,
    )

    return {
        "status": "received",
        "caller_number": request.caller_number,
    }

@app.get("/auth/google")
def google_auth():
    global google_flow

    google_flow = create_google_flow()

    authorization_url, state = google_flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    return RedirectResponse(authorization_url)


@app.get("/auth/google/callback")
def google_callback(code: str):
    global google_flow

    if google_flow is None:
        return {
            "status": "error",
            "message": "Google OAuth flow was not initialized."
        }

    google_flow.fetch_token(code=code)

    save_google_credentials(google_flow.credentials)

    return {
        "status": "authorized",
        "message": "Google Calendar authorization successful."
    }
