"""Pre-export checks for the Q4 2026 draft. Exits non-zero on any failure."""
import datetime
import hashlib
import json
import pathlib
import re
import sys

import pdfplumber
import pypdf

HERE = pathlib.Path(__file__).parent
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out" / "Stephania_Koinonia_Q4_2026_Draft.pdf"
TEMPLATE = HERE / "sources" / "St Stephens MTC BLR - Koinonia Apr-Jun-2026.pdf"
COVER = HERE / "sources" / "A4 - 3.pdf"
content = json.loads((HERE / "build" / "content.json").read_text())

failures = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)


def norm(s):
    return re.sub(r"\s+", "", s)


def latin_runs(s):
    """Non-Malayalam fragments of a value (PDF text of shaped Malayalam is not comparable)."""
    return [r for r in (norm(x) for x in re.split(r"[ഀ-ൿ‌‍]+", s)) if r]


pdf = pdfplumber.open(OUT)
pages = [p.extract_text() or "" for p in pdf.pages]
flat = [norm(t) for t in pages]
body = "".join(flat[1:])


def column(x0, x1, page_range):
    return "".join(norm(pdf.pages[i].crop((x0, 0, x1, 780)).extract_text() or "") for i in page_range)


lect_pages = [i for i, t in enumerate(pages) if "LESSON" in t]
pm_pages = [i for i, t in enumerate(pages) if "MEMBER DETAILS" in t]
lect_values = column(192.5, 560, lect_pages)
pm_date, pm_group, pm_details = (column(36, 149.5, pm_pages), column(149.8, 270, pm_pages),
                                 column(270.3, 560, pm_pages))
LESSON_RE = re.compile(r"^((?:[1-3])?[A-Z][a-z]+ \d+:\d+(?:-\d+(?::\d+)?)?)\s+(.+)$", re.S)


def pieces(key, value):
    """Source value split the way the layout presents it (lines / theme parts / lesson reader+ref)."""
    if key in ("firstLesson", "secondLesson") and LESSON_RE.match(value):
        return list(LESSON_RE.match(value).groups())
    parts = value.split(";") if key == "theme" else [value]
    return [line for p in parts for line in p.split("\n")]

# --- structure
reader = pypdf.PdfReader(OUT)
cover = pypdf.PdfReader(COVER).pages[0]
check(hashlib.sha256(reader.pages[0].get_contents().get_data()).hexdigest() ==
      hashlib.sha256(cover.get_contents().get_data()).hexdigest(), "page 1 is the supplied cover, unchanged")
check("Vol.63" in flat[0] and "Oct-DecQuarter,2026" in flat[0], "cover shows Vol. 63 / Oct - Dec Quarter, 2026")
for p in reader.pages:
    w, h = float(p.mediabox.width), float(p.mediabox.height)
    if abs(w - 595.3) > 1 or abs(h - 841.9) > 1:
        check(False, f"A4 page size ({w}x{h})")
        break
else:
    check(True, f"all {len(reader.pages)} pages are A4")

# --- page numbers
for i, t in enumerate(pages[1:], start=2):
    nums = re.findall(r"PAGE\s*(\d+)", t)
    check(nums == [str(i)], f"page {i} footer reads PAGE {i} (found {nums})")

# --- vicar's message
v = content["vicarMessage"]
vt = flat[1]
for i, para in enumerate(v["paragraphs"] + [v["closing"], v["date"]]):
    check(norm(para) in vt, f"vicar paragraph {i + 1} verbatim on page 2")
check("RenjithAchen" in vt, "vicar sign-off Renjith Achen")

