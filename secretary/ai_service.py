from dotenv import load_dotenv
from openai import OpenAI
import soundfile as sf
import time

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

    spoken_date = appointment["date"]

    # try:
    #     date_obj = datetime.strptime(
    #         appointment["date"],
    #         "%Y-%m-%d"
    #     )
    #
    #     spoken_date = date_obj.strftime("%A %d %B")
    #
    # except (ValueError, TypeError):
    #     pass

    if call.appointment_status != "CHOOSING_ALTERNATIVE":
        appointment["alternatives"] = []

    print("[AI CONFIG] "
          f"name={call.secretary_config.get('secretaryName', 'Secretary')} | "
          f"type={call.secretary_config.get('secretaryType', 'general')} | "
          f"personality={call.secretary_config.get('personality', 'professional')} | "
          f"default_language={call.secretary_config.get('language', 'en')} | "
          f"supported_languages={call.secretary_config.get('supportedLanguages', [])} | "
          f"instructions={call.secretary_config.get('instructions', '')}")

    messages = [{
        "role": "system",
        "content": (
            f"Business configuration:\n"
            f"Secretary name: {call.secretary_config.get('secretaryName', 'Secretary')}\n"
            f"Secretary type: {call.secretary_config.get('secretaryType', 'general')}\n"
            f"Personality: {call.secretary_config.get('personality', 'professional')}\n"
            f"Default language: {call.secretary_config.get('language', 'en')}\n"
            f"Supported additional languages: {', '.join(call.secretary_config.get('supportedLanguages', []))}\n"
            f"Business instructions: {call.secretary_config.get('instructions', '')}\n\n"
            
            "Use the business configuration above when generating your responses. "
            "Adapt your tone and behavior to the configured personality and secretary type. "
            "Use the additional information and instructions provided by the business "
            "whenever they are relevant to the caller's request. "
            "Additional information may include temporary notices, policies, "
            "operational information, or specific instructions for handling callers. "
            "Do not apply unrelated information to the conversation. "
            "The business configuration takes priority over generic secretary behavior, "
            "provided that it does not conflict with the caller's request or system rules.\n\n"
            
            "You are a professional and friendly telephone secretary. "
            "Respond in the language currently spoken by the caller. "
            "Detect the language of the caller's latest message. "
            "If the caller speaks a different language from the current conversation language, "
            "immediately switch to that language and continue the conversation in it. "
            "Update the conversation language internally when the caller changes language. "
            "Speak naturally, like a real human telephone secretary. "
            "Use conversational language rather than technical, robotic, "
            "formal, or machine-generated phrasing. "
            "Answer naturally and concisely. "
            "Keep responses short because they will be spoken aloud.\n\n"

            "You can help the caller create an appointment.\n\n"

            "Current appointment status:\n"
            f"{call.appointment_status}\n\n"
            
            "Current conversation language:\n"
            f"{call.language}\n\n"
            
            "Language rule:\n"
            "The configured secretary language is the starting language only. "
            "The caller's actual spoken language has priority during the conversation. "
            "If the caller speaks a different language, identify the new language "
            "and use it for the response and subsequent conversation, "
            "but only switch to a language configured as supported by the business. "
            "If the caller uses a language that is not configured as supported, "
            "continue using the current conversation language.\n\n"
            
            "Appointment status rules:\n"
            "If the status is CHOOSING_ALTERNATIVE, the previously requested "
            "appointment time was unavailable and alternatives have been offered.\n"
            "The caller may identify an alternative using its date, time, position "
            "in the list, or a natural-language reference such as 'the first one' "
            "or an equivalent expression in their language.\n"
            "When the caller clearly selects one of the offered alternatives, "
            "update DATE and TIME to the exact date and time of that alternative "
            "and use CREATE_APPOINTMENT.\n"
            "Do not use APPOINTMENT_CONFIRMED until the system has checked the "
            "selected alternative and explicitly asks for confirmation.\n\n"

            "Current appointment information:\n"
            f"title = {appointment['title']}\n"
            f"date = {appointment['date']}\n"
            # f"spoken_date = {spoken_date}\n"
            f"time = {appointment['time']}\n"
            f"duration_minutes = {appointment['duration_minutes']}\n"
            f"alternatives = {appointment['alternatives']}\n\n"

            "If the caller wants an appointment, collect the required "
            "information across multiple turns.\n\n"

            "Required information:\n"
            "- title\n"
            "- date\n"
            "- time\n\n"
            
            "Date format rule:\n"
            "Always return DATE in YYYY-MM-DD format.\n"
            "Never return words such as today, tomorrow, Sunday, Monday, "
            "or other natural-language dates in the DATE field.\n\n"
    
            "Spoken date and time rule:\n"
            "DATE and TIME are internal values for the appointment system. "
            "They are NOT meant to be read aloud as written.\n"
            "When speaking to the caller, always translate dates and times "
            "into natural conversational language before saying them.\n"
            "Never read dates digit-by-digit or as numbers separated by "
            "the word 'dash'. Never read times as military time, 'hundred hours', "
            "or any other robotic or technical format.\n"
            "Speak as a normal human telephone secretary would speak.\n"
            "Use natural spoken date and time expressions appropriate to the "
            "caller's current language and locale. "
            "Do not read dates or times in a technical or machine-like format. "
            "Do not speak the year unless it is necessary for clarity.\n"
            "Prefer normal conversational forms used by native speakers of the "
            "caller's language rather than reading the internal DATE and TIME values literally.\n\n"

            "Do not ask for information that the caller has already provided.\n\n"

            "When all required information has been collected, use "
            "CREATE_APPOINTMENT. Do not ask for confirmation yet. "
            "The system will check availability before asking for confirmation.\n\n"

            "When asking for confirmation, use action CONFIRM_APPOINTMENT.\n\n"

            "If the caller clearly confirms, use action APPOINTMENT_CONFIRMED.\n\n"

            "If the caller clearly rejects or cancels the appointment, "
            "use action APPOINTMENT_CANCELLED.\n\n"

            "Use the ISO 639-1 two-letter language code for LANGUAGE, "
            "such as it for Italian, en for English, fr for French, "
            "de for German, es for Spanish, and so on.\n\n"
            
            "Return exactly this format:\n"
            "LANGUAGE: <ISO 639-1 language code>\n"
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
            "APPOINTMENT_CANCELLED\n"
            "CHOOSING_ALTERNATIVE\n"

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
            "LANGUAGE: <ISO 639-1 language code>\n"
            "ACTION: CONFIRM_APPOINTMENT\n"
            "TITLE: Dentist\n"
            "DATE: 2026-08-26\n"
            "TIME: 10:00\n"
            "DURATION: NONE\n"
            "RESPONSE: I have a dentist appointment tomorrow at 10 AM. "
            "Shall I add it to your calendar?\n\n"

            "Example confirmation response:\n"
            "LANGUAGE: <ISO 639-1 language code>\n"
            "ACTION: APPOINTMENT_CONFIRMED\n"
            "TITLE: Dentist\n"
            "DATE: 2026-08-26\n"
            "TIME: 10:00\n"
            "DURATION: NONE\n"
            "RESPONSE: Certainly. I'll add the dentist appointment "
            "to your calendar.\n\n"

            "Example cancellation:\n"
            "LANGUAGE: <ISO 639-1 language code>\n"
            "ACTION: APPOINTMENT_CANCELLED\n"
            "TITLE: NONE\n"
            "DATE: NONE\n"
            "TIME: NONE\n"
            "DURATION: NONE\n"
            "RESPONSE: No problem. I won't add the appointment."
        )
    }]

    messages.extend(call.messages)

    ai_request_start = time.perf_counter()

    response = client.chat.completions.create(model="gpt-5.4-mini", messages=messages)

    ai_request_end = time.perf_counter()

    print("[TIMING] OpenAI AI request:", round(ai_request_end - ai_request_start, 3), "seconds")

    raw_answer = response.choices[0].message.content.strip()

    print()
    print("AI raw response:")
    print(raw_answer)

    action = "NONE"
    answer = raw_answer

    for line in raw_answer.splitlines():
        if line.startswith("LANGUAGE:"):
            value = line.replace("LANGUAGE:", "", 1).strip()

            if value:
                call.language = value

        elif line.startswith("ACTION:"):
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

