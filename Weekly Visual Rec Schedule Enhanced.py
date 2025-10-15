import requests, ssl, re, webbrowser
from ics import Calendar
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

# --- Config ---
ical_url = "http://tmsdln.com/19hyx"
local_tz = pytz.timezone("America/New_York")
today = datetime.now(local_tz).date()
next_saturday = today + timedelta((5 - today.weekday()) % 7)
allowed_times = {"8:30 AM", "9:45 AM", "11:00 AM", "11:30 AM"}
full_block_divisions = {"3/4 Girls", "3/4 Boys", "5/6/7 Girls", "5/6/7 Boys"}
side_by_side_fields = {"Field 1A", "Field 1B", "Field 2A", "Field 2B", "Field 4"}
enlarged_blocks_fields = {"Field 1", "Field 2", "Field 3"}
enlarged_blocks_divisions = {"3/4 Girls", "3/4 Boys", "5/6/7 Girls", "5/6/7 Boys"}

# --- Field Coordinates ---
field_positions = {
    "Field 1":   { "x": 40.0, "y": 16.5, "width": 16.5, "height": 15.0 },
    "Field 2":   { "x": 60.0, "y": 16.5, "width": 16.5, "height": 15.0 },
    "Field 3":   { "x": 15, "y": 75.5, "width": 14.5, "height": 19, "rotate": 7.5 },
    "Field 4":   { "x": 39.5, "y": 69, "width": 27, "height": 9.3, "rotate": 4.8 },

    "Field 1B":  { "x": 40.0, "y": 15.7, "width": 17.0, "height": 13.0 }, "Field 2B":  { "x": 60.0, "y": 15.7, "width": 17.0, "height": 13.0 },
    "Field 1A":  { "x": 40.0, "y": 24.2, "width": 17.0, "height": 13.0 }, "Field 2A":  { "x": 60.0, "y": 24.2, "width": 17.0, "height": 13.0 },
    
    "Field 4A":  { "x": 36.5, "y": 68, "width": 20, "height": 10.5, "rotate": 4.9 }, "Field 4B":  { "x": 55.5, "y": 69, "width": 20, "height": 10.5, "rotate": 4.9 },
}

# --- Team Colors ---
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

# --- Load Calendar ---
ssl._create_default_https_context = ssl._create_unverified_context
calendar = Calendar(requests.get(ical_url).text)

# --- Extract Matchups ---
matchups = []
for event in calendar.events:
    local_start = event.begin.datetime.astimezone(local_tz)
    game_date = local_start.date()
    if game_date != next_saturday:
        continue

    time_label = local_start.strftime("%I:%M %p").lstrip("0")
    if time_label not in allowed_times:
        continue

    name = event.name
    location = event.location or ""
    description = event.description or ""

    if "Practice" in name or "vs." not in name:
        continue

    team1_raw, team2_raw = name.split("vs.")
    team1, color1 = parse_team(team1_raw.strip())
    team2, color2 = parse_team(team2_raw.strip())
    field = format_field(location)
    division = extract_division(description)

    if division == "":
        continue

    matchups.append({
        "time": time_label,
        "field": field,
        "team1": team1,
        "color1": color1,
        "team2": team2,
        "color2": color2,
        "division": division
    })

# --- Group Matchups ---
games_by_block = defaultdict(list)
for m in matchups:
    games_by_block[m["time"]].append(m)

# --- HTML Output ---
image_path = "assets/field_map.jpeg"
output_html = "map_overlay_enhanced.html"

