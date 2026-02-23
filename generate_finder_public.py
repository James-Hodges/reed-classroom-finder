"""
Generates index.html — a PUBLIC version of the classroom finder
that strips course names, titles, and instructor names.
Only location, day, and time data is kept.
Safe to host on GitHub Pages without leaking restricted schedule info.
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

HTML_FILE = Path(__file__).parent / "Schedule of Classes - Reed College.html"
OUT_FILE  = Path(__file__).parent / "index.html"

# ── 1. Parse schedule ─────────────────────────────────────────────────────────

DAY_MAP = {
    "M": "Mon", "Tu": "Tue", "W": "Wed", "Th": "Thu",
    "F": "Fri",  "Sa": "Sat", "Su": "Sun",
}

def parse_time(t):
    """'13:40' -> 13*60+40"""
    h, m = map(int, t.split(":"))
    return h * 60 + m

with open(HTML_FILE, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

table = soup.find("table", id="class_schedule_202603")
if not table:
    raise RuntimeError("Could not find schedule table.")

headers = [th.get_text(strip=True) for th in table.thead.find_all("th")]

# column indices
col = {h: i for i, h in enumerate(headers)}

records = []

for tr in table.tbody.find_all("tr"):
    cells = [td.get_text(separator="\n").strip() for td in tr.find_all("td")]
    if len(cells) < max(col.values()) + 1:
        continue

    days_raw = cells[col.get("Days", 6)]
    time_raw = cells[col.get("Time", 7)]
    loc_raw  = cells[col.get("Location", 8)]

    # Split multi-component rows (labs with two meeting times) on newline
    day_parts  = [d.strip() for d in days_raw.split("\n") if d.strip()]
    time_parts = [t.strip() for t in time_raw.split("\n") if t.strip()]
    loc_parts  = [l.strip() for l in loc_raw.split("\n") if l.strip()]

    n = max(len(day_parts), len(time_parts), len(loc_parts))
    for i in range(n):
        dp  = day_parts[i]  if i < len(day_parts)  else day_parts[-1]  if day_parts  else ""
        tp  = time_parts[i] if i < len(time_parts) else time_parts[-1] if time_parts else ""
        lp  = loc_parts[i]  if i < len(loc_parts)  else loc_parts[-1]  if loc_parts  else ""

        if not lp or lp.upper() in ("", "TBA", "ONLINE"):
            continue

        # parse days  e.g. "MWF" or "TuTh"
        day_tokens = re.findall(r"Tu|Th|Sa|Su|M|W|F", dp)
        if not day_tokens:
            continue

        # parse time  e.g. "10:00-10:50" or "09:00-10:20"
        m = re.match(r"(\d+:\d+)\s*[-–]\s*(\d+:\d+)", tp)
        if not m:
            continue
        start_str, end_str = m.group(1), m.group(2)
        start = parse_time(start_str)
        end   = parse_time(end_str)

        for tok in day_tokens:
            day = DAY_MAP.get(tok)
            if day:
                # PUBLIC: only keep location + time, no course/title/instructor
                records.append({
                    "location":   lp,
                    "day":        day,
                    "start":      start,
                    "end":        end,
                    "start_str":  start_str,
                    "end_str":    end_str,
                })

# Filter out ONLINE / TBA
records = [r for r in records if r["location"].upper() not in ("ONLINE", "TBA")]

print(f"Parsed {len(records)} schedule entries across "
      f"{len({r['location'] for r in records})} locations.")

# ── 2. Build buildings list for checkboxes ────────────────────────────────────

locations = sorted({r["location"] for r in records})

def building(loc):
    return loc.split()[0] if loc else ""

buildings = sorted({building(l) for l in locations})

# ── 3. Render HTML ────────────────────────────────────────────────────────────

data_json = json.dumps(records, ensure_ascii=False)

checkbox_html = "\n".join(
    f'          <label class="bldg-option">'
    f'<input type="checkbox" value="{b}"> {b}</label>'
    for b in buildings
)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reed Classroom Finder — Spring 2026</title>
<style>
:root {{
  --red:   #8b0000;
  --red2:  #a00000;
  --light: #fdf6f6;
  --border:#e0d0d0;
  --card-shadow: 0 2px 6px rgba(0,0,0,.08);
}}
*, *::before, *::after {{ box-sizing: border-box; margin:0; padding:0; }}
body {{ font-family: "Segoe UI", system-ui, sans-serif; background:#f4f4f4; color:#222; }}

/* ── header ── */
header {{
  background: var(--red);
  color: #fff;
  padding: 1.2rem 1.5rem .9rem;
}}
header h1 {{ font-size: 1.5rem; font-weight: 700; letter-spacing:.02em; }}
header p  {{ font-size: .85rem; opacity:.8; margin-top:.2rem; }}

/* ── filter bar ── */
#filters {{
  background: #fff;
  border-bottom: 2px solid var(--red);
  padding: .75rem 1.2rem;
  display: flex;
  flex-wrap: wrap;
  gap: .6rem;
  align-items: flex-end;
}}
.filter-group {{ display:flex; flex-direction:column; gap:.3rem; }}
.filter-group label {{ font-size:.72rem; font-weight:600; color:#555; text-transform:uppercase; letter-spacing:.05em; }}
.filter-group select,
.filter-group input[type=time],
.filter-group input[type=number] {{
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .42rem .6rem;
  font-size: .9rem;
  background:#fff;
  color:#222;
  height: 36px;
}}
.filter-group select:focus,
.filter-group input:focus {{ outline:2px solid var(--red); }}

/* ── building picker ── */
.bldg-picker {{ position: relative; display:flex; flex-direction:column; gap:.3rem; }}
.bldg-picker label {{ font-size:.72rem; font-weight:600; color:#555; text-transform:uppercase; letter-spacing:.05em; }}
#bldg-toggle {{
  height: 36px;
  padding: 0 .7rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: .9rem;
  color: #222;
  display: flex;
  align-items: center;
  gap: .3rem;
  white-space: nowrap;
  min-width: 150px;
  user-select: none;
}}
#bldg-toggle.active {{ border-color: var(--red); color: var(--red); font-weight:600; }}
#bldg-toggle:hover {{ background: var(--light); }}

#bldg-dropdown {{
  display: none;
  position: fixed;
  z-index: 9999;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0,0,0,.15);
  padding: .5rem 0;
  max-height: 320px;
  overflow-y: auto;
  min-width: 160px;
}}
#bldg-dropdown.open {{ display:block; }}

.bldg-option {{
  display: flex;
  align-items: center;
  gap: .5rem;
  padding: .35rem .8rem;
  font-size: .88rem;
  cursor: pointer;
}}
.bldg-option:hover {{ background: var(--light); }}
.bldg-option input {{ accent-color: var(--red); width:14px; height:14px; cursor:pointer; }}

#bldg-clear {{
  display:block;
  width:100%;
  padding: .35rem .8rem;
  border:none;
  border-top:1px solid var(--border);
  background:none;
  font-size:.8rem;
  color: var(--red);
  cursor:pointer;
  text-align:left;
  margin-top:.3rem;
}}
#bldg-clear:hover {{ background: var(--light); }}

/* ── action buttons ── */
.btn {{
  height: 36px;
  padding: 0 1.1rem;
  border-radius: 6px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  align-self: flex-end;
}}
.btn-primary {{ background: var(--red); color:#fff; }}
.btn-primary:hover {{ background: var(--red2); }}
.btn-secondary {{ background: #eee; color:#444; border: 1px solid #ccc; }}
.btn-secondary:hover {{ background: #e0e0e0; }}
.btn-now {{
  height:36px; padding:0 .8rem; border-radius:6px; font-size:.82rem;
  font-weight:600; cursor:pointer; border:1px solid var(--border);
  background:#fff; color:var(--red); align-self:flex-end;
}}
.btn-now:hover {{ background: var(--light); }}

/* ── summary bar ── */
#summary {{
  padding: .6rem 1.2rem;
  font-size: .88rem;
  color: #555;
  background: #fff;
  border-bottom: 1px solid var(--border);
  min-height: 2rem;
}}

/* ── results grid ── */
#results {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  padding: 1rem 1.2rem;
  max-width: 1400px;
  margin: 0 auto;
}}

/* ── card ── */
.card {{
  background: #fff;
  border-radius: 10px;
  box-shadow: var(--card-shadow);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}
.card-header {{
  background: var(--red);
  color: #fff;
  padding: .6rem .9rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.room-name  {{ font-weight:700; font-size:1rem; letter-spacing:.02em; }}
.free-badge {{ font-size:.78rem; background:rgba(255,255,255,.2); padding:.2rem .5rem; border-radius:12px; }}
.card-body  {{ padding:.75rem .9rem; display:flex; flex-direction:column; gap:.5rem; }}

.free-window {{
  background: #e8f5e9;
  border-left: 4px solid #4caf50;
  border-radius: 4px;
  padding: .4rem .6rem;
}}
.fw-time {{ font-weight:700; font-size:.95rem; color:#2e7d32; }}
.fw-dur  {{ font-size:.8rem; color:#555; }}

.next-class {{
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  border-radius: 4px;
  padding: .4rem .6rem;
}}
.nc-label {{ font-size:.78rem; color:#e65100; font-weight:600; }}

details {{ margin-top:.2rem; }}
summary {{
  font-size:.8rem; color: var(--red); cursor:pointer;
  padding:.2rem 0; list-style:none; display:flex; align-items:center; gap:.3rem;
}}
summary::-webkit-details-marker {{ display:none; }}
summary::before {{ content:"▸"; font-size:.7rem; transition:transform .15s; }}
details[open] summary::before {{ transform:rotate(90deg); }}

.sched-item {{
  display: flex;
  gap: .6rem;
  padding: .3rem 0;
  border-bottom: 1px solid #f0f0f0;
  font-size:.83rem;
}}
.sched-item:last-child {{ border-bottom:none; }}
.sched-time {{ min-width:110px; color:#555; font-variant-numeric: tabular-nums; }}
.sched-label {{ color:#888; }}

.no-results {{
  grid-column: 1/-1;
  text-align:center;
  padding:3rem;
  color:#888;
  font-size:1.1rem;
}}

@media(max-width:600px) {{
  #filters {{ flex-direction:column; }}
  #results {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<header>
  <h1>Reed Classroom Finder</h1>
  <p>Spring 2026 — find open classrooms right now</p>
</header>

<div id="filters">
  <div class="filter-group">
    <label for="sel-day">Day</label>
    <select id="sel-day">
      <option value="Mon">Monday</option>
      <option value="Tue">Tuesday</option>
      <option value="Wed">Wednesday</option>
      <option value="Thu">Thursday</option>
      <option value="Fri">Friday</option>
      <option value="Sat">Saturday</option>
      <option value="Sun">Sunday</option>
    </select>
  </div>

  <div class="filter-group">
    <label for="sel-time">Free from</label>
    <input type="time" id="sel-time" value="09:00">
  </div>

  <div class="filter-group" style="width:70px">
    <label for="sel-dur">Min free (min)</label>
    <input type="number" id="sel-dur" value="30" min="5" max="240" step="5">
  </div>

  <div class="bldg-picker">
    <label>Building</label>
    <button type="button" id="bldg-toggle">
      <span>All buildings </span><span id="bldg-caret">▾</span>
    </button>
    <div id="bldg-dropdown">
{checkbox_html}
      <button id="bldg-clear">✕ Clear selection</button>
    </div>
  </div>

  <button class="btn btn-now" id="now-btn">⏱ Now</button>
  <button class="btn btn-primary" id="apply-btn">Find Rooms</button>
  <button class="btn btn-secondary" id="reset-btn">Reset</button>
</div>

<div id="summary"></div>
<div id="results"></div>

<script>
const DATA = {data_json};

const DAY_LABEL = {{Mon:"Monday",Tue:"Tuesday",Wed:"Wednesday",Thu:"Thursday",Fri:"Friday",Sat:"Saturday",Sun:"Sunday"}};
const DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];

function fmtMin(m) {{
  const h = Math.floor(m / 60), mn = m % 60;
  const ampm = h >= 12 ? "pm" : "am";
  const hr = h > 12 ? h - 12 : (h === 0 ? 12 : h);
  return hr + ":" + String(mn).padStart(2, "0") + ampm;
}}

function fmtDur(m) {{
  if (m < 60) return m + " min";
  const h = Math.floor(m / 60), mn = m % 60;
  return mn ? h + "h " + mn + "m" : h + "h";
}}

function getCurrentDayTime() {{
  const now = new Date();
  const jsDay = now.getDay();
  const jsToReed = [6, 0, 1, 2, 3, 4, 5];
  const day = DAYS[jsToReed[jsDay]];
  const mins = now.getHours() * 60 + now.getMinutes();
  return {{ day: day, mins: mins }};
}}

function getSmartDefault() {{
  var dt = getCurrentDayTime();
  if (dt.mins >= 7 * 60 && dt.mins < 22 * 60) return dt;
  var dayIdx = DAYS.indexOf(dt.day);
  if (dt.mins >= 22 * 60) dayIdx = (dayIdx + 1) % 7;
  if (dayIdx >= 5) dayIdx = 0;
  return {{ day: DAYS[dayIdx], mins: 9 * 60 }};
}}

// Build index: location -> day -> sorted list of time blocks
const index = {{}};
for (var i = 0; i < DATA.length; i++) {{
  var r = DATA[i];
  if (!index[r.location]) index[r.location] = {{}};
  if (!index[r.location][r.day]) index[r.location][r.day] = [];
  index[r.location][r.day].push(r);
}}
var _locs = Object.keys(index);
for (var li = 0; li < _locs.length; li++) {{
  var _days = Object.keys(index[_locs[li]]);
  for (var di = 0; di < _days.length; di++) {{
    index[_locs[li]][_days[di]].sort(function(a, b) {{ return a.start - b.start; }});
  }}
}}

const ALL_ROOMS = Object.keys(index).sort();

var bldgToggle   = document.getElementById("bldg-toggle");
var bldgDropdown = document.getElementById("bldg-dropdown");
var bldgCaret    = document.getElementById("bldg-caret");

function findFreeWindows(loc, day, afterMin, minDur) {{
  var classes = (index[loc] && index[loc][day]) ? index[loc][day] : [];
  var DAY_START = 7 * 60, DAY_END = 24 * 60;
  var windows = [];
  var cursor = Math.max(afterMin, DAY_START);
  for (var ci = 0; ci < classes.length; ci++) {{
    var c = classes[ci];
    if (c.end <= cursor) continue;
    if (c.start > cursor) {{
      var end = Math.min(c.start, DAY_END);
      var dur = end - cursor;
      if (dur >= minDur) windows.push({{ start: cursor, end: end, dur: dur, nextClass: c }});
    }}
    if (c.end > cursor) cursor = c.end;
  }}
  if (cursor < DAY_END) {{
    var dur = DAY_END - cursor;
    if (dur >= minDur) windows.push({{ start: cursor, end: DAY_END, dur: dur, nextClass: null }});
  }}
  return windows;
}}

function getCheckedBuildings() {{
  var checked = bldgDropdown.querySelectorAll("input[type=checkbox]:checked");
  return Array.prototype.map.call(checked, function(el) {{ return el.value; }});
}}

function updateBldgLabel() {{
  var sel = getCheckedBuildings();
  var span = bldgToggle.querySelector("span");
  if (sel.length === 0) {{
    span.textContent = "All buildings ";
  }} else if (sel.length === 1) {{
    span.textContent = sel[0] + " ";
  }} else {{
    span.textContent = sel.length + " buildings ";
  }}
  bldgToggle.classList.toggle("active", sel.length > 0);
}}

function render() {{
  var day    = document.getElementById("sel-day").value;
  var timeV  = document.getElementById("sel-time").value;
  var minDur = parseInt(document.getElementById("sel-dur").value) || 30;
  var checkedBldgs = getCheckedBuildings();

  var parts = timeV.split(":");
  var afterMin = parseInt(parts[0]) * 60 + parseInt(parts[1]);
  if (isNaN(afterMin)) afterMin = 9 * 60;

  var rooms = ALL_ROOMS;
  if (checkedBldgs.length > 0) {{
    rooms = ALL_ROOMS.filter(function(r) {{
      return checkedBldgs.some(function(b) {{
        return r === b || r.indexOf(b + " ") === 0;
      }});
    }});
  }}

  var cards = [];
  for (var ri = 0; ri < rooms.length; ri++) {{
    var loc = rooms[ri];
    var wins = findFreeWindows(loc, day, afterMin, minDur);
    if (!wins.length) continue;
    var allClasses = (index[loc] && index[loc][day]) ? index[loc][day] : [];
    cards.push({{ loc: loc, wins: wins, allClasses: allClasses }});
  }}

  cards.sort(function(a, b) {{ return b.wins[0].dur - a.wins[0].dur; }});

  var sumEl = document.getElementById("summary");
  sumEl.innerHTML = cards.length
    ? "<strong>" + cards.length + "</strong> room" + (cards.length !== 1 ? "s" : "") +
      " free on <strong>" + DAY_LABEL[day] + "</strong> at <strong>" + fmtMin(afterMin) +
      "</strong> for at least <strong>" + fmtDur(minDur) + "</strong>"
    : "No rooms found matching your filters.";

  var el = document.getElementById("results");
  if (!cards.length) {{
    el.innerHTML = '<div class="no-results">\U0001f615 No free rooms match your filters.<br>Try a different time or shorter minimum duration.</div>';
    return;
  }}

  var html = "";
  for (var ci2 = 0; ci2 < cards.length; ci2++) {{
    var card = cards[ci2];
    var loc2 = card.loc;
    var wins2 = card.wins;
    var allClasses2 = card.allClasses;
    var w = wins2[0];

    var nextClassHTML = "";
    if (w.nextClass) {{
      nextClassHTML = '<div class="next-class">' +
        '<div class="nc-label">Next class starts at ' + fmtMin(w.nextClass.start) + '</div>' +
        '</div>';
    }} else {{
      nextClassHTML = '<div class="next-class" style="background:#f1f8e9;border-left-color:#8bc34a">' +
        '<div class="nc-label">Free for the rest of the day</div>' +
        '</div>';
    }}

    var moreWins = "";
    for (var wi = 1; wi < wins2.length; wi++) {{
      var w2 = wins2[wi];
      moreWins += '<div class="sched-item">' +
        '<span class="sched-time">' + fmtMin(w2.start) + " \u2013 " + fmtMin(w2.end) + '</span>' +
        '<span class="sched-label">Free \u00b7 ' + fmtDur(w2.dur) + '</span>' +
        '</div>';
    }}

    var schedHTML = "";
    for (var sci = 0; sci < allClasses2.length; sci++) {{
      var c2 = allClasses2[sci];
      schedHTML += '<div class="sched-item">' +
        '<span class="sched-time">' + c2.start_str + " \u2013 " + c2.end_str + '</span>' +
        '<span class="sched-label">Occupied</span>' +
        '</div>';
    }}

    html +=
      '<div class="card">' +
        '<div class="card-header">' +
          '<span class="room-name">' + loc2 + '</span>' +
          '<span class="free-badge">Free ' + fmtDur(w.dur) + '</span>' +
        '</div>' +
        '<div class="card-body">' +
          '<div class="free-window">' +
            '<div class="fw-time">' + fmtMin(w.start) + " \u2013 " + fmtMin(w.end) + '</div>' +
            '<div class="fw-dur">Available for ' + fmtDur(w.dur) + '</div>' +
          '</div>' +
          nextClassHTML +
          (moreWins ? '<details><summary>More free windows today</summary>' + moreWins + '</details>' : '') +
          (schedHTML ? '<details><summary>Room schedule for ' + DAY_LABEL[day] + '</summary>' + schedHTML + '</details>' : '') +
        '</div>' +
      '</div>';
  }}
  el.innerHTML = html;
}}

// ── Building picker ───────────────────────────────────────────────────────────
bldgToggle.addEventListener("click", function(e) {{
  e.stopPropagation();
  var isOpen = bldgDropdown.classList.contains("open");
  if (isOpen) {{
    bldgDropdown.classList.remove("open");
    bldgCaret.textContent = "\u25be";
  }} else {{
    var rect = bldgToggle.getBoundingClientRect();
    bldgDropdown.style.top   = (rect.bottom + window.scrollY + 4) + "px";
    bldgDropdown.style.left  = (rect.left + window.scrollX) + "px";
    bldgDropdown.style.width = Math.max(rect.width, 200) + "px";
    bldgDropdown.classList.add("open");
    bldgCaret.textContent = "\u25b4";
  }}
}});

bldgDropdown.addEventListener("change", updateBldgLabel);

document.getElementById("bldg-clear").addEventListener("click", function() {{
  var boxes = bldgDropdown.querySelectorAll("input[type=checkbox]");
  for (var i = 0; i < boxes.length; i++) boxes[i].checked = false;
  updateBldgLabel();
}});

document.addEventListener("click", function(e) {{
  if (!bldgToggle.closest(".bldg-picker").contains(e.target)) {{
    bldgDropdown.classList.remove("open");
    bldgCaret.textContent = "\u25be";
  }}
}});

// ── Now button ───────────────────────────────────────────────────────────────
document.getElementById("now-btn").addEventListener("click", function() {{
  var dt = getCurrentDayTime();
  document.getElementById("sel-day").value = dt.day;
  var hh = String(Math.floor(dt.mins / 60)).padStart(2, "0");
  var mm = String(dt.mins % 60).padStart(2, "0");
  document.getElementById("sel-time").value = hh + ":" + mm;
  render();
}});

// ── Find Rooms / Reset ────────────────────────────────────────────────────────
document.getElementById("apply-btn").addEventListener("click", render);

document.getElementById("reset-btn").addEventListener("click", function() {{
  var dt = getSmartDefault();
  document.getElementById("sel-day").value = dt.day;
  var hh = String(Math.floor(dt.mins / 60)).padStart(2, "0");
  var mm = String(dt.mins % 60).padStart(2, "0");
  document.getElementById("sel-time").value = hh + ":" + mm;
  document.getElementById("sel-dur").value = "30";
  var boxes = bldgDropdown.querySelectorAll("input[type=checkbox]");
  for (var i = 0; i < boxes.length; i++) boxes[i].checked = false;
  updateBldgLabel();
  render();
}});

// ── Auto-init ─────────────────────────────────────────────────────────────────
(function init() {{
  var dt = getSmartDefault();
  document.getElementById("sel-day").value = dt.day;
  var hh = String(Math.floor(dt.mins / 60)).padStart(2, "0");
  var mm = String(dt.mins % 60).padStart(2, "0");
  document.getElementById("sel-time").value = hh + ":" + mm;
  render();
}})();
</script>
</body>
</html>"""

OUT_FILE.write_text(html, encoding="utf-8")
print(f"Written: {OUT_FILE}  ({OUT_FILE.stat().st_size:,} bytes)")
