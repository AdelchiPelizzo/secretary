import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import uuid
import threading

from secretary.call import Call
from secretary.audio import receive_audio

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

        call.messages.append({"role": "user", "content": message})

        appointment = call.appointment

        messages = [{"role": "system", "content": ("You are a professional and friendly telephone secretary. "

                                                   "Respond in the same language as the caller. "
                                                   "Answer naturally and concisely. "
                                                   "Keep responses short because they will be spoken aloud.\n\n"

                                                   "You can help the caller create an appointment.\n\n"

                                                   "Current appointment status:\n"
                                                   f"{call.appointment_status}\n\n"

                                                   "Current appointment information:\n"
                                                   f"title = {appointment['title']}\n"
                                                   f"date = {appointment['date']}\n"
                                                   f"time = {appointment['time']}\n"
                                                   f"duration_minutes = {appointment['duration_minutes']}\n\n"

                                                   "If the caller wants an appointment, collect the required "
                                                   "information across multiple turns.\n\n"

                                                   "Required information:\n"
                                                   "- title\n"
                                                   "- date\n"
                                                   "- time\n\n"

                                                   "Do not ask for information that the caller has already provided.\n\n"

                                                   "When all required information has been collected, summarize "
                                                   "the appointment and ask the caller whether they want it added "
                                                   "to their calendar.\n\n"

                                                   "When asking for confirmation, use action CONFIRM_APPOINTMENT.\n\n"

                                                   "If the caller clearly confirms, use action APPOINTMENT_CONFIRMED.\n\n"

                                                   "If the caller clearly rejects or cancels the appointment, "
                                                   "use action APPOINTMENT_CANCELLED.\n\n"

                                                   "Return exactly this format:\n"
                                                   "ACTION: <action>\n"
                                                   "TITLE: <value or NONE>\n"
                                                   "DATE: <value or NONE>\n"
                                                   "TIME: <value or NONE>\n"
                                                   "DURATION: <value or NONE>\n"
                                                   "RESPONSE: <spoken response>\n\n"

                                                   "Possible actions:\n"
                                                   "NONE\n"
                                                   "CREATE_APPOINTMENT\n"
                                                   "CONFIRM_APPOINTMENT\n"
                                                   "APPOINTMENT_CONFIRMED\n"
                                                   "APPOINTMENT_CANCELLED\n\n"

                                                   "Use CREATE_APPOINTMENT while collecting appointment "
                                                   "information.\n\n"

                                                   "Use CONFIRM_APPOINTMENT when all required information is "
                                                   "available and you are asking the caller for confirmation.\n\n"

                                                   "Use APPOINTMENT_CONFIRMED when the caller says yes or "
                                                   "otherwise clearly confirms.\n\n"

                                                   "Use APPOINTMENT_CANCELLED when the caller says no or "
                                                   "otherwise clearly cancels.\n\n"

                                                   "Use NONE for normal conversation.\n\n"

                                                   "Example confirmation:\n"
                                                   "ACTION: CONFIRM_APPOINTMENT\n"
                                                   "TITLE: Dentist\n"
                                                   "DATE: 2026-08-26\n"
                                                   "TIME: 10:00\n"
                                                   "DURATION: NONE\n"
                                                   "RESPONSE: I have a dentist appointment tomorrow at 10 AM. "
                                                   "Shall I add it to your calendar?\n\n"

                                                   "Example confirmation response:\n"
                                                   "ACTION: APPOINTMENT_CONFIRMED\n"
                                                   "TITLE: Dentist\n"
                                                   "DATE: 2026-08-26\n"
                                                   "TIME: 10:00\n"
                                                   "DURATION: NONE\n"
                                                   "RESPONSE: Certainly. I'll add the dentist appointment "
                                                   "to your calendar.\n\n"

                                                   "Example cancellation:\n"
                                                   "ACTION: APPOINTMENT_CANCELLED\n"
                                                   "TITLE: NONE\n"
                                                   "DATE: NONE\n"
                                                   "TIME: NONE\n"
                                                   "DURATION: NONE\n"
                                                   "RESPONSE: No problem. I won't add the appointment.")}]

        messages.extend(call.messages)

        response = client.chat.completions.create(model="gpt-5-mini", messages=messages)

        raw_answer = response.choices[0].message.content.strip()

        print()
        print("AI raw response:")
        print(raw_answer)

        action = "NONE"
        answer = raw_answer

        for line in raw_answer.splitlines():

            if line.startswith("ACTION:"):
                action = line.replace("ACTION:", "", 1).strip()

            elif line.startswith("TITLE:"):
                value = line.replace("TITLE:", "", 1).strip()

                if value.upper() != "NONE":
                    appointment["title"] = value

            elif line.startswith("DATE:"):
                value = line.replace("DATE:", "", 1).strip()

                if value.upper() != "NONE":
                    appointment["date"] = value

            elif line.startswith("TIME:"):
                value = line.replace("TIME:", "", 1).strip()

                if value.upper() != "NONE":
                    appointment["time"] = value

            elif line.startswith("DURATION:"):
                value = line.replace("DURATION:", "", 1).strip()

                if value.upper() != "NONE":
                    try:
                        appointment["duration_minutes"] = int(value)
                    except ValueError:
                        pass

            elif line.startswith("RESPONSE:"):
                answer = line.replace("RESPONSE:", "", 1).strip()

        # Update appointment state
        if action == "CREATE_APPOINTMENT":
            call.appointment_status = "COLLECTING"

        elif action == "CONFIRM_APPOINTMENT":
            call.appointment_status = "CONFIRMING"

        elif action == "APPOINTMENT_CONFIRMED":
            call.appointment_status = "CONFIRMED"

        elif action == "APPOINTMENT_CANCELLED":
            call.appointment_status = "CANCELLED"

        call.messages.append({"role": "assistant", "content": answer})

        print()
        print("Action:", action)
        print("Appointment status:", call.appointment_status)
        print("Appointment:", appointment)
        print("Caller:", message)
        print("AI:", answer)

        return action, answer

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

                message = self.speech_to_text(audio)
                if not message.strip():
                    print("No speech detected by transcription.")
                    continue

                print()
                print("Caller:", message)

                if "hang up" in message.lower() or "hangup" in message.lower():
                    print()
                    print("Caller hung up.")
                    break

                action, answer = self.ask_ai(call, message)

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