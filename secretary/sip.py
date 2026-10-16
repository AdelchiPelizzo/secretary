import os
import threading
import time

from secretary import pjsua2 as pj
from dotenv import load_dotenv
from datetime import datetime


SERVER = "sip.vivavox.it"
PORT = 5060


class SecretaryCall(pj.Call):

    def __init__(self, account, call_id, app_call=None):
        super().__init__(account, call_id)

        self.account = account
        self.app_call = app_call
        self.audio_port = None

        if app_call is not None:
            self.audio_port = app_call.audio_port

    def onCallState(self, prm):

        ci = self.getInfo()

        print("[SIP] Remote URI:", ci.remoteUri)
        print("[SIP] Local URI:", ci.localUri)

        print("[SIP] onCallMediaState:", ci.media)

        if ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            ti = self.getMedTransportInfo(0)
            print("[SIP] local RTP:", ti.localRtpName)
            print("[SIP] local RTCP:", ti.localRtcpName)
            print("[SIP] source RTP:", ti.srcRtpName)
            print("[SIP] source RTCP:", ti.srcRtcpName)

            si = self.getStreamInfo(0)

            print("[SIP] codec:", si.codecName)
            print("[SIP] clock rate:", si.codecClockRate)
            print("[SIP] direction:", si.dir)
            print("[SIP] remote RTP:", si.remoteRtpAddress)
            print("[SIP] remote RTCP:", si.remoteRtcpAddress)
            print("[SIP] RX payload:", si.rxPt)
            print("[SIP] TX payload:", si.txPt)

            if ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
                am = self.getAudioMedia(0)
                print("[SIP] Audio port ID:", am.getPortId())
                pi = am.getPortInfo()
                print("[SIP] ConfPortInfo fields:", dir(pi))

        print()
        print("[SIP] Call state:", ci.stateText)

        if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:

            if hasattr(self, "audio_port") and self.audio_port is not None:
                self.audio_port.stop()

            print("[SIP] Call disconnected.")

    def onCallMediaState(self, prm):
        ci = self.getInfo()

        for mi in ci.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO:
                if mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    audio_media = self.getAudioMedia(mi.index)

                    print("[SIP] Connecting call audio to sound device...")

                    print("[DEBUG] account.server:", self.account.server)
                    print("[DEBUG] account.server type:", type(self.account.server))

                    print("[SIP] BEFORE call -> playback")

                    print("[DEBUG] sip_server:", self.account.server.sip_server)
                    print("[DEBUG] sip_server type:", type(self.account.server.sip_server))

                    audio_media.startTransmit(
                        self.account.server.sip.ep.audDevManager().getPlaybackDevMedia()
                    )

                    print("[SIP] AFTER call -> playback")

                    # Leave capture connection commented out for this test
                    self.account.server.sip.ep.audDevManager().getCaptureDevMedia().startTransmit(audio_media)

                    print("[SIP] Audio media port:", audio_media.getPortId())
                    print("[SIP] Audio media info:", audio_media.getPortInfo())


class SecretaryAccount(pj.Account):

    def __init__(self, server):

        super().__init__()

        self.server = server
        self.active_calls = {}

    def onIncomingCall(self, prm):

        print()
        print("================================")
        print("[SIP] INCOMING CALL")
        print("================================")

        print("[SIP] Call ID:", prm.callId)

        call = SecretaryCall(
            self,
            prm.callId
        )

        call_info = call.getInfo()

        print("[SIP] Remote URI:", call_info.remoteUri)
        print("[SIP] Local URI:", call_info.localUri)

        app_call = self.server.receive_call(
            caller_number=self.server.extract_caller_number(
                call_info.remoteUri
            ),
            called_number=call_info.localUri
        )

        # Reject calls if business access cannot be verified
        config = getattr(app_call, "secretary_config", None)

        if not config:
            print("[SIP] REJECTED: Secretary configuration unavailable")

            reject = pj.CallOpParam()
            reject.statusCode = 403
            call.answer(reject)
            return

        payment_status = config.get("paymentStatus")
        now = datetime.now()

        def is_expired(value):
            if not value:
                return True

            try:
                expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))

                current_time = (datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now())

                return expiry <= current_time

            except (ValueError, TypeError, AttributeError):
                return True

        expired = (payment_status == "expired" or (
                payment_status == "trial" and is_expired(config.get("trialEndsAt"))) or (
                           payment_status == "valid" and config.get("paymentValidUntil") and is_expired(
                       config.get("paymentValidUntil"))))

        if expired:
            print("[SIP] REJECTED: Business trial or payment expired")

            reject = pj.CallOpParam()
            reject.statusCode = 403
            call.answer(reject)
            return

        call.app_call = app_call
        call.audio_port = app_call.audio_port

        self.active_calls[
            prm.callId
        ] = call

        answer = pj.CallOpParam()

        answer.statusCode = 200

        call.answer(answer)

        call.audio_port.start()

        threading.Thread(
            target=self.server.process_call,
            args=(call,),
            daemon=True
        ).start()

        print("[SIP] CALL ANSWERED")



