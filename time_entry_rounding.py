#!/usr/bin/env python3
"""
File name: time_entry_rounding.py
Author: Søren S. Mikkelsen
Created on: March 9, 2024
Description:

This script is designed to adjust time logs within Toggl by rounding time
entries to the nearest 15-minute interval. It incorporates additional
administrative time to ensure each workday reflects a total of 8 hours.

The script encompasses various Python modules and a TimeEntry class to handle
time-related computations, including rounding, truncation, and serialization of
time entries. It includes functions to interact with the Toggl API, retrieve and
update time logs, and generate administrative time entries when needed to make
up shortfalls in daily working hours.
"""
import argparse
import base64
import datetime
import json
import os
import sys
from datetime import date, timedelta

import pytz
import requests
from dateutil.parser import parse
from dotenv import load_dotenv
from loguru import logger


class TimeEntryEncoder(json.JSONEncoder):
    """
    An encoder class inheriting from JSONEncoder for serializing TimeEntry objects.
    """

    # Overrides the default method to provide JSON serialization for TimeEntry and datetime objects.
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        if isinstance(obj, TimeEntry):
            return obj.__dict__


class TimeEntry:
    """
    A class used to represent a Time Entry with methods to handle initialization and representation.
    It manipulates time data for various purposes, like truncating to minutes and rounding to quarters.
    Attributes represent different aspects of a time entry such as start, stop, duration, project ID, etc.
    """

    # Initialization method with optional parameters for various time entry attributes.
    def __init__(
        self,
        start=None,
        stop=None,
        duronly=None,
        pid=None,
        billable=None,
        guid=None,
        at=None,
        wid=None,
        id=None,
        uid=None,
        description=None,
        duration=None,
        tags=None,
        workspace_id=None,
        project_id=None,
        task_id=None,
        tag_ids=None,
        server_deleted_at=None,
        user_id=None,
        permissions=None,
    ):
        self.description = description
        self.tags = tags

        # Process start and stop times, if provided, and calculate duration.
        if start is not None:
            self.start = self._round_to_quarter_hour(
                self._truncate_seconds(parse(start))
            )

        if stop is not None:
            self.stop = self._round_to_quarter_hour(self._truncate_seconds(parse(stop)))

        if start is not None and stop is not None:
            self.duration = (self.stop - self.start).seconds

        self.duronly = duronly
        self.pid = pid
        self.billable = billable
        self.guid = guid
        self.at = at
        self.wid = wid
        self.id = id
        self.uid = uid
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.task_id = task_id
        self.tags_id = tag_ids
        self.user_id = user_id

    def __repr__(self):
        return "{0}".format(self.__dict__)

    def _truncate_seconds(self, dt):
        """
        Truncates seconds from a datetime object.
        """
        return dt.replace(second=0, microsecond=0)

    def _round_to_quarter_hour(self, dt):
        """
        Rounds a datetime object to the nearest quarter-hour.
        """
        round_minutes = ((dt.minute + 7) // 15) * 15
        return dt + timedelta(minutes=round_minutes - dt.minute)


def get_headers():
    """
    Generates authentication headers for the Toggl API using an environment variable storing the API key.
    """
    api_key = os.getenv("TOGGL_API_KEY")
    if not api_key:
        logger.error(
            "'TOGGL_API_KEY' environment variable not set. Please set this variable to continue."
        )
        sys.exit(1)

    base64_token = base64.b64encode(f"{api_key}:api_token".encode()).decode()
    return {
        "Authorization": f"Basic {base64_token}",
        "content-type": "application/json",
    }


def get_time_entries(start_date=None, end_date=None):
    """
    Retrieves time entries from Toggl API within a specified date range.
    """
    headers = get_headers()
    url = "https://api.track.toggl.com/api/v9/me/time_entries"
    params = {}
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        logger.error(
            f"Failed to get time entries: Response: {response.status_code} - {response.text}"
        )
        return []

    return [TimeEntry(**entry) for entry in response.json()]


def get_last_time_for_day(date_string, entries):
    """
    Determines the latest stop time for time entries on a given date.
    """
    latest_time = date.min
    target_date = parse(date_string).date()

    # Obtain the latest time entry for the specified date.
    for entry in sorted(
        [e for e in entries if e.start.date() == target_date], key=lambda x: x.start
    ):
        if hasattr(entry, "stop") and entry.stop > latest_time:
            latest_time = entry.stop

    return latest_time if latest_time != date.min else None


def get_time_per_day(entries):
    """
    Aggregates total duration per day from a list of TimeEntry objects.
    """
    time_per_day = {}
    for entry in entries:
        day_key = entry.start.date().isoformat()
        time_per_day[day_key] = time_per_day.get(day_key, 0) + entry.duration
    return time_per_day


def fill_with_admin_time(entries):
    """
    Fills shortfall in work hours with administrative time to ensure 8 hours per day.
    """
    time_per_day = _get_time_per_day(entries)
    admin_entries = []
    eight_hours_in_seconds = 8 * 60 * 60

    # Create administrative time entries where necessary.
    for date_key, duration in time_per_day.items():
        if duration < eight_hours_in_seconds:
            additional_time_needed = eight_hours_in_seconds - duration
            last_time = _get_last_time_for_day(date_key, entries)
            entry = TimeEntry(
                start=last_time.isoformat(),
                stop=_round_to_quarter_hour(
                    last_time + timedelta(seconds=additional_time_needed)
                ).isoformat(),
                wid=876389,
                pid=12780480,
                description="Admin",
            )
            admin_entries.append(entry)

    return admin_entries


def update_entries(entries):
    """
    Submits updates for TimeEntry objects to the Toggl API.
    """
    headers = get_headers()

    for entry in entries:
        url = f"https://api.track.toggl.com/api/v9/workspaces/{entry.workspace_id}/time_entries/{entry.id}"
        json_data = json.dumps(entry, cls=TimeEntryEncoder)
        response = requests.put(url, headers=headers, data=json_data)

        if response.status_code != 200:
            logger.error(f"Failed to update time: {response.text}")
            continue


def main():
    """
    Entry point for the script to process time entries from Toggl.
    """
    parser = argparse.ArgumentParser(description="Process time entries from Toggl")

    parser.add_argument(
        "number_of_days_from_today",
        type=int,
        nargs="?",
        default=1,
        help="Number of days from today to process time entries",
    )

    # Parse command line arguments
    args = parser.parse_args()

    utc_now = datetime.datetime.now(pytz.utc)
    date = utc_now - timedelta(days=args.number_of_days_from_today)
    start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)

    period = {"start_date": start_date, "end_date": utc_now}
    logger.info(f"Getting time entries from {start_date:%Y-%m-%d} to now")
    entries = get_time_entries(**period)
    logger.info(f"Fetched {len(entries)} Toggl entries from {date:%Y-%m-%d %H:%M:%S}")

    # Update time entries
    update_entries(entries)

    # fill in administrative time as needed
    # admin_entries = fill_with_admin_time(entries)
    # update_entries(admin_entries)

    logger.info("Update complete.")


if __name__ == "__main__":
    load_dotenv()
    main()
