import requests
from ics import Calendar
from datetime import datetime, timedelta
import re, ssl, pytz
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import PatternFill
import random

# --- ICS Feed ---
ical_url = "https://calendar.google.com/calendar/ical/6bl9ubrc8vssoqi0jm1l7ljpc05ngqrt%40import.calendar.google.com/public/basic.ics"

local_tz = pytz.timezone("America/New_York")
today = datetime.now(local_tz).date()

# --- Travel Towns (second filter) ---
travel_towns = {
    "Stoughton", "Sharon", "Raynham", "Bridgewater", "Mansfield",
    "Canton", "Foxboro", "Easton", "Taunton", "Whitman", "Abington",
    "Quincy"
}

# --- Helpers ---
def parse_team(raw_team):
    match = re.match(r"(.+?)\s*`\((.*?)\s*-\s*(.*?)\)`", raw_team)
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
    if not description:
        return ""
    match = re.search(r"(\d+(?:/\d+)*\s+(Boys|Girls)(?:\s+Travel)?)", description)
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
        return (int(match.group(1)), match.group(2))
    return (999, "")

# --- Auto Color Detection ---
def get_color_map_from_schedule(future_games):
    known_colors = {
        "Blue": "#4996D1", "Red": "#E88989", "Green": "#429964",
        "Orange": "#FCB03A", "Berry": "#E8DAEF", "Gray": "#F2F3F4",
        "Black": "#000000", "White": "#FFFFFF", "Yellow": "#FFEB3B",
        "Purple": "#9B59B6", "Maroon": "#800000", "Teal": "#008080",
        "Pink": "#FFC0CB", "Gold": "#FFD700", "Silver": "#C0C0C0",
        "Navy": "#001F3F", "Royal Blue": "#4169E1",
        "Light Blue": "#ADD8E6", "Dark Green": "#006400",
    }

    auto_map = {}
    for date, games in future_games.items():
        for g in games:
            for c in (g[3], g[5]):
                if c not in auto_map:
                    auto_map[c] = known_colors.get(
                        c, "#{:06x}".format(random.randint(0x444444, 0xDDDDDD))
                    )
    return auto_map

# --- Load ICS ---
ssl._create_default_https_context = ssl._create_unverified_context
ics_text = requests.get(ical_url).text
calendar = Calendar(ics_text)

# --- Extract REC games only ---
future_games = defaultdict(list)

for event in calendar.events:
    local_start = event.begin.datetime.astimezone(local_tz)
    game_date = local_start.date()
    if game_date < today:
        continue

    name = event.name
    location = event.location or ""
    description = event.description or ""

    if "Practice" in name or "vs." not in name:
        continue

    team1_raw, team2_raw = name.split("vs.")
    team1_raw = team1_raw.strip()
    team2_raw = team2_raw.strip()

    # ⭐ Travel filter #1 — team names containing "Travel"
    if "Travel" in team1_raw or "Travel" in team2_raw:
        continue

    # ⭐ Travel filter #2 — team names matching towns
    if team1_raw in travel_towns or team2_raw in travel_towns:
        continue

    division = extract_division(description)

    # ⭐ Travel filter #3 — division contains "Travel"
    if "Travel" in division:
        continue

    time_label = local_start.strftime("%I:%M %p").lstrip("0")
    team1, color1 = parse_team(team1_raw)
    team2, color2 = parse_team(team2_raw)
    field = format_field(location)
    group = extract_group(team1_raw) or extract_group(team2_raw)

    future_games[game_date].append(
        [time_label, field, team1, color1, team2, color2, group, division]
    )

# --- Auto Color Map ---
color_map = get_color_map_from_schedule(future_games)

def safe_color(c):
    return color_map.get(c, "#DDDDDD")[1:]

# --- Determine next REC Saturday ---
next_saturday = today + timedelta((5 - today.weekday()) % 7)
games_this_sat = future_games.get(next_saturday, [])

# --- Determine next REC game day ---
next_game_date = next((d for d in sorted(future_games) if future_games[d]), None)

# --- Excel Output ---
excel_file = "non_core_games.xlsx"
wb = Workbook()
ws_default = wb.active
ws_default.title = "Placeholder"

for game_date in sorted(future_games.keys()):
    games = future_games[game_date]
    if not games:
        continue

    ws = wb.create_sheet(title=game_date.strftime("%Y-%m-%d"))
    ws.append(["Time", "Field", "Team 1", "
