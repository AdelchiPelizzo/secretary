import os
import time
from pathlib import Path

import pjsua2 as pj
from dotenv import load_dotenv


# ==========================================================
# Paths / environment
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

print(f"[TEST] Loading .env from: {ENV_FILE}")
load_dotenv(ENV_FILE)

NUMBER = os.getenv("VIVAVOX_NUMBER")
USERNAME = os.getenv("VIVAVOX_USERNAME")
PASSWORD = os.getenv("VIVAVOX_PASSWORD")

SERVER = "sip.vivavox.it"
PORT = 5060


# ==========================================================
# Incoming Call
# ==========================================================

class TestCall(pj.Call):

    def onCallState(self, prm):
        try:
            info = self.getInfo()

            print()
            print("=========================================")
            print("[TEST] CALL STATE")
            print("=========================================")
            print(f"[TEST] State : {info.stateText}")
            print(f"[TEST] Code  : {info.lastStatusCode}")
            print(f"[TEST] Reason: {info.lastReason}")
            print("=========================================")
            print()

        except Exception as e:
            print(
                f"[TEST] Call state error: "
                f"{type(e).__name__}: {e}"
            )

    def onCallMediaState(self, prm):
        try:
            info = self.getInfo()

            print()
            print("=========================================")
            print("[TEST] CALL MEDIA STATE")
            print("=========================================")

            for mi in info.media:

                if mi.type == pj.PJMEDIA_TYPE_AUDIO:

                    print(f"[TEST] Audio media status: {mi.status}")

                    if mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:

                        print("[TEST] Audio media is ACTIVE")

                        audio_media = self.getAudioMedia(-1)

                        # Connect call audio to the PJSIP sound device.
                        ep.audDevManager().getPlaybackDevMedia().startTransmit(
                            audio_media
                        )

                        ep.audDevManager().getCaptureDevMedia().startTransmit(
                            audio_media
                        )

                        print("[TEST] Audio connected")
                        print("[TEST] Speak into the microphone")
                        print("[TEST] Audio should come from the selected speakers/headset")

            print("=========================================")
            print()

        except Exception as e:
            print()
            print(
                f"[TEST] Media error: "
                f"{type(e).__name__}: {e}"
            )
            print()


# ==========================================================
# Account
# ==========================================================

class TestAccount(pj.Account):

    def onRegState(self, prm):
        print()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! PYTHON onRegState FIRED !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"code   = {prm.code}")
        print(f"reason = {prm.reason}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print()

    def onIncomingCall(self, prm):

        print()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! PYTHON onIncomingCall FIRED !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"[TEST] Incoming call ID: {prm.callId}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print()

        try:

            global current_call

            current_call = TestCall(
                self,
                prm.callId
            )

            info = current_call.getInfo()

            print("[TEST] Incoming call received")
            print(f"[TEST] Remote URI: {info.remoteUri}")
            print(f"[TEST] State     : {info.stateText}")

            # --------------------------------------------------
            # ANSWER
            # --------------------------------------------------

            print()
            print("[TEST] Answering call with 200 OK...")

            answer_prm = pj.CallOpParam()

            answer_prm.statusCode = 200

            current_call.answer(answer_prm)

            print("[TEST] Answer command sent")
            print("[TEST] Waiting for confirmed call/media...")
            print()

        except Exception as e:

            print()
            print(
                f"[TEST] Incoming call error: "
                f"{type(e).__name__}: {e}"
            )
            print()


# ==========================================================
# Main
# ==========================================================

ep = None
account = None
current_call = None


try:

    print()
    print("=========================================")
    print("[TEST] INCOMING CALL + AUDIO TEST")
    print("=========================================")
    print()

    # ------------------------------------------------------
    # Endpoint
    # ------------------------------------------------------

    print("[TEST] Creating endpoint...")

    ep = pj.Endpoint()

    ep.libCreate()

    # IMPORTANT:
    # Python callback-safe configuration.
    ep_cfg = pj.EpConfig()
    ep_cfg.uaConfig.threadCnt = 0

    ep.libInit(ep_cfg)

    # ------------------------------------------------------
    # UDP transport
    # ------------------------------------------------------

    print("[TEST] Creating UDP transport...")

    tc = pj.TransportConfig()
    tc.port = PORT

    ep.transportCreate(
        pj.PJSIP_TRANSPORT_UDP,
        tc
    )

    # ------------------------------------------------------
    # Start PJSIP
    # ------------------------------------------------------

    ep.libStart()

    print("[TEST] PJSIP started")

    # ------------------------------------------------------
    # Audio devices
    # ------------------------------------------------------

    print()
    print("=========================================")
    print("[TEST] AUDIO DEVICES")
    print("=========================================")

    aud_mgr = ep.audDevManager()

    print(
        f"[TEST] Capture device : "
        f"{aud_mgr.getCaptureDev()}"
    )

    print(
        f"[TEST] Playback device: "
        f"{aud_mgr.getPlaybackDev()}"
    )

    print("=========================================")
    print()

    # ------------------------------------------------------
    # Account configuration
    # ------------------------------------------------------

    print("[TEST] Creating Vivavox account...")

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

    # ------------------------------------------------------
    # Account
    # ------------------------------------------------------

    print("[TEST] Creating TestAccount...")

    account = TestAccount()

    print("[TEST] TestAccount Python object created")
    print(f"[TEST] thisown = {account.thisown}")
    print(f"[TEST] type    = {type(account)}")

    account.create(ac)

    print("[TEST] Account created")

    # ------------------------------------------------------
    # Keep process alive
    # ------------------------------------------------------

    print()
    print("=========================================")
    print("[TEST] INCOMING CALL + AUDIO TEST RUNNING")
    print("=========================================")
    print("[TEST] Waiting for registration...")
    print(f"[TEST] Call {NUMBER} from another phone.")
    print("[TEST] The call WILL be answered automatically.")
    print("[TEST] DO NOT PRESS CTRL+C during the test.")
    print("=========================================")
    print()

    while True:

        # IMPORTANT:
        # PJSIP events are processed explicitly by Python.
        ep.libHandleEvents(100)

        try:

            info = account.getInfo()

            print(
                f"\r[TEST] Registration: "
                f"{info.regStatus} {info.regStatusText}",
                end="",
                flush=True
            )

        except Exception as e:

            print()
            print(
                f"[TEST] Status error: "
                f"{type(e).__name__}: {e}"
            )


except KeyboardInterrupt:

    print()
    print("[TEST] Stopping...")


except Exception as e:

    print()
    print(
        f"[TEST] Python exception: "
        f"{type(e).__name__}: {e}"
    )


finally:

    print()
    print("[TEST] Cleaning up...")

    try:

        if current_call is not None:

            print("[TEST] Hanging up active call...")

            try:
                current_call.hangup(
                    pj.CallOpParam()
                )
            except Exception:
                pass

    except Exception as e:

        print(f"[TEST] Call cleanup: {e}")

    try:

        if account is not None:
            account.shutdown()

    except Exception as e:

        print(f"[TEST] Account shutdown: {e}")

    try:

        if ep is not None:
            ep.libDestroy()

    except Exception as e:

        print(f"[TEST] Endpoint destroy: {e}")

    print("[TEST] Finished.")