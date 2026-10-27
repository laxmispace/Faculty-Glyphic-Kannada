import math


def seg_inter(p1, p2, q1, q2):
    d1 = (p2[0] - p1[0], p2[1] - p1[1]); d2 = (q2[0] - q1[0], q2[1] - q1[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    w = (q1[0] - p1[0], q1[1] - p1[1])
    t = (w[0] * d2[1] - w[1] * d2[0]) / den; u = (w[0] * d1[1] - w[1] * d1[0]) / den
    if 1e-7 < t < 1 - 1e-7 and 1e-7 < u < 1 - 1e-7:
        return (p1[0] + t * d1[0], p1[1] + t * d1[1])
    return None


def _area_perim(poly):
    n = len(poly); a = 0; p = 0
    for k in range(n):
        x1, y1 = poly[k]; x2, y2 = poly[(k + 1) % n]
        a += x1 * y2 - x2 * y1; p += math.hypot(x2 - x1, y2 - y1)
    return abs(a) / 2, p


def remove_small_loops(pts, fl, K=14, AMAX=2500.0, PMAX=160.0):
    """Cut out small self-intersection loops (offset 'swallowtails').
    The loop that is cut is the one with fewer points; it must also be
    small in area and perimeter, so real shapes are never removed."""
    changed = 0
    for _ in range(300):
        n = len(pts); found = None
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            for d in range(2, min(K + 2, n - 2)):
                j = (i + d) % n
                X = seg_inter(a, b, pts[j], pts[(j + 1) % n])
                if not X:
                    continue
                loop = [X] + [pts[(i + 1 + k) % n] for k in range(d)]
                A, P = _area_perim(loop)
                if A <= AMAX and P <= PMAX and d < n - d:
                    found = (i, j, X, d); break
            if found:
                break
        if not found:
            break
        i, j, X, d = found
        rm = {(i + 1 + k) % n for k in range(d)}
        start = (j + 1) % n
        keep, kfl = [], []
        for k in [(start + m) % n for m in range(n)]:
            if k in rm:
                continue
            keep.append(pts[k]); kfl.append(fl[k])
            if k == i:
                keep.append(list(X)); kfl.append(1)
        pts, fl = keep, kfl; changed += 1
    return pts, fl, changed
