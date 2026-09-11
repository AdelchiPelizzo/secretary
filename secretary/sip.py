import os
import threading
import time

from secretary import pjsua2 as pj
from dotenv import load_dotenv


SERVER = "sip.vivavox.it"
PORT = 5060


class SecretaryCall(pj.Call):

    def __init__(self, account, call_id, app_call):
        super().__init__(account, call_id)

        self.account = account
        self.app_call = app_call
        self.audio_port = app_call.audio_port

    def onCallState(self, prm):

        ci = self.getInfo()

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

            if hasattr(self, "audio_port"):
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

        print(
            "[SIP] Call ID:",
            prm.callId
        )

        app_call = self.server.receive_call()

        call = SecretaryCall(self, prm.callId, app_call)

        self.active_calls[
            prm.callId
        ] = call

        answer = pj.CallOpParam()

        answer.statusCode = 200

        call.answer(answer)

        call.audio_port.start()

        threading.Thread(target=self.server.process_call, args=(call,), daemon=True).start()

        print("[SIP] CALL ANSWERED")


class SipServer:

    def __init__(self, server):

        self.server = server

        load_dotenv()

        self.username = os.getenv(
            "VIVAVOX_USERNAME"
        )

        self.password = os.getenv(
            "VIVAVOX_PASSWORD"
        )

        self.number = os.getenv(
            "VIVAVOX_NUMBER"
        )

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
            print("[PJSIP DEVICE]", i, info.name, "in=", info.inputCount, "out=", info.outputCount)

        self.ep.audDevManager().setCaptureDev(4)
        self.ep.audDevManager().setPlaybackDev(8)

        print("[SIP] Audio devices configured:")
        print("[SIP] Capture: CABLE Output")
        print("[SIP] Playback: CABLE Input")

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

        self.acc = SecretaryAccount(self.server)

        self.acc.create(
            account_cfg
        )

        print("[SIP] Account created.")

        print(
            "[SIP] Waiting for registration..."
        )

    def run(self):

        try:

            while True:

                self.ep.libHandleEvents(
                    50
                )

                time.sleep(
                    0.01
                )

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