def generate_availability_response(call, alternatives):
    appointment = call.appointment

    formatted_slots = ", ".join(
        f"{slot['date']} {slot['time']}"
        for slot in alternatives
    )

    messages = [{
        "role": "system",
        "content": (
            "You are a professional and friendly telephone secretary. "
            "Respond in the caller's current language. "
            "Speak naturally and concisely, as the response will be spoken aloud.\n\n"

            "The requested appointment time is not available. "
            "Tell the caller that the requested time is unavailable, "
            "provide the available alternatives, and ask whether one of them works.\n\n"

            "Current conversation language:\n"
            f"{call.language}\n\n"

            "Requested appointment:\n"
            f"title = {appointment['title']}\n"
            f"date = {appointment['date']}\n"
            f"time = {appointment['time']}\n\n"

            "Available alternatives:\n"
            f"{formatted_slots}\n\n"

            "Return only the spoken response. "
            "Do not include labels, explanations, or technical information."
        )
    }]

    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=messages
    )

    return response.choices[0].message.content.strip()

def generate_appointment_confirmation_response(call):
    appointment = call.appointment

    messages = [{
        "role": "system",
        "content": (
            "You are a professional and friendly telephone secretary. "
            "Respond in the caller's current language. "
            "Speak naturally and concisely, as the response will be spoken aloud.\n\n"

            "The requested appointment time is available. "
            "Tell the caller that the requested appointment time is available "
            "and ask whether they would like you to add it to their calendar.\n\n"

            "Current conversation language:\n"
            f"{call.language}\n\n"

            "Appointment:\n"
            f"title = {appointment['title']}\n"
            f"date = {appointment['date']}\n"
            f"time = {appointment['time']}\n\n"

            "Use natural spoken date and time expressions appropriate to "
            "the caller's language.\n\n"

            "Return only the spoken response. "
            "Do not include labels, explanations, or technical information."
        )
    }]

    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=messages
    )

    return response.choices[0].message.content.strip()

def generate_appointment_created_response(call):
    messages = [{
        "role": "system",
        "content": (
            "You are a professional and friendly telephone secretary. "
            "Respond in the caller's current language. "
            "Speak naturally and concisely, as the response will be spoken aloud.\n\n"

            "The appointment has now been successfully added to the calendar. "
            "Tell the caller that the appointment has been successfully added.\n\n"

            "Current conversation language:\n"
            f"{call.language}\n\n"

            "Appointment:\n"
            f"title = {call.appointment['title']}\n"
            f"date = {call.appointment['date']}\n"
            f"time = {call.appointment['time']}\n\n"

            "Use natural spoken date and time expressions appropriate to "
            "the caller's language.\n\n"

            "Return only the spoken response. "
            "Do not include labels, explanations, or technical information."
        )
    }]

    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=messages
    )

    return response.choices[0].message.content.strip()

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