from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from .google_apis import create_service

# ==============================================================
# Pydantic Models for Data Representation
# ==============================================================

class Calendar(BaseModel):
    """
    Represents a single Google Calendar.
    """
    id: str = Field(..., description="The ID of the calendar.")
    name: str = Field(..., description="The name of the calendar.")
    time_zone: str = Field(..., description="The time zone of the calendar.")
    description: str | None = Field(..., description="The description of the calendar.")


class Calendars(BaseModel):
    """
    Represents a collection of Google Calendars.
    """
    count: int = Field(..., description="The number of calendars.")
    calendars: list[Calendar] = Field(..., description="List of calendars.")
    next_page_token: str | None = Field(..., description="Token for the next page of results.")


class Attendee(BaseModel):
    """
    Represents an attendee of a calendar event.
    """
    email: str = Field(..., description="The email of the attendee.")
    display_name: str = Field(..., description="The display name of the attendee.")
    response_status: str | None = Field(..., description="The response status of the attendee.")


class CalendarEvent(BaseModel):
    """
    Represents a single calendar event.
    """
    id: str = Field(..., description="The ID of the calendar event.")
    name: str = Field(..., description="The name of the calendar event.")
    status: str = Field(..., description="The status of the calendar event.")
    description: str | None = Field(..., description="The description of the calendar event.")
    html_link: str = Field(..., description="The HTML link to the calendar event.")
    created: str = Field(..., description="The creation date of the calendar event.")
    updated: str = Field(..., description="The last updated date of the calendar event.")
    organizer_name: str = Field(..., description="The name of the event organizer.")
    organizer_email: str = Field(..., description="The email of the event organizer.")
    start_time: str = Field(..., description="The start time of the calendar event.")
    end_time: str = Field(..., description="The end time of the calendar event.")
    location: str | None = Field(..., description="The location of the calendar event.")
    time_zone: str = Field(..., description="The time zone of the calendar event.")
    attendees: list[Attendee] = Field(default_factory=list, description="List of event attendees.")


class CalendarEvents(BaseModel):
    """
    Represents a collection of calendar events.
    """
    count: int = Field(..., description="The number of calendar events.")
    events: list[CalendarEvent] = Field(..., description="List of calendar events.")
    next_page_token: str | None = Field(..., description="Token for the next page of results.")


# ==============================================================
# Calendar Tool Implementation
# ==============================================================

