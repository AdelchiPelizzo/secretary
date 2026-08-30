import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import uuid
import threading

from secretary.call import Call
from secretary.audio import receive_audio
from secretary.ai_service import speech_to_text, ask_ai

INPUT_DEVICE = 1
OUTPUT_DEVICE = 5

SAMPLE_RATE = 44100
CHANNELS = 1

load_dotenv()

print(sd.query_devices())

client = OpenAI()

class CallServer:

    def __init__(self):
        self.calls = {}

    def receive_call(self, caller_number=None, called_number=None):

        call_id = str(uuid.uuid4())

        call = Call(call_id, caller_number, called_number)

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

    def text_to_speech(self, text):
        filename = "ai_response.wav"

        print()
        print("Generating AI speech...")

        response = client.audio.speech.create(model="gpt-4o-mini-tts", voice="coral", input=text)

        response.write_to_file(filename)

        print("Playing AI response...")

        data, samplerate = sf.read(filename, dtype="float32")

        print("TTS sample rate:", samplerate)

        output_info = sd.query_devices(OUTPUT_DEVICE)
        output_samplerate = int(output_info["default_samplerate"])

        print("Output device:", OUTPUT_DEVICE)
        print("Output device sample rate:", output_samplerate)

        if samplerate != output_samplerate:
            print(f"Resampling audio: "
                  f"{samplerate} Hz -> {output_samplerate} Hz")

            duration = len(data) / samplerate
            new_length = int(duration * output_samplerate)

            old_indices = np.arange(len(data))
            new_indices = np.linspace(0, len(data) - 1, new_length)

            data = np.interp(new_indices, old_indices, data).astype(np.float32)

            samplerate = output_samplerate

        sd.play(data, samplerate=samplerate, device=OUTPUT_DEVICE)

        sd.wait()

        # Give the microphone a moment to settle after AI playback
        sd.sleep(400)

        print("AI finished speaking.")

    def handle_call(self):

        call = None

        try:
            call = self.receive_call()

            while True:

                print()
                print("Caller is speaking...")
                print("Say 'hangup' when you want to end the simulated call.")

                audio = receive_audio()

                message = speech_to_text(audio)
                if not message.strip():
                    print("No speech detected by transcription.")
                    continue

                print()
                print("Caller:", message)

                if "hang up" in message.lower() or "hangup" in message.lower():
                    print()
                    print("Caller hung up.")
                    break

                action, answer = ask_ai(call, message)

                if action == "APPOINTMENT_CONFIRMED":
                    self.create_appointment(call)

                self.text_to_speech(answer)


        except Exception as e:

            print()
            print("Call error:", e)

        finally:

            if call is not None:
                print()
                print("Call finished.")
                print("Call ID:", call.call_id)


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
        thread = threading.Thread(
            target=server.handle_call
        )

        thread.start()