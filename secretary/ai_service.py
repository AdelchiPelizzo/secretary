from dotenv import load_dotenv
from openai import OpenAI
import soundfile as sf

load_dotenv()

client = OpenAI()

def speech_to_text(audio):

    filename = "caller.wav"
    sf.write(
        filename,
        audio,
        44100
    )

    print("Sending audio to OpenAI for transcription...")

    with open(filename, "rb") as audio_file:

        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file
        )

    return transcription.text

def ask_ai(call, message):

    call.messages.append({
        "role": "user",
        "content": message
    })

    appointment = call.appointment

    messages = [{
        "role": "system",
        "content": (
            "You are a professional and friendly telephone secretary. "
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
            "RESPONSE: No problem. I won't add the appointment."
        )
    }]

    messages.extend(call.messages)

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=messages
    )

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

    if action == "CREATE_APPOINTMENT":
        call.appointment_status = "COLLECTING"

    elif action == "CONFIRM_APPOINTMENT":
        call.appointment_status = "CONFIRMING"

    elif action == "APPOINTMENT_CONFIRMED":
        call.appointment_status = "CONFIRMED"

    elif action == "APPOINTMENT_CANCELLED":
        call.appointment_status = "CANCELLED"

    call.messages.append({
        "role": "assistant",
        "content": answer
    })

    print()
    print("Action:", action)
    print("Appointment status:", call.appointment_status)
    print("Appointment:", appointment)
    print("Caller:", message)
    print("AI:", answer)

    return action, answer

def text_to_speech(text):
    filename = "ai_response.wav"

    print()
    print("Generating AI speech...")

    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input=text
    )
    response.write_to_file(filename)

    print("AI speech generated.")

    return filename