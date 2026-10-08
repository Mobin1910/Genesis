"""Build Stephania_Koinonia_Q4_2026_Draft.pdf.

Pipeline
  1. extract_content.py  -> build/content.json   (Q4 data, verbatim)
  2. make_fonts.py       -> build/fonts/*.ttf     (template fonts from Apr-Jun PDF)
  3. this script:
       - writes one HTML file per section using the template's measured styles
       - prints each with Chromium (transparent page, content only)
       - lays each printed page over the template's own page background
         (the faint artwork image, taken from the Apr-Jun PDF)
       - carries forward Apr-Jun pages 23-25 (contacts / organisations /
         prayer groups / fellowships / UPI / directory app) unchanged except
         for the page number
       - prepends the supplied Q4 cover and stamps page numbers
"""
import datetime
import html
import json
import pathlib
import re
import subprocess

import pypdf
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

HERE = pathlib.Path(__file__).parent
SRC = HERE / "sources"
BUILD = HERE / "build"
OUT = HERE / "out" / "Stephania_Koinonia_Q4_2026_Draft.pdf"
TEMPLATE = SRC / "St Stephens MTC BLR - Koinonia Apr-Jun-2026.pdf"
COVER = SRC / "A4 - 3.pdf"

# Apr-Jun pages carried forward unchanged (1-based): contact details,
# organisations, prayer groups, fellowships, UPI / parish directory app.
CARRY_FORWARD_PAGES = [23, 24, 25]

PURPLE = "#7030A0"   # template rgb(0.439, 0.188, 0.627)
LAVENDER = "#DCBFF9"  # template rgb(0.863, 0.749, 0.976)

def weekday(it):
    """Day name from the calendar date. The workbook's DAY column says "Sun" for
    every service, including 25 Dec (Friday) and 31 Dec (Thursday); the church
    confirmed the actual weekday should be printed."""
    d = datetime.datetime.strptime(f"{int(it['date'][:-2])} {it['month']} 2026", "%d %B %Y")
    return d.strftime("%A").upper()

e = html.escape

