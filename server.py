import uuid

import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

INPUT_DEVICE = 31
OUTPUT_DEVICE = 14

SAMPLE_RATE = 44100
CHANNELS = 1
RECORD_SECONDS = 5

load_dotenv()

client = OpenAI()

class Call:

    def __init__(self, call_id):
        self.call_id = call_id
        self.messages = []


class CallServer:

    def __init__(self):
        self.calls = {}

    def receive_call(self):

        call_id = str(uuid.uuid4())

        call = Call(call_id)

        self.calls[call_id] = call

        print()
        print("================================")
        print("INCOMING CALL")
        print("Call ID:", call_id)
        print("================================")

        return call

    def receive_audio(self, call):

        print()
        print("Caller is speaking...")
        print(f"Recording {RECORD_SECONDS} seconds...")

        recording = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            device=INPUT_DEVICE
        )

        sd.wait()

        print("Caller finished speaking.")

        return recording

    def speech_to_text(self, audio):
        filename = "caller.wav"

        sf.write(
            filename,
            audio,
            SAMPLE_RATE
        )

        print("Sending audio to OpenAI for transcription...")

        with open(filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=audio_file)

        return transcription.text

    def ask_ai(self, call, message):

        call.messages.append({
            "role": "caller",
            "message": message
        })

        print()
        print("Caller:", message)

        # Temporary mock AI

        answer = "Hello! Certainly. What day would you like the appointment?"

        call.messages.append({
            "role": "assistant",
            "message": answer
        })

        print("AI:", answer)

        return answer

    def text_to_speech(self, text):

        # Temporary test.
        # We don't have TTS yet.

        print()
        print("AI would now speak:")
        print(text)

    def handle_call(self):

        call = self.receive_call()

        audio = self.receive_audio(call)

        message = self.speech_to_text(audio)

        answer = self.ask_ai(call, message)

        self.text_to_speech(answer)

        print()
        print("Call finished.")


server = CallServer()

print("================================")
print("AI SECRETARY SERVER")
print("================================")
print()
print("Type 'call' to simulate an incoming call.")
print("Type 'quit' to stop.")

while True:

    command = input("\n> ")

    if command.lower() == "quit":
        break

    if command.lower() == "call":

        server.handle_call()