"""Blunt hairline wedges at joints.

Where two edges of one outline meet at a very sharp angle, the tip of the
wedge becomes a hairline: a white crack running into a junction, or a thin
ink needle. Both tips are cut where the wedge reaches W0 units across, by
splitting the two curves exactly (de Casteljau) and joining them with a short
straight edge. Everything else in the outline is untouched.
"""
import math

W0 = 8.0
MAX_DEG = 35.0


def to_segments(pts, fl):
    n = len(pts)
    # rotate so we start on an on-curve point (insert implied if none)
    pts = [tuple(p) for p in pts]; fl = list(fl)
    if not any(fl):
        mid = ((pts[-1][0] + pts[0][0]) / 2, (pts[-1][1] + pts[0][1]) / 2)
        pts = [mid] + pts; fl = [1] + fl
        n = len(pts)
    s = fl.index(1)
    pts = pts[s:] + pts[:s]; fl = fl[s:] + fl[:s]
    segs = []
    i = 0
    cur = tuple(pts[0])
    k = 1
    ctrl = None
    seq = list(zip(pts[1:], fl[1:])) + [(pts[0], 1)]
    for p, f in seq:
        p = tuple(p)
        if f:
            segs.append(('Q', cur, ctrl, p) if ctrl else ('L', cur, p))
            cur = p; ctrl = None
        else:
            if ctrl:
                mid = ((ctrl[0] + p[0]) / 2, (ctrl[1] + p[1]) / 2)
                segs.append(('Q', cur, ctrl, mid)); cur = mid
            ctrl = p
    return segs


def from_segments(segs):
    pts, fl = [], []
    for s in segs:
        pts.append(s[1]); fl.append(1)
        if s[0] == 'Q':
            pts.append(s[2]); fl.append(0)
    return [list(p) for p in pts], fl


def ev(s, t):
    if s[0] == 'L':
        return (s[1][0] + t * (s[2][0] - s[1][0]), s[1][1] + t * (s[2][1] - s[1][1]))
    a, c, b = s[1], s[2], s[3]; u = 1 - t
    return (u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1])


def split(s, t):
    if s[0] == 'L':
        m = ev(s, t); return ('L', s[1], m), ('L', m, s[2])
    a, c, b = s[1], s[2], s[3]
    p1 = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
    p2 = (c[0] + t * (b[0] - c[0]), c[1] + t * (b[1] - c[1]))
    m = (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return ('Q', a, p1, m), ('Q', m, p2, b)


def tan_end(s):
    a = s[-2] if s[0] == 'Q' else s[1]; b = s[-1]
    if s[0] == 'Q' and math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
        a = s[1]
    return (b[0] - a[0], b[1] - a[1])


def tan_start(s):
    a = s[1]; b = s[2]
    if s[0] == 'Q' and math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
        b = s[3]
    return (b[0] - a[0], b[1] - a[1])


def seglen(s):
    if s[0] == 'L':
        return math.hypot(s[2][0] - s[1][0], s[2][1] - s[1][1])
    L = 0; p = s[1]
    for k in range(1, 21):
        q = ev(s, k / 20); L += math.hypot(q[0] - p[0], q[1] - p[1]); p = q
    return L


def merge_micro(pts, fl, tol=4.0):
    """collapse straight micro-edges (both ends on-curve, shorter than tol)."""
    pts = [list(p) for p in pts]; fl = list(fl)
    changed = True
    while changed and len(pts) > 4:
        changed = False
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            if fl[i] and fl[j] and math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]) < tol:
                m = [(pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2]
                pts[i] = m; del pts[j]; del fl[j]; changed = True
                break
    return pts, fl


def blunt(pts, fl):
    pts, fl = merge_micro(pts, fl)
    segs = to_segments(pts, fl)
    n = len(segs)
    if n < 3:
        return pts, fl, 0
    cuts = 0
    k = 0
    while k < len(segs):
        n = len(segs)
        s1, s2 = segs[k], segs[(k + 1) % n]
        ti, to = tan_end(s1), tan_start(s2)
        li, lo = math.hypot(*ti), math.hypot(*to)
        if li < 1e-6 or lo < 1e-6:
            k += 1; continue
        cosw = (-ti[0] * to[0] - ti[1] * to[1]) / (li * lo)     # angle between the two edges at the tip
        wedge = math.degrees(math.acos(max(-1, min(1, cosw))))
        if wedge >= MAX_DEG:
            k += 1; continue
        L1, L2 = seglen(s1), seglen(s2)
        # walk back on s1 and forward on s2 until the gap reaches W0
        found = None
        for step in range(1, 200):
            t1 = 1 - step / 200; t2 = step / 200
            if (1 - t1) * L1 > 0.85 * L1 or t2 * L2 > 0.85 * L2:
                break
            p, q = ev(s1, t1), ev(s2, t2)
            if math.hypot(p[0] - q[0], p[1] - q[1]) >= W0:
                found = (t1, t2); break
        if not found:
            k += 1; continue
        a, _ = split(s1, found[0]); _, b = split(s2, found[1])
        bridge = ('L', a[-1], b[1])
        if (k + 1) % n == 0:     # s2 is segs[0]
            segs = [b] + segs[1:k] + [a, bridge]
        else:
            segs = segs[:k] + [a, bridge, b] + segs[k + 2:]
        cuts += 1
        k += 2
    p, f = from_segments(segs)
    return p, f, cuts
