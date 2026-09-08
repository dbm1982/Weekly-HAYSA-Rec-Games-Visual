import requests, ssl, re
from ics import Calendar
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
import random

# --- ICS Feed ---
ical_url = "https://calendar.google.com/calendar/ical/6bl9ubrc8vssoqi0jm1l7ljpc05ngqrt%40import.calendar.google.com/public/basic.ics"

local_tz = pytz.timezone("America/New_York")
today = datetime.now(local_tz).date()

# --- Travel Towns (second filter) ---
travel_towns = {
    "Stoughton", "Sharon", "Raynham", "Bridgewater", "Mansfield",
    "Canton", "Foxboro", "Easton", "Taunton", "Whitman", "Abington",
    "Quincy"  # Added because ICS contains Quincy Travel games
}

# --- Field Map Coordinates ---
field_positions = {
    "Field 1":   { "x": 40.0, "y": 16.5, "width": 17.5, "height": 15.0 },
    "Field 2":   { "x": 60.0, "y": 16.5, "width": 17.5, "height": 15.0 },
    "Field 3":   { "x": 15, "y": 75.5, "width": 14.5, "height": 19, "rotate": 7.5 },
    "Field 4":   { "x": 39.5, "y": 69, "width": 27, "height": 9.3, "rotate": 4.8 },
    "Field 1B":  { "x": 40.0, "y": 15.7, "width": 17.0, "height": 13.0 },
    "Field 2B":  { "x": 60.0, "y": 15.7, "width": 17.0, "height": 13.0 },
    "Field 1A":  { "x": 40.0, "y": 24.2, "width": 17.0, "height": 13.0 },
    "Field 2A":  { "x": 60.0, "y": 24.2, "width": 17.0, "height": 13.0 },
    "Field 4A":  { "x": 36.5, "y": 68, "width": 20, "height": 10.5, "rotate": 4.9 },
    "Field 4B":  { "x": 55.5, "y": 69, "width": 20, "height": 10.5, "rotate": 4.9 },
}

# --- Helpers ---
def parse_team(raw_team):
    raw_team = raw_team.strip()

    # Matches: Team Name (Coach-Color)
    match = re.match(r"^(.*?)\s*\(([^()-]+)-([^()]+)\)$", raw_team)
    if match:
        team_name = match.group(1).strip()
        coach = match.group(2).strip()
        color = match.group(3).strip()
        return f"{team_name} ({coach})", color

    # Travel or malformed → coach only
    match = re.match(r"^(.*?)\s*\(([^()]+)\)$", raw_team)
    if match:
        team_name = match.group(1).strip()
        coach = match.group(2).strip()
        return f"{team_name} ({coach})", "Gray"

    return raw_team, "Gray"


def extract_division(description):
    if not description:
        return ""
    match = re.search(r"(\d+(?:/\d+)*\s+(Boys|Girls)(?:\s+Travel)?)", description)
    if match:
        return match.group(1)
    if "Kindergarten" in description:
        return "Kindergarten"
    return ""


# ⭐ UNIFIED FIELD PARSER (same logic as enhanced script)
def format_field(raw_field):
    if not raw_field:
        return raw_field

    core = raw_field.split(",", 1)[0].strip()

    # Snack Shack
    if core == "H-SuSS":
        return "Snack Shack Area"

    # Sumner A/B fields
    m = re.match(r"^H-Su(\d)([A-Z])$", core)
    if m:
        num, suffix = m.groups()
        return f"Field {num}{suffix}"

    # Sumner full fields
    m = re.match(r"^H-Su(\d)$", core)
    if m:
        num = m.group(1)
        return f"Field {num}"

    # Sean Joyce A/B fields
    m = re.match(r"^H-SJ(\d)([A-Z])$", core)
    if m:
        num, suffix = m.groups()
        return f"Field {num}{suffix}"

    # Sean Joyce full fields
    m = re.match(r"^H-SJ(\d)$", core)
    if m:
        num = m.group(1)
        return f"Field {num}"

    # External fields (travel opponents)
    m = re.match(r"^[A-Z]+-(.+)$", core)
    if m:
        return f"Field {m.group(1)}"

    return core


def time_sort_key(t):
    return datetime.strptime(t, "%I
