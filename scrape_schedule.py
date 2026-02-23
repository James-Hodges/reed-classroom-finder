"""
Scrapes course schedule data from the saved Reed College HTML file
and exports it to a CSV.
"""

import csv
from pathlib import Path
from bs4 import BeautifulSoup

HTML_FILE = Path(__file__).parent / "Schedule of Classes - Reed College.html"
OUTPUT_FILE = Path(__file__).parent / "reed_spring_2026_schedule.csv"

with open(HTML_FILE, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

table = soup.find("table", id="class_schedule_202603")
if not table:
    raise RuntimeError("Could not find the schedule table in the HTML file.")

# --- headers ---
headers = [th.get_text(strip=True) for th in table.thead.find_all("th")]

# --- rows ---
rows = []
for tr in table.tbody.find_all("tr"):
    cells = tr.find_all("td")
    row = []
    for td in cells:
        # Some cells contain <br>-separated multi-line values (e.g. labs with
        # two meeting times).  Join them with " | " so nothing is lost.
        parts = [s.strip() for s in td.get_text(separator="\n").splitlines() if s.strip()]
        row.append(" | ".join(parts) if parts else "")
    rows.append(row)

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)

print(f"Done!  Wrote {len(rows)} courses to:\n  {OUTPUT_FILE}")
print(f"\nColumns: {headers}")
