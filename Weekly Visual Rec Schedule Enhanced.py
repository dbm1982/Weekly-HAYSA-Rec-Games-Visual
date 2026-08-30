import requests
from ics import Calendar
from datetime import datetime, timedelta
import re, ssl, pytz, os
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import PatternFill

# --- iCal Feed ---
ical_url = "https://calendar.google.com/calendar/ical/6bl9ubrc8vssoqi0jm1l7ljpc05ngqrt%40import.calendar.google.com/public/basic.ics"

local_tz = pytz.timezone("America/New_York")
today = datetime.now(local_tz).date()
cutoff_date = today

# --- Color Map ---
color_map = {
    "Blue": "#4996D1",
    "Red": "#E88989",
    "Green": "#429964",
    "Orange": "#FCB03A",
    "Berry": "#E8DAEF",
    "Gray": "#F2F3F4"
}

# --- Helpers ---
def parse_team(raw_team):
    match = re.match(r"(.+?)\s*\((.*?)\s*-\s*(.*?)\)", raw_team)
    if match:
        name = match.group(1).strip()
        coach = match.group(2).strip()
        color = match.group(3).strip()
        return f"{name} ({coach})", color
    return raw_team.strip(), "Gray"

def extract_group(team_name):
    match = re.search(r"(\d+(?:/\d+)*\s+(Boys|Girls))", team_name)
    if match:
        return match.group(1)
    if "Kindergarten" in team_name:
        return "Kindergarten"
    return ""

def extract_division(description):
    match = re.search(r"(\d+(?:/\d+)*\s+(Boys|Girls))", description or "")
    if match:
        return match.group(1)
    if "Kindergarten" in description:
        return "Kindergarten"
    return ""

def format_field(raw_field):
    if "H-SuSS" in raw_field:
        return "Snack Shack Area"
    if not raw_field or len(raw_field) < 5:
        return raw_field
    trimmed = raw_field[4:].split(",")[0].strip()
    match = re.match(r"([A-Z]*)(\d+)([A-Z]*)", trimmed)
    if match:
        _, number, suffix = match.groups()
        return f"Field {number}{suffix}" if suffix else f"Field {number}"
    return f"Field {trimmed}"

def field_sort_key(field_label):
    match = re.match(r"Field\s+(\d+)([A-Z]?)", field_label)
    if match:
        number = int(match.group(1))
        suffix = match.group(2)
        return (number, suffix)
    return (999, "")

# --- Load Calendar ---
ssl._create_default_https_context = ssl._create_unverified_context

print("📡 Fetching ICS feed...")
ics_text = requests.get(ical_url).text

if "<!DOCTYPE html>" in ics_text[:200]:
    raise Exception("❌ ICS feed returned HTML instead of ICS.")

calendar = Calendar(ics_text)
print("✅ ICS feed loaded successfully.")

# --- Group Events ---
games_by_date = defaultdict(list)

for event in calendar.events:
    local_start = event.begin.datetime.astimezone(local_tz)
    game_date = local_start.date()

    if game_date <= cutoff_date:
        continue

    time_label = local_start.strftime("%I:%M %p").lstrip("0")
    sort_key = local_start.strftime("%H:%M")
    name = event.name
    location = event.location or ""
    description = event.description or ""

    if "Practice" in name:
        continue
    if any(k in name for k in ["3/4", "5/6", "7/8"]) and "vs." in name:
        continue
    if "vs." not in name:
        continue

    team1_raw, team2_raw = name.split("vs.")
    team1, color1 = parse_team(team1_raw.strip())
    team2, color2 = parse_team(team2_raw.strip())
    group = extract_group(team1_raw.strip()) or extract_group(team2_raw.strip
