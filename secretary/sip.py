import os
import time

from secretary import pjsua2 as pj
from dotenv import load_dotenv


SERVER = "sip.vivavox.it"
PORT = 5060


class SecretaryCall(pj.Call):

    def __init__(self, account, call_id):
        super().__init__(account, call_id)

    def onCallState(self, prm):
        ci = self.getInfo()

        print()
        print("[SIP] Call state:", ci.stateText)

        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            print("[SIP] Call disconnected.")


class SecretaryAccount(pj.Account):

    def __init__(self):
        super().__init__()
        self.active_calls = {}

    def onIncomingCall(self, prm):

        print()
        print("================================")
        print("[SIP] INCOMING CALL")
        print("================================")
        print("[SIP] Call ID:", prm.callId)

        call = SecretaryCall(self, prm.callId)

        self.active_calls[prm.callId] = call

        answer = pj.CallOpParam()
        answer.statusCode = 200

        call.answer(answer)

        print("[SIP] CALL ANSWERED")


class SipServer:

    def __init__(self, server):

        self.server = server

        load_dotenv()

        self.username = os.getenv("VIVAVOX_USERNAME")
        self.password = os.getenv("VIVAVOX_PASSWORD")
        self.number = os.getenv("VIVAVOX_NUMBER")

        self.ep = None
        self.acc = None

    def start(self):

        print()
        print("=========================================")
        print("[SIP] Starting PJSIP")
        print("=========================================")

        self.ep = pj.Endpoint()

        self.ep.libCreate()

        ep_cfg = pj.EpConfig()

        # Important:
        # Let Python explicitly drive PJSIP events.
        ep_cfg.uaConfig.threadCnt = 0

        self.ep.libInit(ep_cfg)

        transport_cfg = pj.TransportConfig()
        transport_cfg.port = PORT

        self.ep.transportCreate(
            pj.PJSIP_TRANSPORT_UDP,
            transport_cfg
        )

        self.ep.libStart()

        print("[SIP] PJSIP started.")

        account_cfg = pj.AccountConfig()

        account_cfg.idUri = (
            f"sip:{self.username}@{SERVER}"
        )

        account_cfg.regConfig.registrarUri = (
            f"sip:{SERVER}:{PORT}"
        )

        credentials = pj.AuthCredInfo(
            "digest",
            "*",
            self.username,
            0,
            self.password
        )

        account_cfg.sipConfig.authCreds.append(
            credentials
        )

        self.acc = SecretaryAccount()

        self.acc.create(account_cfg)

        print("[SIP] Account created.")
        print("[SIP] Waiting for registration...")

    def run(self):

        try:

            while True:

                # Explicitly process PJSIP events.
                self.ep.libHandleEvents(50)

                time.sleep(0.01)

        except KeyboardInterrupt:

            print()
            print("[SIP] Stopping...")

    def stop(self):

        print("[SIP] Shutting down.")

        if self.acc:
            self.acc.shutdown()
            self.acc = None

        if self.ep:
            self.ep.libDestroy()
            self.ep = None