# --------------------------------------------------------------------------
# Shared CSS. Measurements are in pt, taken from the Apr-Jun PDF:
#   page A4, content x 36 -> 559.44, continuation pages start at y 48.8,
#   content ends by y ~776, footer baseline y 793.6
#   page title: Agency FB 21.96pt, +1.5pt tracking, baseline y 70.4,
#               dotted underline 1.44 x 1.10 dashes every 2.88pt
#   lectionary: Aptos 13pt, 15.8pt leading, rows 20.3pt for one line,
#               label column 156pt, 0.48pt black rules
#   prayer meetings: header Aptos Bold 13pt purple on lavender,
#               body Aptos 12pt / 14.6pt, columns 112.7 / 120 / 288.8
#   vicar's message: Aptos 13pt / 18.25pt, justified, one blank line
#               between paragraphs, signature Rastanty Cortez 48pt purple
# --------------------------------------------------------------------------
CSS = f"""
@font-face {{ font-family: 'Aptos'; src: url('fonts/Aptos-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: 'Aptos'; src: url('fonts/Aptos-Bold.ttf'); font-weight: 700; }}
@font-face {{ font-family: 'AgencyFB'; src: url('fonts/AgencyFB.ttf'); }}
@font-face {{ font-family: 'Daytona'; src: url('fonts/Daytona.ttf'); }}
@font-face {{ font-family: 'Rastanty'; src: url('fonts/RastantyCortez.ttf'); }}
@font-face {{ font-family: 'Mal'; src: url('../sources/fonts/NotoSansMalayalam-Regular.ttf');
              font-weight: 400; unicode-range: U+0D00-0D7F, U+200C-200D; size-adjust: 100%; }}
@font-face {{ font-family: 'Mal'; src: url('../sources/fonts/NotoSansMalayalam-Bold.ttf');
              font-weight: 700; unicode-range: U+0D00-0D7F, U+200C-200D; size-adjust: 100%; }}
@font-face {{ font-family: 'Fallback'; src: url('../sources/fonts/NotoSans-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: 'Fallback'; src: url('../sources/fonts/NotoSans-Bold.ttf'); font-weight: 700; }}

@page {{ size: 595.32pt 841.92pt; margin: 48.8pt 35.88pt 64pt 36pt; }}
html, body {{ margin: 0; padding: 0; background: transparent; }}
body {{ font-family: 'Aptos', 'Mal', 'Fallback'; color: #000; font-size: 13pt;
        -webkit-print-color-adjust: exact; print-color-adjust: exact; }}

.title {{ height: 42.5pt; position: relative; text-align: center; }}
.title span {{ position: absolute; left: 0; right: 0; top: 1.84pt;
               font-family: 'AgencyFB'; font-size: 21.96pt; line-height: 21.96pt;
               letter-spacing: 1.5pt; }}
.title i {{ display: inline-block; font-style: normal; position: relative; padding-left: 1.5pt; }}
.title i svg {{ position: absolute; left: 0; bottom: -1.7pt; width: calc(100% - 1.5pt); height: 1.104pt; }}

sup {{ font-size: 8pt; line-height: 0; vertical-align: 4.2pt; }}

table {{ width: 523.44pt; border-collapse: collapse; table-layout: fixed; }}
td, th {{ border: 0.48pt solid #000; padding: 2pt 5.1pt 2.5pt; vertical-align: top;
          line-height: 15.8pt; text-align: left; overflow-wrap: anywhere; }}

/* Lectionary */
table.lect col.l {{ width: 156.3pt; }}
table.lect tr {{ break-inside: avoid; }}
tr.month, tr.svc {{ break-after: avoid; }}
/* A service may continue onto the next page (as in the template), but never
   leaves its header strip or only its last rows stranded. */
table.lect tr.keep {{ break-before: avoid; }}
table.lect tbody.last {{ break-inside: avoid; }}
table.lect td.k {{ font-weight: 700; }}
tr.month td {{ background: {PURPLE}; color: #fff; font-weight: 700; text-align: center;
               border-color: {PURPLE}; }}
tr.svc td {{ background: {LAVENDER}; color: {PURPLE}; font-weight: 700;
             border-top-color: {PURPLE}; }}
.ml {{ line-height: 17pt; }}

/* Area wise prayer meetings */
table.pm {{ font-size: 12pt; }}
table.pm col.d {{ width: 113.2pt; }}
table.pm col.g {{ width: 120.5pt; }}
table.pm th {{ background: {LAVENDER}; color: {PURPLE}; font-size: 13pt; font-weight: 700;
               vertical-align: top; }}
table.pm td {{ line-height: 14.6pt; vertical-align: middle; padding: 1pt 5.1pt 1.5pt; }}
table.pm tr {{ break-inside: avoid; }}
table.pm tr.newpage {{ break-before: page; }}

/* Vicar's message */
.vicar {{ font-size: 13pt; line-height: 18.25pt; text-align: justify; }}
.vicar .photo {{ float: left; width: 129pt; height: 141pt; }}
.vicar .lead {{ height: 18.25pt; }}
.vicar p {{ margin: 0 0 18.25pt; }}
.signrow {{ display: flex; justify-content: space-between; align-items: baseline; margin-top: 4pt; }}
.sign {{ font-family: 'Rastanty'; font-size: 48pt; line-height: 56pt; color: {PURPLE}; }}
"""


def page_html(body):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"


def title(text):
    # Word's dotted underline: 1.44 x 1.104pt dots every 2.88pt (SVG user units are px).
    px = 96 / 72
    dots = "".join(f"<rect x='{k * 2.88 * px:.3f}' width='{1.44 * px:.3f}' height='{1.104 * px:.3f}'/>"
                   for k in range(200))
    return f"<div class='title'><span><i>{e(text)}<svg>{dots}</svg></i></span></div>"


# Legacy Malayalam typing in the workbook: an independent vowel followed by a
# vowel sign, which Word's fonts draw as one letter but Unicode shaping shows
# as a broken cluster. Display them as the single letter they represent.
MALAYALAM_DISPLAY = {"\u0D07\u0D57": "\u0D08",   # ഇ + ൗ -> ഈ
                     "\u0D0E\u0D46": "\u0D10"}   # എ + െ -> ഐ


def display(text):
    for old, new in MALAYALAM_DISPLAY.items():
        text = text.replace(old, new)
    return text


def multiline(text):
    """Escape and keep the source's own line breaks."""
    lines = [e(display(l)) for l in text.split("\n")]
    return "<br>".join(f"<span class='ml'>{l}</span>" if re.search('[ഀ-ൿ]', l) else l
                       for l in lines)