# --- lectionary
check(len(content["lectionary"]) == 15, "15 lectionary records in content model")
for it in content["lectionary"]:
    label = f"{it['date']} {it['month']}"
    missing = [k for k in ("theme", "firstLesson", "secondLesson", "epistle", "worshipAssistance",
                           "kissOfPeace", "offertory", "prayer", "language")
               for piece in pieces(k, it[k]) for run in latin_runs(piece) if run not in lect_values]
    check(not missing, f"lectionary {label}: all field text present {missing or ''}")
    day = datetime.date(2026, datetime.datetime.strptime(it["month"], "%B").month,
                        int(it["date"][:-2])).strftime("%A").upper()
    hdr = norm(f"{day} {it['date'][:-2]}{it['date'][-2:].upper()} {it['month'].upper()} 2026 AT {it['time']}")
    check(norm(f"WORSHIPHoly Qurbana ({it['language']})") in body,
          f"lectionary {label}: WORSHIP row reads Holy Qurbana ({it['language']})")
    check(hdr in body, f"lectionary {label}: strip reads {day} ... AT {it['time']}")

# --- prayer meetings
check(len(content["prayerMeetings"]) == 12, "12 prayer meetings in content model")
for it in content["prayerMeetings"]:
    ok = norm(it["memberDetails"]) in pm_details and norm(it["groupAndTime"]) in pm_group
    check(ok, f"prayer meeting {it['date']} {it['groupAndTime']} present verbatim")
for d in {it["date"] for it in content["prayerMeetings"]}:
    check(norm(d) in pm_date, f"prayer meeting date {d} shown")

# --- house style: every ER reference in the tables reads "(ER 000)"
cols = lect_values + pm_details  # whitespace removed, so "(ER 056)" -> "(ER056)"
refs = re.findall(r"\(E[Rr][^)]*\)", cols)
odd_er = [r for r in refs if not re.fullmatch(r"\(ER\d{3}\)", r)]
check(len(refs) > 50 and not odd_er, f"all {len(refs)} ER numbers are three digits as (ER 000) {odd_er or ''}")

raw = json.dumps(content, ensure_ascii=False)
raw_refs = re.findall(r".?\(\s*E[Rr][^)]*\)", raw)
check(all(re.fullmatch(r" \(ER \d{3}\)", r) for r in raw_refs),
      f"ER numbers spaced as 'Name (ER 000)' in content {[r for r in raw_refs if not re.fullmatch(r' [(]ER [0-9]{3}[)]', r)] or ''}")

# --- new members (from the Oct-Dec newsletter DOCX)
nm_pages = [i for i, t in enumerate(pages) if "HOME ADDRESS" in t]
nm_text = "".join(flat[i] for i in nm_pages)
check(len(content["newMembers"]) == 14, "14 new member families in content model")
check(nm_pages and "WarmwelcometheNewMemberstotheSt.Stephen’sfamily" in flat[nm_pages[0]],
      "New Members bar + welcome line")
nm_hof = column(127.5, 211.5, nm_pages)
nm_addr = column(247, 424, nm_pages)
nm_fam = column(424.5, 560, nm_pages)
for it in content["newMembers"]:
    ok = (norm(it["hof"]) in nm_hof and it["er"] in nm_text and norm(it["address"]) in nm_addr
          and norm(it["family"]) in nm_fam)
    check(ok, f"new member ER {it['er']}: HOF, address and family present")
    check(it["mobile"] not in "".join(flat[1:-3]), f"new member ER {it['er']}: mobile number not printed")

# --- newborn babies (sent by the church in chat; Secretary's Desk sections not used this quarter)
check(len(content["newborns"]) == 2, "2 newborn announcements in content model")
nb_text = flat[nm_pages[0]] if nm_pages else ""
check("NEWBORNBABIES" in nb_text and "CongratulationstothejoyfuloccasionoftheNewborns" in nb_text,
      "Newborn Babies bar + congratulations line on the New Members page")
for it in content["newborns"]:
    line = norm(f"{it['parents'][0].upper()} and {it['parents'][1].upper()} (ER {it['er']}) {it['text']}")
    check(line in nb_text, f"newborn (ER {it['er']}) announcement printed in full")
check(nb_text.find("NEWBORNBABIES") < nb_text.find("NEWMEMBERS"), "Newborn Babies comes before New Members")

