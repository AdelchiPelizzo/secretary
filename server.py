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

        print("Listening...")

        block_duration = 0.1

        silence_threshold = 0.015
        silence_duration = 0.8

        warmup_duration = 0.5
        pre_buffer_duration = 0.4

        warmup_blocks = int(warmup_duration / block_duration)
        pre_buffer_blocks = int(pre_buffer_duration / block_duration)

        blocks_read = 0

        audio_blocks = []
        pre_buffer = []

        speech_started = False
        silence_time = 0.0

        def callback(indata, frames, time, status):

            nonlocal speech_started
            nonlocal silence_time
            nonlocal blocks_read
            nonlocal pre_buffer

            audio = indata.copy()

            level = np.sqrt(np.mean(audio ** 2))

            blocks_read += 1

            # Ignore microphone startup transient
            if blocks_read <= warmup_blocks:
                return

            # Keep a small amount of audio before speech detection
            if not speech_started:

                pre_buffer.append(audio)

                if len(pre_buffer) > pre_buffer_blocks:
                    pre_buffer.pop(0)

                if level > silence_threshold:
                    speech_started = True

                    # Include audio immediately before detection
                    audio_blocks.extend(pre_buffer)

                    print("Speech detected...")

            else:

                audio_blocks.append(audio)

                if level < silence_threshold:
                    silence_time += block_duration
                else:
                    silence_time = 0.0

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", device=INPUT_DEVICE,
                blocksize=int(SAMPLE_RATE * block_duration), callback=callback):

            while not speech_started:
                sd.sleep(100)

            while silence_time < silence_duration:
                sd.sleep(100)

        print("Speech finished.")

        return np.concatenate(audio_blocks)

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
            "role": "user",
            "content": message
        })

        messages = [{"role": "system", "content": ("You are a professional and friendly telephone secretary. "
                                                   "Answer the caller naturally and concisely. "
                                                   "Keep responses short because they will be spoken aloud.")}]

        messages.extend(call.messages)

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages
        )

        answer = response.choices[0].message.content

        call.messages.append({
            "role": "assistant",
            "content": answer
        })

        print()
        print("Caller:", message)
        print("AI:", answer)

        return answer

    def text_to_speech(self, text):
        filename = "ai_response.wav"

        print()
        print("Generating AI speech...")

        response = client.audio.speech.create(model="gpt-4o-mini-tts", voice="coral", input=text)

        response.write_to_file(filename)

        print("Playing AI response...")

        data, samplerate = sf.read(filename, dtype="float32")

        sd.play(data, samplerate=samplerate, device=OUTPUT_DEVICE)

        sd.wait()

        print("AI finished speaking.")

    def handle_call(self):

        call = self.receive_call()

        while True:

            print()
            print("Caller is speaking...")
            print("Say 'hangup' when you want to end the simulated call.")

            audio = self.receive_audio(call)

            message = self.speech_to_text(audio)

            print()
            print("Caller:", message)

            # Temporary hangup detection
            if "hang up" in message.lower() or "hangup" in message.lower():
                print()
                print("Caller hung up.")
                break

            answer = self.ask_ai(call, message)

            self.text_to_speech(answer)

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

        server.handle_call()