# Stephanian Koinonia — Q4 2026 build

Builds `out/Stephania_Koinonia_Q4_2026_Draft.pdf` from the Apr–Jun 2026 issue
(used as the visual template) plus the Q4 sources.

Place the source files in `sources/` (not committed — they contain parish
member data):

- `St Stephens MTC BLR - Koinonia Apr-Jun-2026.pdf` (template)
- `Lectionary & Prayer Oct Nov and Dec 2026.xlsx`
- `Vicar's Desk.docx`
- `A4 - 3.pdf` (cover)
- `fonts/` — Noto Sans and Noto Sans Malayalam (Regular, Bold) from notofonts

Then:

```sh
python3 extract_content.py   # -> build/content.json (Q4 data, verbatim)
python3 make_fonts.py        # -> build/fonts (template fonts from the Apr-Jun PDF)
python3 build.py             # -> out/Stephania_Koinonia_Q4_2026_Draft.pdf
python3 validate.py          # content / layout checks, non-zero exit on failure
```

Requires Python (pypdf, pdfplumber, openpyxl, python-docx, fonttools) and Node
with Playwright's Chromium.
