from datetime import datetime

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


def get_events_between(start_time, end_time):
    """
    Return calendar events that overlap the requested time range.

    start_time and end_time must be timezone-aware datetime objects.
    """

    if start_time.tzinfo is None or end_time.tzinfo is None:
        raise ValueError(
            "start_time and end_time must include a timezone."
        )

    if end_time <= start_time:
        raise ValueError(
            "end_time must be later than start_time."
        )

    service = get_calendar_service()

    events = service.events().list(
        calendarId="primary",
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return events.get("items", [])


def is_available(start_time, end_time):
    """
    Return True if the requested time range has no calendar events.
    """

    events = get_events_between(
        start_time,
        end_time,
    )

    return len(events) == 0

def create_event(
    title,
    start_time,
    end_time,
    description=None,
):
    """
    Create an event in the user's primary Google Calendar.

    start_time and end_time must be timezone-aware datetime objects.
    """

    if start_time.tzinfo is None or end_time.tzinfo is None:
        raise ValueError(
            "start_time and end_time must include a timezone."
        )

    if end_time <= start_time:
        raise ValueError(
            "end_time must be later than start_time."
        )

    service = get_calendar_service()

    event = {
        "summary": title,
        "start": {
            "dateTime": start_time.isoformat(),
        },
        "end": {
            "dateTime": end_time.isoformat(),
        },
    }

    if description:
        event["description"] = description

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
    ).execute()

    return created_event