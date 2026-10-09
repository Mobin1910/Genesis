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
_CORR = json.loads(CORRECTIONS_FILE.read_text()) if CORRECTIONS_FILE.exists() else {}
APPROVED_CORRECTIONS = _CORR.get("text", {})
# {"<date> | <GROUP>": "<time>"} - meeting times the church corrected.
PRAYER_TIME_FIXES = _CORR.get("prayerMeetingTime", {})
NEWSLETTER_DOCX = SRC / "Newsletter Oct- Dec 2026.docx"

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
APPLIED_TIMES = set()


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


# ---------------------------------------------------------------- newsletter docx
# Prayer-group codes used in the New Members table -> names used elsewhere in
# the newsletter (Prayer Groups directory).
PRAYER_GROUP_NAMES = {"CAR": "Carmelaram", "KOR": "Koramangala", "BLR": "Bellandur",
                      "ECITY": "Electronic City", "HSR": "HSR", "BTM": "BTM"}
# Three-letter capitalised words that are ordinary words, not codes like BSR/SJR.
_SHORT_WORDS = {"NEO", "SRI", "ANN", "OFF", "THE", "AND"}


def _tidy_case(text, names=False):
    """Fix capitals-lock / stray capitals while keeping codes (BSR, SJR), initials and unit numbers."""
    def word(m):
        w = m.group(0)
        if w.islower() or (w[0].isupper() and w[1:].islower()):
            return w
        if len(w) >= 4 or (names and len(w) >= 2) or w.upper() in _SHORT_WORDS:
            return w.capitalize()
        return w
    t = re.sub(r"(?<![A-Za-z0-9])[A-Za-z]{2,}(?![A-Za-z])", word, text)
    t = re.sub(r"(\d)(ST|ND|RD|TH)\b", lambda m: m.group(1) + m.group(2).lower(), t)  # 6TH -> 6th
    if names:
        t = re.sub(r"\b([a-z])\b", lambda m: m.group(1).upper(), t)                # "Johnson k" -> "K"
    t = re.sub(r"\bNO(?=[.:])", "No", t)                                         # "Flat NO." / "H.NO:"
    t = re.sub(r"[^\S\n]+", " ", t)                                                # incl. Word's no-break spaces
    t = re.sub(r" ,", ",", t)
    t = "\n".join(line.strip() for line in t.split("\n")).strip()
    t = re.sub(r"(?<=[^\s(])\((?=[A-Z]\))", " (", t)                              # "Rajan(W)"
    return t


def _cell_lines(c):
    return "\n".join(p.text for p in c.paragraphs).strip()


def new_members(d):
    table = next(t for t in d.tables if t.rows[0].cells[1].text.strip() == "HOF")
    head = [c.text.strip() for c in table.rows[0].cells]
    assert head == ["Prayer Group", "HOF", "ER", "Home Address", "Mobile", "Family Members"], head
    out = []
    for row in table.rows[1:]:
        grp, hof, er, addr, mobile, fam = (_cell_lines(c) for c in row.cells)
        raw = {"prayerGroup": grp, "hof": hof, "er": er, "address": addr, "family": fam}
        rec = {
            "prayerGroup": PRAYER_GROUP_NAMES.get(grp.strip().upper(), grp.strip()),
            "hof": _tidy_case(hof, names=True),
            "er": er.strip(),
            # Mobile numbers are not printed (the template has no mobile column);
            # one address cell repeats the mobile number as a line - drop it.
            "address": _tidy_case("\n".join(l for l in addr.split("\n") if l.strip() != mobile.strip())),
            "mobile": mobile.strip(),
        }
        family = [_tidy_case(l, names=True) for l in fam.split("\n") if l.strip()]
        # Template lists the head of family only in the HOF column.
        if family and re.sub(r"\W", "", family[0]).lower() == re.sub(r"\W", "", rec["hof"]).lower():
            family = family[1:]
        rec["family"] = "\n".join(family)
        for k in ("prayerGroup", "hof", "address", "family"):
            if rec[k] != raw[k]:
                STYLE_LOG.append(f"New member ER {rec['er']} | {k}\n  was: {raw[k]!r}\n  now: {rec[k]!r}")
        out.append(rec)
    return out


