import os
import time
from pathlib import Path

import pjsua2 as pj
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

print(f"[SIP] Loading .env from: {ENV_FILE}")
load_dotenv(ENV_FILE)

NUMBER = os.getenv("VIVAVOX_NUMBER")
USERNAME = os.getenv("VIVAVOX_USERNAME")
PASSWORD = os.getenv("VIVAVOX_PASSWORD")

SERVER = "sip.vivavox.it"
PORT = 5060


ep = None
acc = None


try:
    print()
    print("[SIP] =========================================")
    print("[SIP] Secretary SIP service")
    print("[SIP] =========================================")
    print(f"[SIP] Number   : {NUMBER}")
    print(f"[SIP] Username : {USERNAME}")
    print(f"[SIP] Server   : {SERVER}:{PORT}")

    # --------------------------------------------------
    # Endpoint
    # --------------------------------------------------

    print("[SIP] Creating PJSIP endpoint...")

    ep = pj.Endpoint()
    ep.libCreate()
    ep.libInit(pj.EpConfig())

    print("[SIP] Endpoint created.")

    # --------------------------------------------------
    # UDP transport
    # --------------------------------------------------

    print("[SIP] Creating UDP transport...")

    tc = pj.TransportConfig()
    tc.port = PORT

    ep.transportCreate(
        pj.PJSIP_TRANSPORT_UDP,
        tc
    )

    print("[SIP] UDP transport created.")

    # --------------------------------------------------
    # Start
    # --------------------------------------------------

    ep.libStart()

    print("[SIP] PJSIP started.")

    # --------------------------------------------------
    # Account
    # --------------------------------------------------

    print("[SIP] Creating Vivavox account...")

    ac = pj.AccountConfig()

    ac.idUri = f"sip:{USERNAME}@{SERVER}"

    ac.regConfig.registrarUri = (
        f"sip:{SERVER}:{PORT}"
    )

    cred = pj.AuthCredInfo(
        "digest",
        "*",
        USERNAME,
        0,
        PASSWORD
    )

    ac.sipConfig.authCreds.append(cred)

    print("[SIP] SIP authentication configured.")

    # IMPORTANT:
    # Use plain pj.Account(), exactly like the successful
    # 30-second test.
    acc = pj.Account()
    acc.create(ac)

    print("[SIP] Account created.")

    print()
    print("[SIP] =========================================")
    print("[SIP] SIP SERVICE RUNNING")
    print("[SIP] =========================================")
    print("[SIP] Waiting for Vivavox registration...")
    print("[SIP] Call 0873210201 to test.")
    print("[SIP] Press CTRL+C to stop.")
    print()

    # --------------------------------------------------
    # Keep Python alive forever.
    # --------------------------------------------------

    while True:
        time.sleep(1)

        try:
            info = acc.getInfo()

            print(
                f"\r[SIP] Registration: "
                f"{info.regStatus} {info.regStatusText}",
                end="",
                flush=True
            )

        except Exception as e:
            print()
            print(f"[SIP] Status error: {e}")

except KeyboardInterrupt:
    print()
    print("[SIP] Stopping...")

except Exception as e:
    print()
    print(f"[SIP] Python exception: {type(e).__name__}: {e}")

finally:
    print("[SIP] Cleaning up...")

    try:
        if acc is not None:
            acc.shutdown()
    except Exception as e:
        print(f"[SIP] Account cleanup: {e}")

    try:
        if ep is not None:
            ep.libDestroy()
    except Exception as e:
        print(f"[SIP] Endpoint cleanup: {e}")

    print("[SIP] Stopped.")