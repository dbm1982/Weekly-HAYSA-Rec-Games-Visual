import requests, ssl, re, webbrowser
from ics import Calendar
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

# --- Config ---
ical_url = "https://calendar.google.com/calendar/ical/6bl9ubrc8vssoqi0jm1l7ljpc05ngqrt%40import.calendar.google.com/public/basic.ics"

local_tz = pytz.timezone("America/New_York")
today = datetime.now(local_tz).date()

# --- Field Map Settings ---
allowed_times = {"8:30 AM", "9:45 AM", "11:00 AM", "11:30 AM"}
full_block_divisions = {"3/4 Girls", "3/4 Boys", "5/6/7 Girls", "5/6/7 Boys"}
side_by_side_fields = {"Field 1A", "Field 1B", "Field 2A", "Field 2B", "Field 4"}
enlarged_blocks_fields = {"Field 1", "Field 2", "Field 3"}
enlarged_blocks_divisions = {"3/4 Girls", "3/4 Boys", "5/6/7 Girls", "5/6/7 Boys"}

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

color_map = {
    "Blue": "#4996D1",
    "Red": "#E88989",
    "Green": "#429964",
    "Orange": "#FCB03A"
}

# --- Helpers ---
def parse_team(raw_team):
    match = re.match(r".*?\((.*?)\s*-\s*(.*?)\)", raw_team)
    if match:
        coach = match.group(1).strip()
        color = match.group(2).strip()
        return coach, color
    return raw_team.strip(), "Gray"

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

def time_sort_key(t):
    return datetime.strptime(t, "%I:%M %p")

# --- Load ICS ---
ssl._create_default_https_context = ssl._create_unverified_context
ics_text = requests.get(ical_url).text

if "<!DOCTYPE html>" in ics_text[:200]:
    raise Exception("ICS feed returned HTML instead of ICS.")

calendar = Calendar(ics_text)

# --- Extract all future games ---
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

    time_label = local_start.strftime("%I:%M %p").lstrip("0")
    team1_raw, team2_raw = name.split("vs.")
    team1, color1 = parse_team(team1_raw.strip())
    team2, color2 = parse_team(team2_raw.strip())
    field = format_field(location)
    division = extract_division(description)

    future_games[game_date].append({
        "time": time_label,
        "field": field,
        "team1": team1,
        "color1": color1,
        "team2": team2,
        "color2": color2,
        "division": division
    })

# --- Determine upcoming Saturday ---
next_saturday = today + timedelta((5 - today.weekday()) % 7)

games_this_sat = future_games.get(next_saturday, [])

# --- Determine next date with games ---
next_game_date = None
for d in sorted(future_games.keys()):
    if future_games[d]:
        next_game_date = d
        break

# --- HTML Output ---
output_html = "map_overlay_enhanced.html"
image_path = "assets/field_map.jpeg"

with open(output_html, "w", encoding="utf8") as f:
    f.write("<html><head><style>\n")
    f.write("""
        body { font-family: sans-serif; background: #fff; padding: 20px; }
        .map-grid { display: flex; flex-wrap: wrap; gap: 20px; }
        .map-column { flex: 1; min-width: 300px; text-align: center; }
        .map-container { position: relative; width: 100%; max-width: 400px; margin: auto; }
        .field-map { width: 100%; display: block; }
        .match-overlay { position: absolute; font-size: 0.65em; background: white; border: 0.5px solid black;
            text-align: center; padding: 4px 2px; box-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
        .team-left, .team-right { font-weight: bold; padding: 6px 2px; color: #000; }
        .division-label { font-size: 0.75em; font-weight: bold; margin-top: 2px; }
    """)
    f.write("</style></head><body>\n")

    # --- Small message if no games this Saturday ---
    if not games_this_sat:
        f.write(f"""
        <p style="color:#666; font-style:italic; font-size:0.85em;">
            No games scheduled for Saturday, {next_saturday.strftime('%B %d')}
        </p>
        """)

    # --- Next game day heading ---
    if next_game_date:
        f.write(f"<h1>Next game day: {next_game_date.strftime('%A, %B %d')}</h1>\n")
    else:
        f.write("<h1>No upcoming games found.</h1>")
        f.write("</body></html>")
        exit(0)

    # --- Render next game day map ---
    games = future_games[next_game_date]
    games_by_block = defaultdict(list)
    for m in games:
        games_by_block[m["time"]].append(m)

    f.write("<div class='map-grid'>\n")

    for block in sorted(games_by_block.keys(), key=time_sort_key):
        f.write(f"<div class='map-column'><h2>{block}</h2>\n")
        f.write(f"<div class='map-container'><img src='{image_path}' class='field-map'>\n")

        for matchup in games_by_block[block]:
            field = matchup["field"]
            pos = field_positions.get(field)
            if not pos:
                continue

            height = f"{pos['height']}%"
            left = f"{pos['x']}%"
            top = f"{pos['y']}%"
            width = f"{pos['width']}%"
            rotation = pos.get("rotate", 0)
            transform = f"rotate({rotation}deg)" if rotation else "none"

            f.write(f"<div class='match-overlay' style='left:{left}; top:{top}; width:{width}; height:{height}; transform:{transform};'>\n")
            f.write(f"<div class='team-left' style='background-color:{color_map.get(matchup['color1'], '#ccc')}'>{matchup['team1']}</div>\n")
            f.write(f"<div class='team-right' style='background-color:{color_map.get(matchup['color2'], '#ccc')}'>{matchup['team2']}</div>\n")
            f.write(f"<div class='division-label'>{matchup['division']}</div>\n")
            f.write("</div>\n")

        f.write("</div></div>\n")

    f.write("</div></body></html>")

print(f"✅ Overlay saved to: {output_html}")