# Wording fixes in the events list (house style / typos).
EVENT_FIXES = {"Bibel": "Bible", "Young Womens": "Young Women's", "Chief Celebrant :": "Chief Celebrant:"}
_EVT_TIME = re.compile(r"\s*@\s*(\d{1,2}:\d{2})\s*([ap]m)\b\.?", re.I)


def events(d):
    paras = [p for p in d.paragraphs]
    start = next(i for i, p in enumerate(paras) if p.text.strip().upper().startswith("MAJOR UPCOMING EVENTS"))
    title = paras[start].text.strip()
    months, current = [], None
    for p in paras[start + 1:]:
        text = p.text.strip()
        if not text:
            continue
        if p.style.name != "List Paragraph":
            current = {"month": text, "items": []}
            months.append(current)
            continue
        m = re.match(r"^(.*?)\s*(?:–|:)\s+(.*)$", text)
        date, what = (m.group(1), m.group(2)) if m else (text, "")
        raw = text
        times = _EVT_TIME.findall(date) + _EVT_TIME.findall(what)
        date, what = _EVT_TIME.sub("", date).strip(), _EVT_TIME.sub(".", what).strip(" .")
        what = re.sub(r"\.\s*\.", ".", what)
        date = re.sub(r"^(\d{1,2})(?=\s+[A-Z])", lambda m: m.group(1) + {1: "st", 2: "nd", 3: "rd"}.get(
            int(m.group(1)) % 10 if int(m.group(1)) not in (11, 12, 13) else 0, "th"), date)
        date = re.sub(r"\s+,", ",", date)
        if current["month"] not in date:              # "10th, 11th, ... 19th" under December
            date = f"{date} {current['month']}"
        if times:
            hh, ap = times[0]
            date += f" @ {hh.zfill(5)} {ap.upper()}"
        for a, b in EVENT_FIXES.items():
            what = what.replace(a, b)
        item = {"date": date, "event": what}
        STYLE_LOG.append(f"Event | {raw!r}\n  now: {date!r} | {what!r}")
        current["items"].append(item)
    return {"title": title, "months": months}


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
    news = docx.Document(NEWSLETTER_DOCX)
    content["newMembers"] = new_members(news)
    content["events"] = events(news)
    for it in content["lectionary"]:
        where = f"Lectionary {it['date']} {it['month']}"
        for key in ("firstLesson", "secondLesson", "worshipAssistance", "kissOfPeace", "offertory", "prayer"):
            styled(it, key, "people", where)
        styled(it, "theme", "theme", where)
    for it in content["prayerMeetings"]:
        where = f"Prayer meeting {it['date']}"
        styled(it, "groupAndTime", "group", where)
        key = f"{it['date']} | {it['groupAndTime'].split(' (')[0].upper()}"
        if key in PRAYER_TIME_FIXES:
            before = it["groupAndTime"]
            it["groupAndTime"] = re.sub(r"\(.*\)", f"({PRAYER_TIME_FIXES[key]})", before)
            STYLE_LOG.append(f"{where} | groupAndTime (church correction)\n  was: {before!r}\n  now: {it['groupAndTime']!r}")
            APPLIED_TIMES.add(key)
        styled(it, "memberDetails", "people", where)
    (OUT.parent / "style_changes.txt").parent.mkdir(exist_ok=True)
    (OUT.parent / "style_changes.txt").write_text("\n".join(STYLE_LOG) + "\n")
    print(f"house-style changes: {len(STYLE_LOG)} fields")

    unused = (set(APPROVED_CORRECTIONS) - APPLIED) | (set(PRAYER_TIME_FIXES) - APPLIED_TIMES)
    assert not unused, f"approved corrections not found in source: {unused}"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(content, ensure_ascii=False, indent=2))
    print(f"lectionary={len(content['lectionary'])} prayerMeetings={len(content['prayerMeetings'])} "
          f"newMembers={len(content['newMembers'])} "
          f"events={sum(len(m['items']) for m in content['events']['months'])}")


if __name__ == "__main__":
    main()
