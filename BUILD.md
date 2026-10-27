# Faculty Glyphic Kannada — Regular, v1.009

One font file containing Faculty Glyphic's Latin (unchanged) plus a Kannada
companion restyled to match it.

## Files
- fonts/ttf/FacultyGlyphicKannada-Regular.ttf   — desktop install
- fonts/webfonts/FacultyGlyphicKannada-Regular.woff2 — web (use this first)
- fonts/webfonts/FacultyGlyphicKannada-Regular.woff  — older browsers

## Web use
@font-face {
  font-family: "Faculty Glyphic Kannada";
  src: url("FacultyGlyphicKannada-Regular.woff2") format("woff2"),
       url("FacultyGlyphicKannada-Regular.woff") format("woff");
  font-weight: 400;
}

## The rules (taken from the Latin in this font)
Every Kannada glyph now follows these numbers. They are measured from the
Latin, not chosen by eye, so they will not drift between versions.

| Rule                      | Faculty Latin      | Kannada v1.008 | Kannada v1.009 |
|---------------------------|--------------------|----------------|----------------|
| Flat x-height / head line | 550                | 565            | 550            |
| Round top (overshoot)     | 564 (o)            | 577            | 561            |
| Baseline / round bottom   | 0 / -14            | 0 / -12        | 0 / -11        |
| Thick stroke (vertical)   | 98 (o), 96-101 stems | ~86          | ~97            |
| Thin stroke (horizontal)  | 80 (o), 75-82 bars | ~71            | ~78            |
| Dot (tittle)              | 165 diamond (i)    | 165            | 165            |
| Head curl height          | cap 775            | 811            | 785            |
| OS/2 x-height             | 550                | 568            | 550            |

## What changed in v1.009 (one pass, scripts/v1009.py)
1. Size: Kannada scaled by 0.948 so the head line sits on Faculty's
   x-height (550) instead of 15 units above it.
2. Weight: strokes thickened 8.3 units per side horizontally and 7.2
   vertically, so thick/thin strokes match Faculty's "o" (98 / 80).
   Ottus (subscripts), which are lighter by design, get 0.87 of that.
3. Spacing kept: letters keep their sidebearings; ottus stay centred under
   their letter; below-base forms keep their gap to the letter above;
   above-base marks keep their gap to the head line. GPOS anchors and
   kerning moved with the glyphs.
4. Joints: hairline white cracks and needle tips at junctions are cut back
   to an 8-unit flat (271 places). Parts that only "kissed" in v1.008
   (e.g. the ಣ head bar, ಟ loop) are now properly joined; parts that are
   separate by design (ಕ್ರ, ಭ್ರ, ಮ್ಯ, ೄ forms) keep a 10-unit gap.
5. Edges: all overlaps removed (no self-intersecting contours), duplicate
   points removed, small kinks on curves straightened, curves kept smooth
   after thickening.
6. ು / ೂ alternates used after ಪ ವ ಫ ಘ ಳ (6 glyphs) were rebuilt from
   clean source outlines — v1.008 had a jagged, many-point start and a
   stray fragment there.
7. Faculty's 165-unit diamond dot is kept exactly; only its position scales.
8. Collision check on ~5,300 letter + ottu + vowel-sign clusters. Ottus that
   would touch the descending tail of ಛ ಢ ಫ ಭ (and the ವ ottu after ಕ ottu)
   are nudged right 18-22 units by one GPOS pair lookup (scripts/addpairs.py).
   This also works with a vowel sign in between (e.g. ಛ್ಪು).

## Rebuild
pip install fonttools
python scripts/rebuild6.py        (needs Noto Sans Kannada VF; path inside)
python scripts/v1009.py v1008c.ttf k.ttf kn2.txt
python scripts/addpairs.py k.ttf FacultyGlyphicKannada-Regular.ttf

## Known limits
- Regular weight only
- Outlines adjusted algorithmically; no hand optical corrections
- No Kannada–Latin kerning pairs
- Unhinted
- Line metrics unchanged from v1.008: ascender 1037 / descender -450

License: SIL Open Font License 1.1 (see OFL.txt).