class CalendarTool:
    """
    A tool for interacting with the Google Calendar API.
    """
    API_NAME = 'calendar'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, client_secret_file: str) -> None:
        """
        Initialize the CalendarTool with authentication details.

        Args:
            client_secret_file: Path to the client secret JSON file for OAuth2 authentication.
        """
        self.client_secret_file = client_secret_file
        self._init_service()
        self.today = datetime.today()
        self.delta = timedelta(days=7)

    def _init_service(self) -> None:
        """
        Initialize the Google Calendar API service using the provided credentials.
        """
        self.service = create_service(
            self.client_secret_file,
            self.API_NAME,
            self.API_VERSION,
            self.SCOPES
        )

    # ----------------------------------------------------------
    # Calendar Management
    # ----------------------------------------------------------

    def list_calendars(
        self,
        max_results: int = 10,
        next_page_token: str | None = None,
    ) -> Calendars:
        """
        List calendars in the user's calendar list.
        """
        records = []
        current_page_token = next_page_token

        while True:
            response = self.service.calendarList().list(
                maxResults=min(max_results - len(records), 100),
                pageToken=current_page_token,
            ).execute()

            items = response.get('items', [])
            records.extend(items)

            current_page_token = response.get('nextPageToken')
            if not current_page_token or len(records) >= max_results:
                break

        calendars = [
            Calendar(
                id=record['id'],
                name=record['summary'],
                time_zone=record['timeZone'],
                description=record.get('description', None),
            )
            for record in records[:max_results]
        ]

        return Calendars(
            count=len(calendars),
            calendars=calendars,
            next_page_token=current_page_token,
        )

    def create_calendar(
        self,
        name: str,
        time_zone: str = 'America/Chicago',
        description: str | None = None,
    ) -> Calendar | str:
        """
        Create a new calendar.
        """
        calendar = {
            'summary': name,
            'timeZone': time_zone,
        }

        if description:
            calendar['description'] = description

        try:
            response = self.service.calendars().insert(body=calendar).execute()
        except Exception as e:
            return f'An error occurred: {str(e)}'

        return Calendar(
            id=response['id'],
            name=response['summary'],
            time_zone=response['timeZone'],
            description=response.get('description', None),
        )

    def delete_calendar(self, calendar_id: str) -> str:
        """
        Delete a calendar by its ID.
        """
        try:
            self.service.calendars().delete(calendarId=calendar_id).execute()
            return 'Calendar deleted'
        except Exception as e:
            return f'An error occurred: {str(e)}'

    def search_calendar(
        self,
        name: str,
        max_results: int = 10,
        case_sensitive: bool = False,
        next_page_token: str | None = None,
    ) -> Calendars:
        """
        Search for calendars by name.
        """
        records = []
        next_page_token_ = next_page_token
        remaining_results = max_results

        while True:
            response = self.service.calendarList().list(
                maxResults=min(remaining_results, 100),
                pageToken=next_page_token_,
            ).execute()

            items = response.get('items', [])

            for item in items:
                calendar_name = item['summary']
                search_name = name

                if not case_sensitive:
                    calendar_name = calendar_name.lower()
                    search_name = search_name.lower()

                if search_name in calendar_name:
                    records.append(item)

                if len(records) >= max_results:
                    break

            next_page_token_ = response.get('nextPageToken')

            if len(records) >= max_results or not next_page_token_ or len(items) == 0:
                break

            remaining_results = max_results - len(records)

        calendars = [
            Calendar(
                id=record['id'],
                name=record['summary'],
                time_zone=record['timeZone'],
                description=record.get('description', None),
            )
            for record in records
        ]

        return Calendars(
            count=len(calendars),
            calendars=calendars,
            next_page_token=next_page_token_,
        )

    # ----------------------------------------------------------
    # Event Management
    # ----------------------------------------------------------

    def list_calendar_events(
        self,
        calendar_id: str = 'primary',
        max_results: int = 10,
        time_min: str | None = None,
        time_max: str | None = None,
        next_page_token: str | None = None,
    ) -> CalendarEvents:
        """
        List events in a calendar.
        """
        if time_min is None:
            time_min = (self.today - self.delta).isoformat() + 'Z'

        if time_max is None:
            time_max = (self.today + self.delta).isoformat() + 'Z'

        records = []
        current_page_token = next_page_token

        while True:
            response = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=min(max_results - len(records), 100),
                pageToken=current_page_token,
            ).execute()

            items = response.get('items', [])
            records.extend(items)

            current_page_token = response.get('nextPageToken')
            if not current_page_token or len(records) >= max_results:
                break

        events = []
        for record in records[:max_results]:
            start = record.get('start', {})
            end = record.get('end', {})
            start_time = start.get('dateTime', start.get('date', ''))
            end_time = end.get('dateTime', end.get('date', ''))
            location = record.get('location', '')

            time_zone = start.get('timeZone') or end.get('timeZone', '')

            organizer = record.get('organizer', {})
            organizer_name = organizer.get('displayName', '')
            organizer_email = organizer.get('email', '')

            attendees_list = [
                Attendee(
                    email=attendee.get('email', ''),
                    display_name=attendee.get('displayName', ''),
                    response_status=attendee.get('responseStatus', '')
                )
                for attendee in record.get('attendees', [])
            ]

            events.append(
                CalendarEvent(
                    id=record['id'],
                    name=record.get('summary', ''),
                    description=record.get('description', ''),
                    status=record.get('status', ''),
                    html_link=record.get('htmlLink', ''),
                    created=record.get('created', ''),
                    updated=record.get('updated', ''),
                    organizer_name=organizer_name,
                    organizer_email=organizer_email,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    time_zone=time_zone,
                    attendees=attendees_list,
                )
            )

        return CalendarEvents(
            count=len(events),
            events=events,
            next_page_token=current_page_token,
        )
    
    def search_calendar_events(
        self,
        calendar_id: str = 'primary',
        query: str = '',
        max_results: int = 10,
        time_min: str | None = None,
        time_max: str | None = None,
        next_page_token: str | None = None,
    ) -> CalendarEvents:
        """
        Search events in a calendar by a query string.
        """
        if time_min is None:
            time_min = (self.today - self.delta).isoformat() + 'Z'

        if time_max is None:
            time_max = (self.today + self.delta).isoformat() + 'Z'

        records = []
        current_page_token = next_page_token

        while True:
            response = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                q=query,
                maxResults=min(max_results - len(records), 100),
                pageToken=current_page_token,
            ).execute()

            items = response.get('items', [])
            records.extend(items)

            current_page_token = response.get('nextPageToken')
            if not current_page_token or len(records) >= max_results:
                break

        events = []
        for record in records[:max_results]:
            start = record.get('start', {})
            end = record.get('end', {})
            start_time = start.get('dateTime', start.get('date', ''))
            end_time = end.get('dateTime', end.get('date', ''))
            location = record.get('location', '')

            time_zone = start.get('timeZone') or end.get('timeZone', '')

            organizer = record.get('organizer', {})
            organizer_name = organizer.get('displayName', '')
            organizer_email = organizer.get('email', '')

            attendees_list = [
                Attendee(
                    email=attendee.get('email', ''),
                    display_name=attendee.get('displayName', ''),
                    response_status=attendee.get('responseStatus', '')
                )
                for attendee in record.get('attendees', [])
            ]

            events.append(
                CalendarEvent(
                    id=record['id'],
                    name=record.get('summary', ''),
                    description=record.get('description', ''),
                    status=record.get('status', ''),
                    html_link=record.get('htmlLink', ''),
                    created=record.get('created', ''),
                    updated=record.get('updated', ''),
                    organizer_name=organizer_name,
                    organizer_email=organizer_email,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    time_zone=time_zone,
                    attendees=attendees_list,
                )
            )

        return CalendarEvents(
            count=len(events),
            events=events,
            next_page_token=current_page_token,
        )

    def add_calendar_event(
        self,
        calendar_id: str = 'primary',
        name: str = '',
        start_time: str = '',
        end_time: str = '',
        time_zone: str = 'America/Chicago',
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
    ) -> CalendarEvent | str:
        """
        Add a new event to a calendar.
        """
        event = {
            'summary': name,
            'start': {
                'dateTime': start_time,
                'timeZone': time_zone
            },
            'end': {
                'dateTime': end_time,
                'timeZone': time_zone
            }
        }

        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        try:
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
        except Exception as e:
            return f'An error occurred: {str(e)}'

        organizer = created_event.get('organizer', {})
        attendees_list = [
            Attendee(
                email=a.get('email', ''),
                display_name=a.get('displayName', ''),
                response_status=a.get('responseStatus', '')
            )
            for a in created_event.get('attendees', [])
        ]

        return CalendarEvent(
            id=created_event['id'],
            name=created_event.get('summary', ''),
            description=created_event.get('description', ''),
            status=created_event.get('status', ''),
            html_link=created_event.get('htmlLink', ''),
            created=created_event.get('created', ''),
            updated=created_event.get('updated', ''),
            organizer_name=organizer.get('displayName', ''),
            organizer_email=organizer.get('email', ''),
            start_time=created_event['start'].get('dateTime', ''),
            end_time=created_event['end'].get('dateTime', ''),
            location=created_event.get('location', ''),
            time_zone=time_zone,
            attendees=attendees_list,
        )

    def delete_calendar_event(self, calendar_id: str, event_id: str) -> str:
        """
        Delete an event from a calendar.
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return 'Event deleted'
        except Exception as e:
            return f'An error occurred: {str(e)}'

    def update_calendar_event(
        self,
        calendar_id: str,
        event_id: str,
        name: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        time_zone: str = 'America/Chicago',
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
    ) -> CalendarEvent | str:
        """
        Update an existing calendar event.
        """
        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
        except Exception as e:
            return f'An error occurred: {str(e)}'

        if name:
            event['summary'] = name
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        if start_time:
            event['start'] = {'dateTime': start_time, 'timeZone': time_zone}
        if end_time:
            event['end'] = {'dateTime': end_time, 'timeZone': time_zone}

        try:
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
        except Exception as e:
            return f'An error occurred: {str(e)}'

        organizer = updated_event.get('organizer', {})
        attendees_list = [
            Attendee(
                email=a.get('email', ''),
                display_name=a.get('displayName', ''),
                response_status=a.get('responseStatus', '')
            )
            for a in updated_event.get('attendees', [])
        ]

        return CalendarEvent(
            id=updated_event['id'],
            name=updated_event.get('summary', ''),
            description=updated_event.get('description', ''),
            status=updated_event.get('status', ''),
            html_link=updated_event.get('htmlLink', ''),
            created=updated_event.get('created', ''),
            updated=updated_event.get('updated', ''),
            organizer_name=organizer.get('displayName', ''),
            organizer_email=organizer.get('email', ''),
            start_time=updated_event['start'].get('dateTime', ''),
            end_time=updated_event['end'].get('dateTime', ''),
            location=updated_event.get('location', ''),
            time_zone=time_zone,
            attendees=attendees_list,
        )