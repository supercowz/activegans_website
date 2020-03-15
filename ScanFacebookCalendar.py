from icalendar import Calendar
from datetime import datetime, timedelta
from pytz import timezone

import requests
import json
import os
import configparser

# Set the timezone we are going to use
eastern = timezone('US/Eastern')
utc = timezone('UTC')

class Event:
    def __init__(self, date_start, date_end, summary, description, location):
        self.fullstartdate = date_start.dt.astimezone(eastern)
        self.fullenddate = date_end.dt.astimezone(eastern)
        self.date_start = date_start.dt.astimezone(eastern).strftime("%A, %B %d")
        self.date_end = date_end.dt.astimezone(eastern).strftime("%A, %B %d")
        self.time_start = date_start.dt.astimezone(eastern).strftime("%I:%M%p")
        self.time_end = date_end.dt.astimezone(eastern).strftime("%I:%M%p")
        self.summary = summary
        self.description = description.replace('\n', '<br/>')
        self.location = location

# We don't want to include events that have already occured.
def removePastEvents(events):
    eventsToReturn = []
    today = utc.localize(datetime.now())
    for event in events:
        if ((event.fullstartdate + timedelta(hours=8)) >= today):
            eventsToReturn.append(event)

    return eventsToReturn

def writeJsonFile(events):
    def converter(o):
        if isinstance(o, datetime):
            return o.__str__()

    dictEvents = [event.__dict__ for event in events]
    with open(settings["json_file_path"], "w") as write_file:
        json.dump(dictEvents, write_file, default=converter)

    os.chmod(settings["json_file_path"], 0o644)

def convertCalendarToListOfEvents(gcal):
    events = []
    for component in gcal.walk():
        if component.name == "VEVENT":
            #uid = component.get('uid')
            #organzier = component.get('organizer')
            date_start = component.get('dtstart')
            date_end = component.get('dtend')
            summary = component.get('summary')
            description = component.get('description')
            location = component.get('location')
            events.append(Event(date_start, date_end, summary, description, location))
    return events

def main():
    url = settings["calendar_url"]

    # get the ical file via the url
    response = requests.get(url)

    # convert calendar file to list of events
    gcal = Calendar.from_ical(response.text)
    events = convertCalendarToListOfEvents(gcal)

    # Remove events that have already occured
    events = removePastEvents(events)

    # sort the events by the full date descending
    events = sorted(events, key=lambda o: o.fullstartdate)

    # Write the final JSON write_file
    writeJsonFile(events)


# initialize the App Settings
config = configparser.ConfigParser()
config.read('settings.ini')
settings = config["AppSettings"]

main()
