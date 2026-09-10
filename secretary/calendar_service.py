from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = "google_token.json"

SCOPES = [
"https://www.googleapis.com/auth/calendar.events"
]

def get_calendar_service():
    """
    Create and return an authenticated Google Calendar service.
    """

    credentials = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES,
    )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
    )

def get_upcoming_events(max_results=10):
    """
    Return upcoming events from the user's primary calendar.
    """


    service = get_calendar_service()

    events = service.events().list(
        calendarId="primary",
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return events.get("items", [])