f.write("<html><head><style>\n")
f.write("""body { font-family: sans-serif; background: #fff; padding: 20px; }
.map-grid { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 20px; }
.map-column { flex: 1; min-width: 300px; text-align: center; }
.map-container { position: relative; width: 100%; max-width: 400px; margin: auto; }
.field-map { width: 100%; display: block; }
.match-overlay { position: absolute; font-size: 0.65em; background: white; border: 0.5px solid black;
    text-align: center; padding: 4px 2px; box-shadow: 2px 2px 4px rgba(0,0,0,0.2); transform-origin: center;
    line-height: 1.2em; }
.team-left, .team-right { font-weight: bold; padding: 6px 2px; color: #000; line-height: 1.4em;
    display: flex; align-items: center; justify-content: center; overflow: hidden; white-space: nowrap;
    text-overflow: ellipsis; font-size: clamp(0.5em, 1.2vw, 0.85em); max-width: 100%; }
.diagonal-text { transform: rotate(-45deg); transform-origin: center; font-size: 0.6em; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; justify-content: center;
    height: 100%; }
.team-left { background-color: #eee; border-bottom: 1px solid #ccc; }
.team-right { background-color: #eee; }
.division-label { font-size: 0.75em; font-weight: bold; color: #333; margin-top: 2px; line-height: 1.2em; }

@media print {
    body { background: white; padding: 0; margin: 0; }
    .map-grid { gap: 0; }
    .map-column { page-break-inside: avoid; }
    button, hr { display: none; }
    .match-overlay { box-shadow: none; border: 1px solid #000; }
    .field-map { max-width: 100%; }
}
""")
f.write("</style></head><body>\n")



    f.write("<div class='map-grid'>\n")

    for block in sorted(games_by_block.keys(), key=time_sort_key):
        f.write(f"<div class='map-column'><h2>{block}</h2>\n")
        f.write(f"<div class='map-container'><img src='{image_path}' class='field-map'>\n")

        for matchup in games_by_block[block]:
            field = matchup["field"]
            pos = field_positions.get(field)
            if not pos:
                print(f"⚠️ Skipping {field} — no coordinates defined")
                continue

            # Base height logic
            is_full = matchup["division"] in full_block_divisions

            # Default height
            height = f"{pos['height']}%" if is_full else f"{pos['height'] * 0.6:.1f}%"

            # ⬇️ Shorten white box for Field 3 if not full-block
            if field == "Field 3" and not is_full:
                height = f"{pos['height'] * 0.45:.1f}%"
    

            # ⬆️ Adjust height ONLY for 11:00 AM matchups on Field 4A and 4B
            if matchup["time"] == "11:00 AM" and field in {"Field 4A", "Field 4B"}:
                height = f"{pos['height'] * 0.75:.1f}%"

            left = f"{pos['x']}%"
            top = f"{pos['y']}%"
            width = f"{pos['width']}%"
            rotation = pos.get("rotate", 0)
            transform = f"rotate({rotation}deg)" if rotation else "none"
            
            # Shrink font size for 11:00 AM matchups on tight fields
            shrink_font = matchup["time"] == "11:00 AM" and field in {"Field 1A", "Field 1B", "Field 2A", "Field 2B"}
            font_size = "font-size:0.55em;" if shrink_font else ""



            f.write(f"<div class='match-overlay' style='left:{left}; top:{top}; width:{width}; height:{height}; transform:{transform};'>\n")

            # Layout logic
            enlarged = field in enlarged_blocks_fields and matchup["division"] in enlarged_blocks_divisions
            is_diagonal = matchup["time"] == "11:30 AM"
            left_class = "team-left diagonal-text" if is_diagonal else "team-left"
            right_class = "team-right diagonal-text" if is_diagonal else "team-right"

            # Shrink font size for 11:00 AM matchups on tight fields
            shrink_font = matchup["time"] == "11:00 AM" and field in {"Field 1A", "Field 1B", "Field 2A", "Field 2B"}
            font_size = "font-size:0.55em;" if shrink_font else ""

            if field in side_by_side_fields:
                block_height = "80%" if enlarged else "66%"
                f.write(f"<div style='display:flex; flex-direction:row; height:{block_height};'>\n")
                f.write(f"<div class='{left_class}' style='flex:1; {font_size} background-color:{color_map.get(matchup['color1'], '#ccc')}'>{matchup['team1']}</div>\n")
                f.write(f"<div class='{right_class}' style='flex:1; {font_size} background-color:{color_map.get(matchup['color2'], '#ccc')}'>{matchup['team2']}</div>\n")
                f.write("</div>\n")
            else:
                block_style = "padding:10px 2px;" if enlarged else "padding:6px 2px;"
                f.write(f"<div class='{left_class}' style='{block_style} {font_size} background-color:{color_map.get(matchup['color1'], '#ccc')}'>{matchup['team1']}</div>\n")
                f.write(f"<div class='{right_class}' style='{block_style} {font_size} background-color:{color_map.get(matchup['color2'], '#ccc')}'>{matchup['team2']}</div>\n")

            f.write(f"<div class='division-label'>{matchup['division']}</div>\n")
            
            f.write("</div>\n")
    
        f.write("</div>\n")
        f.write("</div>\n")

    f.write("</div>\n")
    f.write("</div></body></html>\n")

print(f"✅ Overlay saved to: {output_html}")
webbrowser.open(output_html)
