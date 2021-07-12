from icalendar import Calendar
from datetime import datetime, timedelta
from pytz import timezone

import requests
import json
import os
import configparser
import re
import cgi

# Set the timezone we are going to use
eastern = timezone('US/Eastern')
utc = timezone('UTC')

class Event:
    def __init__(self, date_start, date_end, summary, description, location):
        # Currently, this means the event was generated as a multiday event.
        if isinstance(date_start, datetime) and isinstance(date_start, datetime):
            self.fullstartdate = date_start.astimezone(eastern)
            self.fullenddate = date_end.astimezone(eastern)
            self.date_start = date_start.astimezone(eastern).strftime("%A, %B %d")
            self.date_end = date_end.astimezone(eastern).strftime("%A, %B %d")
            self.time_start = date_start.astimezone(eastern).strftime("%I:%M%p")
            self.time_end = date_end.astimezone(eastern).strftime("%I:%M%p")
        else:
            self.fullstartdate = date_start.dt.astimezone(eastern)
            self.fullenddate = date_end.dt.astimezone(eastern)
            self.date_start = date_start.dt.astimezone(eastern).strftime("%A, %B %d")
            self.date_end = date_end.dt.astimezone(eastern).strftime("%A, %B %d")
            self.time_start = date_start.dt.astimezone(eastern).strftime("%I:%M%p")
            self.time_end = date_end.dt.astimezone(eastern).strftime("%I:%M%p")
        self.location = location
        self.summary = summary
        self.short_description = self.__adjustShortDescription(description)
        self.facebook_event_url = self.__getFacebookEventUrl(description)
        self.description = self.__adjustDescription(description)

    def __adjustShortDescription(self, description):
        # We don't want to write html directly from whatever we see in the JSON file.
        # description = cgi.escape(description)

        if (len(description) > 300):
            description = description[0:300] + "..."

        # convert \n to <br/>
        description = description.replace('\n', '<br/>')
        
        return description

    def __adjustDescription(self, description):
        # We don't want to write html directly from whatever we see in the JSON file.
        # description = cgi.escape(description)

        # Replace all URLS with clickable links.
        pattern = re.compile(r"(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)")
        description = pattern.sub(r"<a href='\1'>\1</a>", description)
        
        # convert \n to <br/>
        description = description.replace('\n', '<br/>')

        return description

    def __getFacebookEventUrl(self, description):
        urls = re.findall(r"https?://www\.facebook\.com/events/\d+/", description)
        if (len(urls) == 1):
            return urls[0]
        else:
            return None

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
            # If events are multi-day, split them up.  
            if isEventMultiDay(date_start, date_end):
                eventsToAppend = getEventsForMultiDay(date_start, date_end, summary, description, location)
                events = events + eventsToAppend
            else:
                events.append(Event(date_start, date_end, summary, description, location))
    return events

def isEventMultiDay(date_start, date_end):
    date_start = date_start.dt.astimezone(eastern)
    date_end = date_end.dt.astimezone(eastern)
    return date_start.date() != date_end.date()

def getEventsForMultiDay(date_start, date_end, summary, description, location):
    datetime_start = date_start.dt.astimezone(eastern)
    datetime_end = date_end.dt.astimezone(eastern)

    events = []
    theRange = (datetime_end - datetime_start).days + 1
    for i in range(theRange):
        new_date_start = datetime_start if i == 0 else datetime(datetime_start.year, datetime_start.month, datetime_start.day, 0, 0, 0, 0, eastern) + timedelta(days=i)
        new_date_end = datetime_end if i == theRange-1 else datetime(datetime_start.year, datetime_start.month, datetime_start.day, 23, 59, 0, 0, eastern) + timedelta(days=i)
        events.append(Event(new_date_start, new_date_end, summary, description, location))
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
