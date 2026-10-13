from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file(
    "google_token.json",
    ["https://www.googleapis.com/auth/calendar.events"],
)

service = build("calendar", "v3", credentials=creds)

events = service.events().list(
    calendarId="primary",
    maxResults=10,
    singleEvents=True,
    orderBy="startTime",
).execute()

for event in events.get("items", []):
    print(event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
          "|",
          event.get("summary", "(no title)"))