"""Build the Q4 2026 content model from the supplied source files.

Values are copied verbatim from the workbook / DOCX. The only transformations
are presentational (e.g. formatting an Excel time cell as "08:30 AM").
Blank cells stay blank (empty string).
"""
import datetime
import json
import re
import pathlib

import docx
import openpyxl

HERE = pathlib.Path(__file__).parent
SRC = HERE / "sources"
OUT = HERE / "build" / "content.json"

# Corrections to the workbook approved by the church, kept with the (private)
# sources as {"wrong text": "right text"}. Applied as exact substring
# replacements; anything not listed stays verbatim.
CORRECTIONS_FILE = SRC / "approved_corrections.json"
APPROVED_CORRECTIONS = json.loads(CORRECTIONS_FILE.read_text()) if CORRECTIONS_FILE.exists() else {}

# House style applied to names, ER numbers and meeting times (user request:
# "make the ER numbers consistent with three digits" and similar fixes).
# Every change is logged to build/style_changes.txt for review.
ER_RE = re.compile(r"\(\s*E[Rr]\s*(?:No\.?)?\s*(\d+)\s*\)")
TIME_RE = re.compile(r"\((\d{1,2}):(\d{2})\s*([AaPp][Mm])\)")
TITLE_RE = re.compile(r"\b(Mr|Mrs|Ms|Dr)\.?[ \t]*(?=[A-Z])")


def _uncap(segment):
    """Title-case a segment typed in capitals (keeps ER, initials and codes like M-111)."""
    letters = [ch for ch in segment if ch.isalpha()]
    if not letters or sum(ch.isupper() for ch in letters) / len(letters) < 0.7:
        return segment
    return re.sub(r"\b[A-Z]{3,}\b", lambda m: m.group(0) if m.group(0) == "ER" else m.group(0).capitalize(),
                  segment)


def house_style(text, kind):
    """kind: 'people' (names / ER numbers), 'theme', 'group' (prayer group + time)."""
    t = ER_RE.sub(lambda m: f"(ER {int(m.group(1)):03d})", text)
    t = re.sub(r"(?<=[^\s(\[])\(", " (", t)                 # space before "("
    t = re.sub(r"[ \t]{2,}", " ", t)                         # collapse repeated spaces
    if kind == "people":
        t = TITLE_RE.sub(lambda m: m.group(1) + ". ", t)       # Mr/Mrs/Dr -> "Mr. "
        t = re.sub(r"(&|\band) family\b", r"\1 Family", t)
        t = "\n".join(" - ".join(_uncap(seg) for seg in line.split(" - ")) for line in t.split("\n"))
    if kind == "group":
        t = TIME_RE.sub(lambda m: f"({int(m.group(1))}:{m.group(2)}{m.group(3).upper()})", t)
    return t


STYLE_LOG = []


def styled(rec, key, kind, where):
    before = rec[key]
    rec[key] = house_style(before, kind)
    if rec[key] != before:
        STYLE_LOG.append(f"{where} | {key}\n  was: {before!r}\n  now: {rec[key]!r}")


LECT_COLS = ["day", "month", "date", "language", "time", "theme", "firstLesson",
             "secondLesson", "epistle", "worshipAssistance", "kissOfPeace",
             "offertory", "prayer"]


def cell(v):
    if v is None:
        return ""
    if isinstance(v, datetime.time):
        return v.strftime("%I:%M %p")
    v = str(v)
    for wrong, right in APPROVED_CORRECTIONS.items():
        if wrong in v:
            v = v.replace(wrong, right)
            APPLIED.add(wrong)
    return v


APPLIED = set()


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
    for it in content["lectionary"]:
        where = f"Lectionary {it['date']} {it['month']}"
        for key in ("firstLesson", "secondLesson", "worshipAssistance", "kissOfPeace", "offertory", "prayer"):
            styled(it, key, "people", where)
        styled(it, "theme", "theme", where)
    for it in content["prayerMeetings"]:
        where = f"Prayer meeting {it['date']}"
        styled(it, "groupAndTime", "group", where)
        styled(it, "memberDetails", "people", where)
    (OUT.parent / "style_changes.txt").parent.mkdir(exist_ok=True)
    (OUT.parent / "style_changes.txt").write_text("\n".join(STYLE_LOG) + "\n")
    print(f"house-style changes: {len(STYLE_LOG)} fields")

    unused = set(APPROVED_CORRECTIONS) - APPLIED
    assert not unused, f"approved corrections not found in source: {unused}"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(content, ensure_ascii=False, indent=2))
    print(f"lectionary={len(content['lectionary'])} prayerMeetings={len(content['prayerMeetings'])}")


if __name__ == "__main__":
    main()