# ------------------------------------------------------------------ Vicar
def vicar_html(v):
    paras = "".join(f"<p>{e(p)}</p>" for p in v["paragraphs"])
    body = (title("VICAR’S MESSAGE") +
            "<div class='vicar'><div class='photo'></div><div class='lead'></div>"
            f"{paras}<p>{e(v['closing'])}</p></div>"
            f"<div class='signrow'><div>{e(v['date'])}</div><div class='sign'>{e(v['signOff'])}</div></div>")
    return page_html(body)


# ------------------------------------------------------------------ Lectionary
LESSON_RE = re.compile(r"^((?:[1-3])?[A-Z][a-z]+ \d+:\d+(?:-\d+(?::\d+)?)?)\s+(.+)$", re.S)


def lesson(text):
    """Template shows the reader on the first line and the reference below."""
    m = LESSON_RE.match(text)
    if not m:
        return multiline(text)
    ref, reader = m.groups()
    return f"{multiline(reader)}<br>{e(ref)}"


def ordinal(d):
    m = re.match(r"^(\d+)(\D*)$", d)
    return f"{m.group(1)}<sup>{e(m.group(2).upper())}</sup>" if m else e(d)


def theme(text):
    return "<br>".join(multiline(part.strip()) for part in text.split(";"))


def lectionary_html(items):
    out = [title("LECTIONARY"), "<table class='lect'><colgroup><col class='l'><col></colgroup>"]
    month = None
    for n, it in enumerate(items):
        out.append("<tbody class='last'>" if n == len(items) - 1 else "<tbody>")
        if it["month"] != month:
            month = it["month"]
            out.append(f"<tr class='month'><td colspan='2'>{e(month.upper())}</td></tr>")
        day = weekday(it)
        out.append(f"<tr class='svc'><td colspan='2'>{e(day)} {ordinal(it['date'])} "
                   f"{e(it['month'].upper())} 2026 AT {e(it['time'])}</td></tr>")
        rows = [
            ("WORSHIP", f"Holy Qurbana ({e(it['language'])})"),
            ("THEME", theme(it["theme"])),
            ("1<sup>st</sup> LESSON", lesson(it["firstLesson"])),
            ("2<sup>nd</sup> LESSON", lesson(it["secondLesson"])),
            ("EPISTLE", multiline(it["epistle"])),
            ("WORSHIP ASSISTANCE", multiline(it["worshipAssistance"])),
            ("KISS OF PEACE", multiline(it["kissOfPeace"])),
            ("OFFERTORY", multiline(it["offertory"])),
            ("PRAYER", multiline(it["prayer"])),
        ]
        for i, (k, v) in enumerate(rows):
            keep = " class='keep'" if i < 3 or i >= len(rows) - 3 else ""
            out.append(f"<tr{keep}><td class='k'>{k}</td><td>{v}</td></tr>")
        out.append("</tbody>")
    out.append("</table>")
    return page_html("".join(out))


# ------------------------------------------------------------------ Prayer meetings
def group_cell(text):
    # "KORAMANGALA (4:00PM)" -> group on one line, time below, as in the template.
    m = re.match(r"^(.*?)\s*(\(.*\))\s*$", text)
    return f"{e(m.group(1))}<br>{e(m.group(2))}" if m else e(text)


def prayer_html(items):
    out = [title("AREA WISE PRAYER MEETINGS"),
           "<table class='pm'><colgroup><col class='d'><col class='g'><col></colgroup>"
           "<thead><tr><th>DATE</th><th>PRAYER GROUP &amp; TIME</th><th>MEMBER DETAILS</th></tr></thead><tbody>"]
    # The list needs two pages at template size; split at the month boundary
    # nearest the middle rather than leaving a lone row on the second page.
    month_starts = [i for i, it in enumerate(items) if it["dateGroupStart"] and
                    (i == 0 or it["date"].split()[1] != items[i - 1]["date"].split()[1])]
    split = min(month_starts[1:], key=lambda i: abs(i - len(items) / 2), default=None)
    for i, it in enumerate(items):
        out.append("<tr class='newpage'>" if i == split else "<tr>")
        if it["dateGroupStart"]:
            span = f" rowspan='{it['dateGroupSize']}'" if it["dateGroupSize"] > 1 else ""
            out.append(f"<td{span}>{e(it['date'])}</td>")
        out.append(f"<td>{group_cell(it['groupAndTime'])}</td><td>{multiline(it['memberDetails'])}</td></tr>")
    out.append("</tbody></table>")
    return page_html("".join(out))


