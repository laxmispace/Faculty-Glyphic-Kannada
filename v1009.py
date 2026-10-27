"""v1.009: bring the Kannada onto Faculty Glyphic's Latin rules in ONE pass.

Rules (measured from the Latin in this same font):
  x-height (flat)      550     -> Kannada head line was 565
  round overshoot top  564     -> Kannada rounds were 577
  baseline / bottom    0 / -14 -> Kannada 0 / -12
  thick round stroke   98 (o)  -> Kannada verticals ~86
  thin  round stroke   80 (o)  -> Kannada horizontals ~71
  tittle (dot)         165 diamond, unchanged

Method
  1. scale every Kannada glyph by S about the origin (outline, advance, GPOS)
  2. embolden by EX (x) / EY (y) per side (FreeType EmboldenXY algorithm);
     subscript forms (lighter by design, 0.87 of base) get 0.87 of that
  3. move all Kannada ink up EY so the baseline stays at 0
  4. spacing: free-standing glyphs move right EX and get 2*EX more advance;
     glyphs that hang left of their origin (vowel signs, ottus, marks) move
     left EX instead, so every join and every ottu keeps its exact position
     relative to its base. Anchors move with their glyph's ink.
  5. diamond dots keep Faculty's 165 size (only their position scales)
  6. clean-up: duplicate points removed; tiny kinks (<8 deg) on smooth curves
     straightened.
"""
import math, sys, copy
from loops import remove_small_loops
from union import union
from crotch import blunt
from apart import keep_apart
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

S, EX, EY = 0.948, 8.3, 7.2
SUB_FACTOR = 0.87
KINK_MAX = 8.0


def contours(g):
    s = 0
    for e in g.endPtsOfContours:
        yield list(range(s, e + 1)); s = e + 1


def is_diamond(pts, fl):
    if len(pts) != 4 or not all(f & 1 for f in fl):
        return False
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    # every point lies on a bbox edge midpoint -> rotated square
    ok = all(min(abs(x - cx), abs(y - cy)) < 0.12 * w for x, y in pts)
    return ok and 0.8 < w / max(h, 1) < 1.25 and 50 < w < 220


def dedupe(pts, fl):
    out, ofl = [], []
    for p, f in zip(pts, fl):
        if out and abs(p[0] - out[-1][0]) < 0.5 and abs(p[1] - out[-1][1]) < 0.5:
            ofl[-1] |= (f & 1)
            continue
        out.append(list(p)); ofl.append(f & 1)
    while len(out) > 1 and abs(out[0][0] - out[-1][0]) < 0.5 and abs(out[0][1] - out[-1][1]) < 0.5:
        ofl[0] |= ofl[-1]; out.pop(); ofl.pop()
    return out, ofl


def unit(v):
    l = math.hypot(*v)
    return ((v[0] / l, v[1] / l), l) if l > 1e-9 else ((0.0, 0.0), 0.0)


def embolden(pts, ex, ey):
    """FreeType FT_Outline_EmboldenXY for one TrueType (clockwise) contour."""
    n = len(pts)
    if n < 3:
        return pts
    out = []
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        (vi, li), (vo, lo) = unit((p[0] - a[0], p[1] - a[1])), unit((b[0] - p[0], b[1] - p[1]))
        d = vi[0] * vo[0] + vi[1] * vo[1]
        if d <= -0.9375 or li == 0 or lo == 0:
            out.append(list(p)); continue
        d += 1.0
        sx, sy = -(vi[1] + vo[1]), (vi[0] + vo[0])
        q = -(vo[0] * vi[1] - vo[1] * vi[0])
        l = min(li, lo)
        sx = sx * ex / d if ex * q <= l * d else sx * l / q
        sy = sy * ey / d if ey * q <= l * d else sy * l / q
        out.append([p[0] + sx, p[1] + sy])
    return out


def unkink(pts, fl):
    n = len(pts); fixed = 0
    for i in range(n):
        if not fl[i]:
            continue
        a, b = (i - 1) % n, (i + 1) % n
        (vi, li), (vo, lo) = unit((pts[i][0] - pts[a][0], pts[i][1] - pts[a][1])), unit((pts[b][0] - pts[i][0], pts[b][1] - pts[i][1]))
        if li < 2 or lo < 2:
            continue
        ang = math.degrees(math.acos(max(-1, min(1, vi[0] * vo[0] + vi[1] * vo[1]))))
        if not (0.8 < ang < KINK_MAX):
            continue
        if not fl[a] and not fl[b]:          # curve-curve: put point on the handle line
            t = li / (li + lo)
            pts[i] = [pts[a][0] + t * (pts[b][0] - pts[a][0]), pts[a][1] + t * (pts[b][1] - pts[a][1])]; fixed += 1
        elif fl[a] and not fl[b]:            # line in -> curve out: align handle with line
            pts[b] = [pts[i][0] + vi[0] * lo, pts[i][1] + vi[1] * lo]; fixed += 1
        elif fl[b] and not fl[a]:            # curve in -> line out
            pts[a] = [pts[i][0] - vo[0] * li, pts[i][1] - vo[1] * li]; fixed += 1
    return fixed


