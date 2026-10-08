"""Extract the template fonts embedded in the Apr-Jun 2026 Koinonia PDF.

The PDF carries subsets of Aptos / Aptos Bold (body), Agency FB (page titles),
Daytona (page footer) and Rastanty Cortez (Vicar's signature). The Aptos
subset lacks a few characters used in the Q4 text (q, en dash, curly double
quotes); those are synthesised from existing Aptos glyphs so the body text
keeps one consistent face. Anything else missing falls back to Noto Sans in CSS.
"""
import io
import pathlib

import pypdf
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

HERE = pathlib.Path(__file__).parent
TEMPLATE = HERE / "sources" / "St Stephens MTC BLR - Koinonia Apr-Jun-2026.pdf"
OUT = HERE / "build" / "fonts"

WANTED = {
    "Aptos": "Aptos-Regular.ttf",
    "Aptos,Bold": "Aptos-Bold.ttf",
    "AgencyFB-Reg": "AgencyFB.ttf",
    "Daytona": "Daytona.ttf",
    "Rastanty Cortez": "RastantyCortez.ttf",
}


def extract():
    found = {}
    for page in pypdf.PdfReader(TEMPLATE).pages:
        for f in page["/Resources"].get("/Font", {}).values():
            f = f.get_object()
            base = str(f["/BaseFont"]).split("+", 1)[-1]
            if base not in WANTED or base in found:
                continue
            if "/DescendantFonts" in f:
                fd = f["/DescendantFonts"][0].get_object()["/FontDescriptor"].get_object()
            else:
                fd = f["/FontDescriptor"].get_object()
            found[base] = fd["/FontFile2"].get_object().get_data()
    missing = set(WANTED) - set(found)
    assert not missing, missing
    return found


def add_glyph(font, name, codepoint, parts, advance):
    """parts: list of (source glyph name, affine (a,b,c,d,e,f), reverse)."""
    gs = font.getGlyphSet()
    pen = TTGlyphPen(gs)
    for src, xform, reverse in parts:
        target = ReverseContourPen(pen) if reverse else pen
        rec = DecomposingRecordingPen(gs)
        gs[src].draw(rec)
        rec.replay(TransformPen(target, xform))
    glyph = pen.glyph()
    order = font.getGlyphOrder() + [name]
    font.setGlyphOrder(order)
    font["glyf"].glyphs[name] = glyph
    font["glyf"].glyphOrder = order
    glyph.recalcBounds(font["glyf"])
    font["hmtx"].metrics[name] = (advance, glyph.xMin if hasattr(glyph, "xMin") else 0)
    font["maxp"].numGlyphs = len(order)
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap[codepoint] = name


def patch_aptos(data):
    font = TTFont(io.BytesIO(data))
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    p, emdash, rsquo = cmap[ord("p")], cmap[0x2014], cmap[0x2019]
    pw = hmtx[p][0]
    # q: mirror of p (Aptos p/q are symmetric about the bowl).
    add_glyph(font, "q.synth", ord("q"), [(p, (-1, 0, 0, 1, pw, 0), True)], pw)
    # en dash: em dash at half width.
    ew = hmtx[emdash][0]
    add_glyph(font, "endash.synth", 0x2013, [(emdash, (0.5, 0, 0, 1, 0, 0), False)], ew // 2)
    # Curly double quotes built from the right single quote.
    rw = hmtx[rsquo][0]
    gap = int(rw * 0.55)
    g = font.getGlyphSet()[rsquo]
    rec = DecomposingRecordingPen(font.getGlyphSet())
    g.draw(rec)
    add_glyph(font, "rdquo.synth", 0x201D,
              [(rsquo, (1, 0, 0, 1, 0, 0), False), (rsquo, (1, 0, 0, 1, gap, 0), False)], rw + gap)
    # Left quotes: the right quote rotated 180 degrees about its own centre.
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(font.getGlyphSet())
    g.draw(bp)
    x0, y0, x1, y1 = bp.bounds
    cx, cy = x0 + x1, y0 + y1
    add_glyph(font, "ldquo.synth", 0x201C,
              [(rsquo, (-1, 0, 0, -1, cx, cy), False), (rsquo, (-1, 0, 0, -1, cx + gap, cy), False)],
              rw + gap)
    add_glyph(font, "lsquo.synth", 0x2018, [(rsquo, (-1, 0, 0, -1, cx, cy), False)], rw)
    for t in ("meta", "STAT", "hdmx", "LTSH", "VDMX"):
        if t in font:
            del font[t]
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for base, data in extract().items():
        if base == "Aptos":
            data = patch_aptos(data)
        (OUT / WANTED[base]).write_bytes(data)
        print("wrote", WANTED[base], len(data))


if __name__ == "__main__":
    main()
