import logging

from fastapi import FastAPI
from pydantic import BaseModel


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