def smooth_set(pts, fl, maxdeg=1.5):
    n = len(pts); out = set()
    for i in range(n):
        if not fl[i]:
            continue
        a, b = (i - 1) % n, (i + 1) % n
        if fl[a] and fl[b]:
            continue
        (vi, li), (vo, lo) = unit((pts[i][0] - pts[a][0], pts[i][1] - pts[a][1])), unit((pts[b][0] - pts[i][0], pts[b][1] - pts[i][1]))
        if li < 1 or lo < 1:
            continue
        if vi[0] * vo[0] + vi[1] * vo[1] > math.cos(math.radians(maxdeg)):
            out.add(i)
    return out


def resmooth(pts, fl, sset):
    """restore G1 continuity at points that were smooth before emboldening"""
    n = len(pts)
    for i in sset:
        a, b = (i - 1) % n, (i + 1) % n
        (vi, li), (vo, lo) = unit((pts[i][0] - pts[a][0], pts[i][1] - pts[a][1])), unit((pts[b][0] - pts[i][0], pts[b][1] - pts[i][1]))
        if li < 1e-6 or lo < 1e-6:
            continue
        if not fl[a] and not fl[b]:
            t = li / (li + lo)
            pts[i] = [pts[a][0] + t * (pts[b][0] - pts[a][0]), pts[a][1] + t * (pts[b][1] - pts[a][1])]
        elif fl[a] and not fl[b]:
            pts[b] = [pts[i][0] + vi[0] * lo, pts[i][1] + vi[1] * lo]
        elif fl[b] and not fl[a]:
            pts[a] = [pts[i][0] - vo[0] * li, pts[i][1] - vo[1] * li]


def implied(pts, fl, tol=0.75):
    """round, then drop on-curve points that sit (within tol) at the midpoint of
    two off-curve neighbours: TrueType implies them exactly, so the curve is
    perfectly smooth there; other smooth points are re-aligned after rounding."""
    P = [[round(x), round(y)] for x, y in pts]
    keep = []
    n = len(P)
    for i in range(n):
        a, b = (i - 1) % n, (i + 1) % n
        if fl[i] and not fl[a] and not fl[b] and n > 4:
            mx, my = (P[a][0] + P[b][0]) / 2, (P[a][1] + P[b][1]) / 2
            if abs(pts[i][0] - mx) <= tol and abs(pts[i][1] - my) <= tol and (P[a][0] + P[b][0]) % 2 == 0 and (P[a][1] + P[b][1]) % 2 == 0:
                continue
        keep.append(i)
    if not any(fl[i] for i in keep):
        keep = list(range(n))
    return [P[i] for i in keep], [fl[i] for i in keep]