# --- major upcoming events
ev_pages = [i for i, t in enumerate(pages) if "MAJOR UPCOMING EVENTS" in t]
ev_dates, ev_events = column(36, 227, ev_pages), column(227.5, 560, ev_pages)
n_ev = sum(len(m["items"]) for m in content["events"]["months"])
check(n_ev == 13, f"13 events in content model ({n_ev})")
for m in content["events"]["months"]:
    for it in m["items"]:
        check(norm(it["date"]) in ev_dates and norm(it["event"]) in ev_events,
              f"event {it['date']}: {it['event'][:40]}")

# --- church corrections to prayer meeting times
pm = {(it["date"], it["groupAndTime"].split(" (")[0]): it["groupAndTime"] for it in content["prayerMeetings"]}
check(pm[("4th October 2026", "KORAMANGALA")] == "KORAMANGALA (4:30PM)", "4 Oct Koramangala at 4:30PM")
check(pm[("11th October 2026", "ECITY")] == "ECITY (6:00PM)", "11 Oct ECITY at 6:00PM")
check(pm[("1st November 2026", "ECITY")] == "ECITY (6:30PM)", "1 Nov ECITY unchanged at 6:30PM")
check(norm("KORAMANGALA (4:30PM)") in pm_group and norm("ECITY (6:00PM)") in pm_group, "corrected times printed")

# --- removed / pending / old-quarter content must be absent
generated = "".join(flat[1:-3])  # pages built from Q4 data
for bad in ["APRIL", "MAY2026", "JUNE2026", "BIRTHDAYS", "MARRIAGEANNIVERSARIES", "SECRETARY'SDESK",
            "BAPTISM", "BAPTIZED", "OBITUARY", "CONDOLENCES", "HOLYMATRIMONY",
            "395/CRLM", "371/Carmelaram", "087/Belandur",
            "19thApril2026", "21stJune2026", "Easter"]:
    check(bad.lower() not in generated.lower(), f"no old/removed content: {bad}")
check(not any("BIRTHDAYS" in t or "ANNIVERSARIES" in t for t in pages), "no birthday/anniversary pages anywhere")

# --- carried-forward directory pages identical to Apr-Jun pages 23-25 (apart from page number)
tpl = pdfplumber.open(TEMPLATE)
for k, n in enumerate([23, 24, 25]):
    old = re.sub(r"PAGE\s*\d+", "", tpl.pages[n - 1].extract_text())
    new = re.sub(r"PAGE\s*\d+", "", pages[len(pages) - 3 + k])
    check(norm(old) == norm(new), f"Apr-Jun page {n} carried forward unchanged (now page {len(pages) - 2 + k})")

# --- glyph / layout sanity
for i, p in enumerate(pdf.pages[1:], start=2):
    chars = p.chars
    bad = [c["text"] for c in chars if c["text"] in ("◌", "�")]
    check(not bad, f"page {i}: no dotted-circle / replacement glyphs")
    out = [c["text"] for c in chars if c["x0"] < 30 or c["x1"] > 566 or c["top"] < 30 or c["bottom"] > 800]
    check(not out, f"page {i}: all text inside page margins")
    body_chars = [c for c in chars if not c["fontname"].endswith("Daytona")]
    low = max((c["bottom"] for c in body_chars), default=0)
    check(low < 781, f"page {i}: content clears the footer (lowest text {low:.1f}pt)")
    small = {round(c["size"], 1) for c in body_chars if c["text"].strip() and c["size"] < 11.5
             and c["fontname"].split("+")[-1].startswith(("Aptos", "Noto"))}
    # Superscript ordinals (8pt) are the only sub-12pt body text the template uses.
    check(small <= {8.0}, f"page {i}: no body text below template size {sorted(small)}")

fonts = {c["fontname"].split("+")[-1] for p in pdf.pages[1:-3] for c in p.chars}
print("fonts on generated pages:", sorted(fonts))

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
