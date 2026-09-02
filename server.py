import os
import uuid
import threading
import time

import numpy as np
import soundfile as sf

from openai import OpenAI
from dotenv import load_dotenv

from secretary.call import Call
from secretary.ai_service import speech_to_text, ask_ai
from secretary.sip import SipServer

INPUT_DEVICE = 1
OUTPUT_DEVICE = 5

SAMPLE_RATE = 44100
CHANNELS = 1

load_dotenv()

client = OpenAI()

class CallServer:

    def __init__(self):

        self.calls = {}
        self.active_call = None

        self.sip_server = "sip.vivavox.it"
        self.username = os.getenv("VIVAVOX_USERNAME")
        self.password = os.getenv("VIVAVOX_PASSWORD")

    def receive_call(
        self,
        caller_number=None,
        called_number=None
    ):

        call_id = str(uuid.uuid4())

        call = Call(
            call_id,
            caller_number,
            called_number
        )

        self.calls[call_id] = call

        print()
        print("================================")
        print("INCOMING CALL")
        print("Call ID:", call_id)
        print("================================")

        return call

    def create_appointment(self, call):

        appointment = call.appointment

        print()
        print("=== APPOINTMENT READY ===")
        print("Title:", appointment["title"])
        print("Date:", appointment["date"])
        print("Time:", appointment["time"])
        print("Duration:", appointment["duration_minutes"])
        print("=========================")

    def resample(self, audio, source_rate, target_rate):

        if source_rate == target_rate:
            return audio

        duration = len(audio) / source_rate

        new_length = int(
            duration * target_rate
        )

        old_indices = np.arange(len(audio))

        new_indices = np.linspace(
            0,
            len(audio) - 1,
            new_length
        )

        return np.interp(
            new_indices,
            old_indices,
            audio
        ).astype(np.float32)

    def wait_for_speech(self, audio_port):

        print()
        print("[AUDIO] Waiting for caller speech...")

        chunks = []
        speech_started = False
        silence_frames = 0

        # 8 kHz / 20 ms
        max_silence_frames = 35

        while True:

            data = audio_port.input_queue.get()

            audio = np.frombuffer(
                data,
                dtype=np.int16
            )

            if len(audio) == 0:
                continue

            rms = np.sqrt(
                np.mean(
                    audio.astype(np.float32) ** 2
                )
            )

            # Basic speech detector.
            is_speech = rms > 500

            if is_speech:

                speech_started = True
                silence_frames = 0
                chunks.append(data)

            elif speech_started:

                chunks.append(data)

                silence_frames += 1

                if silence_frames >= max_silence_frames:

                    break

        if not chunks:
            return None

        raw_audio = b"".join(chunks)

        audio = np.frombuffer(
            raw_audio,
            dtype=np.int16
        ).astype(np.float32) / 32768.0

        # Your existing STT function expects 44.1 kHz.
        audio = self.resample(
            audio,
            8000,
            44100
        )

        return audio

    def text_to_speech_to_sip(
        self,
        text,
        audio_port
    ):

        filename = "ai_response.wav"

        print()
        print("[TTS] Generating AI speech...")

        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="coral",
            input=text
        )

        response.write_to_file(filename)

        data, samplerate = sf.read(
            filename,
            dtype="float32"
        )

        # Make mono.
        if data.ndim > 1:
            data = np.mean(
                data,
                axis=1
            )

        # Convert OpenAI TTS sample rate to SIP rate.
        data = self.resample(
            data,
            samplerate,
            8000
        )

        # Convert float32 [-1,1] to int16.
        data = np.clip(
            data,
            -1.0,
            1.0
        )

        pcm = (
            data * 32767
        ).astype(np.int16)

        raw = pcm.tobytes()

        print("[TTS] Sending speech to caller...")

        # Feed 20 ms chunks into PJSIP.
        for position in range(
            0,
            len(raw),
            320 * 2
        ):

            chunk = raw[
                position:
                position + 320 * 2
            ]

            audio_port.output_queue.put(
                chunk
            )

        # Wait until all generated audio has been consumed.
        while not audio_port.output_queue.empty():
            time.sleep(0.02)

        print("[TTS] AI finished speaking.")

    def process_call(self, sip_call):

        app_call = sip_call.app_call
        audio_port = sip_call.audio_port

        print()
        print("[AI] Call processing started.")

        try:

            while True:

                # Wait for caller to speak.
                audio = self.wait_for_speech(
                    audio_port
                )

                if audio is None:
                    continue

                print(
                    "[STT] Transcribing caller..."
                )

                message = speech_to_text(
                    audio
                )

                message = message.strip()

                if not message:
                    print(
                        "[STT] No speech detected."
                    )
                    continue

                print()
                print("Caller:", message)

                if (
                    "hang up" in message.lower()
                    or
                    "hangup" in message.lower()
                ):

                    print(
                        "[SIP] Caller requested hangup."
                    )

                    break

                action, answer = ask_ai(
                    app_call,
                    message
                )

                if action == "APPOINTMENT_CONFIRMED":
                    self.create_appointment(
                        app_call
                    )

                self.text_to_speech_to_sip(
                    answer,
                    audio_port
                )

        except Exception as e:

            print()
            print("[AI] Call processing error:")
            print(type(e).__name__, e)

        finally:

            print()
            print("[AI] Call processing finished.")


load_dotenv()

client = OpenAI()

server = CallServer()
sip = SipServer(server)

try:
    sip.start()

    print()
    print("================================")
    print("AI SECRETARY SERVER")
    print("================================")
    print()
    print("SIP service running.")
    print("Call your VivaVox number to test.")
    print("Press CTRL+C to stop.")
    print()

    while True:
        sip.ep.libHandleEvents(50)
        time.sleep(0.01)

except KeyboardInterrupt:
    print()
    print("Stopping...")

except Exception as e:
    print()
    print("SERVER ERROR:")
    print(type(e).__name__, e)

finally:
    sip.stop()