def main(src, dst, knlist):
    f = TTFont(src)
    kn = [l.strip() for l in open(knlist) if l.strip()]
    kn = [n for n in kn if n in f['glyf'].glyphs]
    knset = set(kn) | {'uni25CC'}
    glyf, hmtx = f['glyf'], f['hmtx']
    # every Kannada-script glyph, including empty ones (advance must scale too)
    allkn = [n for n in f.getGlyphOrder() if n in knset]
    shift = {}
    stats = dict(kinks=0, dots=0)
    merge_ok = set(l.strip() for l in open('merge_ok.txt'))
    for n in allkn:
        g = glyf[n]; adv, lsb = hmtx[n]
        if g.numberOfContours <= 0:
            hmtx[n] = (round(adv * S), round(lsb * S)); shift[n] = 0; continue
        fac = SUB_FACTOR if 'subscript' in n else 1.0
        ex, ey = EX * fac, EY * fac
        below = g.yMax <= 150 and g.yMin < -150
        above = g.yMin > 400
        # horizontal: free letters keep their sidebearings; stacked forms keep
        # their centre over the base; spacing signs that hang left share the growth
        if adv > 0 and g.xMin >= 0:
            sx, addadv = EX, round(2 * EX)
        elif adv == 0 or below or 'subscript' in n:
            sx, addadv = -EX, 0
        else:
            sx, addadv = 0.0, 0
        # vertical: letters keep the baseline; below-base forms keep their top
        # (gap to the letter above); above-base marks keep their gap to the head
        sy = -ey if below else (2 * EY + ey if above else EY)
        shift[n] = sx
        coords, flags = list(g.coordinates), list(g.flags)
        src_polys, cl, dots = [], [], []
        for idx in contours(g):
            pts = [coords[i] for i in idx]; fl = [flags[i] & 1 for i in idx]
            if is_diamond(pts, fl):
                cx = (max(p[0] for p in pts) + min(p[0] for p in pts)) / 2
                cy = (max(p[1] for p in pts) + min(p[1] for p in pts)) / 2
                src_polys.append(([[x * S + sx, y * S + sy] for x, y in pts], fl))
                pts = [[(x - cx) + cx * S + sx, (y - cy) + cy * S + sy] for x, y in pts]
                stats['dots'] += 1; dots.append(len(cl))
            else:
                pts, fl = dedupe(pts, fl)
                if len(pts) < 3:
                    continue
                pts = [[x * S, y * S] for x, y in pts]
                src_polys.append(([[x + sx, y + sy] for x, y in pts], list(fl)))
                stats['kinks'] += unkink(pts, fl)
                ss = smooth_set(pts, fl)
                pts = embolden(pts, ex, ey)
                resmooth(pts, fl, ss)
                pts, fl, c = remove_small_loops(pts, fl)
                stats['loops'] = stats.get('loops', 0) + c
                pts = [[x + sx, y + sy] for x, y in pts]
            cl.append((pts, fl))
        mv = keep_apart(src_polys, cl, protect=n in merge_ok, fixed=dots)
        if mv:
            stats.setdefault('kept_apart', []).append(n)
        cl, nx = union(cl)
        if nx:
            stats['unions'] = stats.get('unions', 0) + 1
        newpts, newfl, ends = [], [], []
        for pts, fl in cl:
            pts, fl = dedupe(pts, fl)
            pts, fl, c = blunt(pts, fl)
            stats['wedges'] = stats.get('wedges', 0) + c
            pts, fl = dedupe(pts, fl)
            pts, fl = implied(pts, fl)
            newpts += pts; newfl += fl; ends.append(len(newpts) - 1)
        g.coordinates = GlyphCoordinates([(round(x), round(y)) for x, y in newpts])
        g.flags = bytearray(newfl); g.endPtsOfContours = ends; g.numberOfContours = len(ends)
        g.program = None if not hasattr(g, 'program') else g.program
        g.recalcBounds(glyf)
        hmtx[n] = (round(adv * S) + addadv, g.xMin)
    # ---- GPOS ----
    gpos = f['GPOS'].table

    def sv(vr):
        if vr is None:
            return
        for a in ('XPlacement', 'YPlacement', 'XAdvance', 'YAdvance'):
            if hasattr(vr, a) and getattr(vr, a):
                setattr(vr, a, round(getattr(vr, a) * S))

    def anc(a, gname):
        if a is None:
            return None
        a = copy.deepcopy(a)
        a.XCoordinate = round(a.XCoordinate * S + shift.get(gname, 0))
        a.YCoordinate = round(a.YCoordinate * S + EY)
        return a

    touched = 0
    for lk in gpos.LookupList.Lookup:
        for st in lk.SubTable:
            t, s = lk.LookupType, st
            if t == 9:
                t, s = st.ExtensionLookupType, st.ExtSubTable
            cov = getattr(s, 'Coverage', None) or getattr(s, 'MarkCoverage', None)
            if cov is None or not (set(cov.glyphs) & knset):
                continue
            assert set(cov.glyphs) <= knset, 'mixed Latin/Kannada lookup'
            touched += 1
            if t == 1:
                if s.Format == 1:
                    sv(s.Value)
                else:
                    for v in s.Value: sv(v)
            elif t == 2:
                if s.Format == 1:
                    for ps in s.PairSet:
                        for r in ps.PairValueRecord: sv(r.Value1); sv(r.Value2)
                else:
                    for c1 in s.Class1Record:
                        for c2 in c1.Class2Record: sv(c2.Value1); sv(c2.Value2)
            elif t == 3:
                for g, r in zip(s.Coverage.glyphs, s.EntryExitRecord):
                    r.EntryAnchor = anc(r.EntryAnchor, g); r.ExitAnchor = anc(r.ExitAnchor, g)
            elif t == 4:
                for g, r in zip(s.MarkCoverage.glyphs, s.MarkArray.MarkRecord):
                    r.MarkAnchor = anc(r.MarkAnchor, g)
                for g, r in zip(s.BaseCoverage.glyphs, s.BaseArray.BaseRecord):
                    r.BaseAnchor = [anc(a, g) for a in r.BaseAnchor]
            elif t == 6:
                for g, r in zip(s.Mark1Coverage.glyphs, s.Mark1Array.MarkRecord):
                    r.MarkAnchor = anc(r.MarkAnchor, g)
                for g, r in zip(s.Mark2Coverage.glyphs, s.Mark2Array.Mark2Record):
                    r.Mark2Anchor = [anc(a, g) for a in r.Mark2Anchor]
            elif t == 5:
                raise SystemExit('ligature mark positioning not handled')
            elif t in (7, 8):
                pass   # contextual: values live in the referenced lookups
    # ---- metadata ----
    f['OS/2'].sxHeight = 550
    for r in f['name'].names:
        s = r.toUnicode()
        if '1.008' in s:
            r.string = s.replace('1.008', '1.009')
    f['head'].fontRevision = 1.009
    f.save(dst)
    print('glyphs', len(allkn), 'gpos subtables', touched, stats)


if __name__ == '__main__':
    main(*sys.argv[1:4])