class SipServer:

    def __init__(self, server):

        self.server = server
        self.registrations = []

        self.ep = None
        self.acc = None
        self.accounts = []

    def start(self):

        print()
        print("=========================================")
        print("[SIP] Starting PJSIP")
        print("=========================================")

        self.ep = pj.Endpoint()

        self.ep.libCreate()

        ep_cfg = pj.EpConfig()
        ep_cfg.uaConfig.threadCnt = 0

        # NAT / STUN
        ep_cfg.uaConfig.natTypeInSdp = 1
        ep_cfg.uaConfig.stunServer.append("stun.l.google.com:19302")
        ep_cfg.uaConfig.stunIgnoreFailure = False

        self.ep.libInit(ep_cfg)

        transport_cfg = pj.TransportConfig()
        transport_cfg.port = PORT

        self.ep.transportCreate(
            pj.PJSIP_TRANSPORT_UDP,
            transport_cfg
        )

        self.ep.libStart()

        for i in range(self.ep.audDevManager().getDevCount()):
            info = self.ep.audDevManager().getDevInfo(i)
            print(
                "[PJSIP DEVICE]",
                i,
                info.name,
                "in=",
                info.inputCount,
                "out=",
                info.outputCount
            )

        self.ep.audDevManager().setCaptureDev(3)
        self.ep.audDevManager().setPlaybackDev(6)

        print("[SIP] Audio devices configured:")
        print("[SIP] Capture: CABLE Output")
        print("[SIP] Playback: CABLE Input")
        print("[SIP] PJSIP started.")

        for registration in self.registrations:

            sip_data = registration.get("sip", {})

            username = sip_data.get("username")
            password = sip_data.get("password")
            host = sip_data.get("host") or SERVER
            port = int(sip_data.get("port") or PORT)
            transport = (sip_data.get("transport") or "UDP").upper()

            if not sip_data.get("active"):
                continue

            if not username or not password:
                print(
                    "[SIP] Skipping account with missing credentials:",
                    registration.get("number")
                )
                continue

            if transport != "UDP":
                print(
                    "[SIP] Skipping unsupported transport:",
                    transport
                )
                continue

            account_cfg = pj.AccountConfig()
            account_cfg.idUri = f"sip:{username}@{host}"
            account_cfg.regConfig.registrarUri = f"sip:{host}:{port}"

            credentials = pj.AuthCredInfo(
                "digest",
                "*",
                username,
                0,
                password
            )
            account_cfg.sipConfig.authCreds.append(credentials)

            account = SecretaryAccount(self.server)
            account.create(account_cfg)
            self.accounts.append(account)

            print(
                "[SIP] Account created for number:",
                registration.get("number")
            )

        if not self.accounts:
            raise RuntimeError(
                "No valid active SIP accounts were created."
            )

        # Preserve compatibility with existing code expecting self.acc.
        self.acc = self.accounts[0]

        print("[SIP] Waiting for registration...")

    def run(self):

        try:
            while True:
                self.ep.libHandleEvents(50)
                time.sleep(0.01)

        except KeyboardInterrupt:
            print()
            print("[SIP] Stopping...")


    def stop(self):

        print(
            "[SIP] Shutting down."
        )

        if self.acc:

            self.acc.shutdown()

            self.acc = None

        if self.ep:

            self.ep.libDestroy()

            self.ep = None