# ------------------------------------------------------------------ Footers
def footer_html(numbers):
    pages = "".join(
        f"<div class='pg'>{'<span>PAGE&nbsp;' + str(n) + '</span>' if n else ''}</div>" for n in numbers)
    css = (CSS + "@page { margin: 0; } .pg { height: 841.92pt; position: relative; break-after: page; }"
           ".pg span { position: absolute; right: 37pt; top: 785.5pt; font-family: 'Daytona';"
           " font-size: 9pt; line-height: 9pt; letter-spacing: 0.97pt; }")
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{pages}</body></html>"


# ------------------------------------------------------------------ PDF helpers
def print_pdf(name, markup):
    src = BUILD / f"{name}.html"
    dst = BUILD / f"{name}.pdf"
    src.write_text(markup)
    subprocess.run(["node", str(HERE / "print_pdf.js"), str(src), str(dst)], check=True,
                   env={**__import__("os").environ, "PLAYWRIGHT_MODULE": "/opt/node22/lib/node_modules/playwright"})
    return pypdf.PdfReader(dst)


def background_pages():
    """Page backgrounds from the template: [plain, vicar-with-photo]."""
    reader = pypdf.PdfReader(TEMPLATE)
    writer = pypdf.PdfWriter()
    bg_ops = b"q 0 0 595.32 841.92 re W n 627.85 0 0 895.43 -15.9 -54.06 cm /Image88 Do Q\n"
    # Vicar photo + its frame, exactly as placed on Apr-Jun page 2.
    photo_ops = (b"q 129 0.000061035 0 140.65 25.44 607.91 cm /Image113 Do Q\n"
                 b"q 40.5 621.92 99.85 111.5 re W n 99.85 0 0 111.5 40.5 621.92 cm /Image115 Do Q\n")
    for src_index, ops, names in [(12, bg_ops, ["/Image88"]),
                                  (1, bg_ops + photo_ops, ["/Image88", "/Image113", "/Image115"])]:
        page = writer.add_page(reader.pages[src_index])
        xobjs = page["/Resources"]["/XObject"]
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/XObject"): DictionaryObject({NameObject(n): xobjs.raw_get(n) for n in names})})
        stream = DecodedStreamObject()
        stream.set_data(ops)
        page[NameObject("/Contents")] = writer._add_object(stream)
        for k in ("/Annots", "/StructParents"):
            if k in page:
                del page[k]
    path = BUILD / "backgrounds.pdf"
    writer.write(path)
    return pypdf.PdfReader(path).pages


FOOTER_RE = re.compile(rb"(/Subtype/Footer>> BDC)(.*?)(EMC)", re.S)


def strip_template_footer(page):
    data = page.get_contents().get_data()
    new, n = FOOTER_RE.subn(rb"\1\n\3", data, count=1)
    assert n == 1, "footer artifact not found"
    stream = DecodedStreamObject()
    stream.set_data(new)
    page.replace_contents(stream)


def main():
    content = json.loads((BUILD / "content.json").read_text())
    assert len(content["lectionary"]) == 15 and len(content["prayerMeetings"]) == 12

    plain_bg, vicar_bg = background_pages()
    sections = [
        ("vicar", vicar_html(content["vicarMessage"]), vicar_bg),
        ("lectionary", lectionary_html(content["lectionary"]), plain_bg),
        ("prayer", prayer_html(content["prayerMeetings"]), plain_bg),
    ]

    writer = pypdf.PdfWriter()
    writer.append(str(COVER))  # page 1, untouched

    for name, markup, bg in sections:
        for i, page in enumerate(print_pdf(name, markup).pages):
            page.mediabox = pypdf.generic.RectangleObject([0, 0, 595.32, 841.92])
            # The vicar photo belongs only on the first page of the message.
            page.merge_page(bg if i == 0 else plain_bg, over=False)
            writer.add_page(page)

    template = pypdf.PdfReader(TEMPLATE)
    for n in CARRY_FORWARD_PAGES:
        page = writer.add_page(template.pages[n - 1])
        strip_template_footer(page)

    total = len(writer.pages)
    footers = print_pdf("footers", footer_html([None] + list(range(2, total + 1)))).pages
    for i in range(1, total):
        writer.pages[i].merge_page(footers[i])

    writer.add_metadata({"/Title": "Stephanian Koinonia - Oct-Dec Quarter 2026 (Vol. 63) - Draft"})
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "wb") as f:
        writer.write(f)
    print(f"wrote {OUT} ({total} pages)")


if __name__ == "__main__":
    main()
