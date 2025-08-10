import os
from mcp.server.fastmcp import FastMCP
from tools.google import CalendarTool

mcp = FastMCP(
    'Google Calendar',
    dependencies=[
        'google-api-python-client',
        'google-auth-httplib2',
        'google-auth-oauthlib'
    ],
)

if 'tutorial-claude-desktop-mcp' not in os.getcwd():
    calendar_tool = CalendarTool('F:\\PythonVenv\\tutorial-claude-desktop-mcp\\client-secret.json')

mcp.add_tool(calendar_tool.create_calendar, name='Create-Calendar', description='Create a new calendar')
mcp.add_tool(calendar_tool.add_calendar_event, name='Create-Calendar-Event', description='Create a new calendar event')
mcp.add_tool(calendar_tool.delete_calendar, name='Delete-Calendar', description='Delete a calendar')
mcp.add_tool(calendar_tool.list_calendars, name='List-Calendars', description='List all calendars')
mcp.add_tool(calendar_tool.search_calendar, name='Search-Calendar', description='Search for a calendar')
mcp.add_tool(calendar_tool.delete_calendar_event, name='Delete-Calendar-Event', description='Delete a calendar event')
mcp.add_tool(calendar_tool.list_calendar_events, name='List-Calendar-Events', description='List all events in a calendar')
mcp.add_tool(calendar_tool.search_calendar_event, name='Search-Calendar-Event', description='Search for a calendar event')
mcp.add_tool(calendar_tool.update_calendar_event, name='Update-Calendar-Event', description='Update a calendar event')