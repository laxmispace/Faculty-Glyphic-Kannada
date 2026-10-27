"""Overlap removal (union) for TrueType contours, done on the control polygon.

Every point (on- or off-curve) is treated as a polygon vertex. Crossings are
found between control-polygon edges, inserted as on-curve points, and the
pieces that lie on the outer boundary of the filled (nonzero) region are kept
and re-linked. Contours that do not touch anything are kept or dropped by the
same nonzero test, so a contour buried completely in ink disappears.
"""
import math


def _inter(p1, p2, q1, q2):
    d1 = (p2[0] - p1[0], p2[1] - p1[1]); d2 = (q2[0] - q1[0], q2[1] - q1[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    w = (q1[0] - p1[0], q1[1] - p1[1])
    t = (w[0] * d2[1] - w[1] * d2[0]) / den
    u = (w[0] * d1[1] - w[1] * d1[0]) / den
    e = 1e-9
    if e < t < 1 - e and e < u < 1 - e:
        return t, u, (p1[0] + t * d1[0], p1[1] + t * d1[1])
    return None


def winding(pt, polys):
    x, y = pt; w = 0
    for poly in polys:
        n = len(poly)
        for i in range(n):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
            if y1 <= y < y2 or y2 <= y < y1:
                xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if xi > x:
                    w += 1 if y2 > y1 else -1
    return w


def _bbox(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def union(contours):
    """contours: list of (pts, flags). Returns (new_contours, n_crossings)."""
    cs = [([tuple(p) for p in pts], list(fl)) for pts, fl in contours if len(pts) >= 3]
    polys = [c[0] for c in cs]
    # 1. crossings
    cuts = [[[] for _ in range(len(p))] for p in polys]   # per edge: (t, node_id, point)
    nid = 0
    boxes = [_bbox(p) for p in polys]
    for a in range(len(polys)):
        for b in range(a, len(polys)):
            ba, bb = boxes[a], boxes[b]
            if ba[0] > bb[2] or bb[0] > ba[2] or ba[1] > bb[3] or bb[1] > ba[3]:
                continue
            P, Q = polys[a], polys[b]
            na, nb = len(P), len(Q)
            for i in range(na):
                p1, p2 = P[i], P[(i + 1) % na]
                for j in range(i + 2 if a == b else 0, nb):
                    if a == b and (j + 1) % nb == i:
                        continue
                    r = _inter(p1, p2, Q[j], Q[(j + 1) % nb])
                    if r:
                        t, u, X = r
                        cuts[a][i].append((t, nid, X)); cuts[b][j].append((u, nid, X)); nid += 1
    if nid == 0:
        keep = []
        for pts, fl in cs:
            if _is_boundary_contour(pts, polys):
                keep.append((pts, fl))
        return keep, 0
    # 2. contours with nodes inserted
    seqs = []
    for c, (pts, fl) in enumerate(cs):
        s = []
        for i in range(len(pts)):
            s.append((pts[i], fl[i], None))
            for t, k, X in sorted(cuts[c][i]):
                s.append((X, 1, k))
        seqs.append(s)
    newpolys = [[q[0] for q in s] for s in seqs]
    # 3. chains between nodes
    chains = []          # (start_node, end_node, [(pt,fl)...] including both node points)
    keep_whole = []
    for s in seqs:
        idx = [i for i, q in enumerate(s) if q[2] is not None]
        if not idx:
            pts = [q[0] for q in s]
            if _is_boundary_contour(pts, newpolys):
                keep_whole.append(([q[0] for q in s], [q[1] for q in s]))
            continue
        n = len(s)
        for m, i0 in enumerate(idx):
            i1 = idx[(m + 1) % len(idx)]
            seg = []
            k = i0
            while True:
                seg.append(s[k])
                if k == i1 and len(seg) > 1:
                    break
                k = (k + 1) % n
                if k == i0 and len(idx) == 1:
                    seg.append(s[k]); break
            # classify by the middle edge of the chain
            e = len(seg) // 2 - 1 if len(seg) > 2 else 0
            A, B = seg[e][0], seg[e + 1][0]
            mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
            dx, dy = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L * 0.05, dx / L * 0.05
            wl = winding((mx + nx, my + ny), newpolys); wr = winding((mx - nx, my - ny), newpolys)
            if (wl == 0) != (wr == 0):
                chains.append((seg[0][2], seg[-1][2], seg))
    # 4. link
    by_start = {}
    for ch in chains:
        by_start.setdefault(ch[0], []).append(ch)
    used = set(); out = list(keep_whole)
    for ch in chains:
        if id(ch) in used:
            continue
        pts, fl = [], []
        cur = ch; guard = 0
        while cur is not None and id(cur) not in used and guard < 10000:
            used.add(id(cur)); guard += 1
            for q in cur[2][:-1]:
                pts.append(q[0]); fl.append(q[1])
            nxt = [c for c in by_start.get(cur[1], []) if id(c) not in used]
            cur = nxt[0] if nxt else None
        if len(pts) >= 3:
            out.append((pts, fl))
    return out, nid


def _is_boundary_contour(pts, polys):
    n = len(pts)
    for i in range(n):
        A, B = pts[i], pts[(i + 1) % n]
        dx, dy = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dy)
        if L < 2:
            continue
        mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        nx, ny = -dy / L * 0.05, dx / L * 0.05
        wl = winding((mx + nx, my + ny), polys); wr = winding((mx - nx, my - ny), polys)
        return (wl == 0) != (wr == 0)
    return True
