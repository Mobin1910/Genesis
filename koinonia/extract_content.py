"""Build the Q4 2026 content model from the supplied source files.

Values are copied verbatim from the workbook / DOCX. The only transformations
are presentational (e.g. formatting an Excel time cell as "08:30 AM").
Blank cells stay blank (empty string).
"""
import datetime
import json
import pathlib

import docx
import openpyxl

HERE = pathlib.Path(__file__).parent
SRC = HERE / "sources"
OUT = HERE / "build" / "content.json"

LECT_COLS = ["day", "month", "date", "language", "time", "theme", "firstLesson",
             "secondLesson", "epistle", "worshipAssistance", "kissOfPeace",
             "offertory", "prayer"]


def cell(v):
    if v is None:
        return ""
    if isinstance(v, datetime.time):
        return v.strftime("%I:%M %p")
    return str(v)


def lectionary(wb):
    ws = wb["Lectionary OND"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    assert header[0] == "DAY" and header[-1] == "PRAYER", header
    out = []
    for r in rows[1:]:
        if all(v is None for v in r):
            continue
        out.append({k: cell(v) for k, v in zip(LECT_COLS, r)})
    return out


def prayer_meetings(wb):
    ws = wb["Area Wise Prayer Meeting"]
    # Merged date cells: the date lives in the top-left cell of the range.
    merged_owner = {}
    for rng in ws.merged_cells.ranges:
        for row in range(rng.min_row, rng.max_row + 1):
            merged_owner[(row, rng.min_col)] = (rng.min_row, rng.max_row)
    out = []
    for row in range(2, ws.max_row + 1):
        vals = [ws.cell(row, c).value for c in (1, 2, 3)]
        if all(v is None for v in vals):
            continue
        span = merged_owner.get((row, 1))
        date_row = span[0] if span else row
        out.append({
            "date": cell(ws.cell(date_row, 1).value),
            "dateGroupStart": date_row == row,
            "dateGroupSize": (span[1] - span[0] + 1) if span else 1,
            "groupAndTime": cell(vals[1]),
            "memberDetails": cell(vals[2]),
        })
    return out


def vicar_message():
    d = docx.Document(SRC / "Vicar's Desk.docx")
    paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]
    # Last three paragraphs are the closing, sign-off name and date.
    *body, closing, name, date = paras
    return {"paragraphs": body, "closing": closing, "signOff": name, "date": date}


def main():
    wb = openpyxl.load_workbook(SRC / "Lectionary & Prayer Oct Nov and Dec 2026.xlsx")
    content = {
        "quarter": "October - December",
        "year": 2026,
        "volume": 63,
        "vicarMessage": vicar_message(),
        "lectionary": lectionary(wb),
        "prayerMeetings": prayer_meetings(wb),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(content, ensure_ascii=False, indent=2))
    print(f"lectionary={len(content['lectionary'])} prayerMeetings={len(content['prayerMeetings'])}")


if __name__ == "__main__":
    main()
