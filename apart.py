"""Keep parts that are separate by design separate after emboldening.

A glyph's contours are grouped into pieces (an outer contour plus the holes
inside it). If two pieces were apart in the source but come closer than GAP
after emboldening, the smaller piece is moved straight away from the larger
one until the gap is GAP again.
"""
import math

GAP = 10.0


def area(poly):
    n = len(poly)
    return sum(poly[k][0] * poly[(k + 1) % n][1] - poly[(k + 1) % n][0] * poly[k][1] for k in range(n)) / 2


def inside(pt, poly):
    x, y = pt; c = False; n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def pieces(polys):
    """group contour indices: outer (clockwise, area<0) + holes inside it"""
    outers = [i for i, p in enumerate(polys) if area(p) < 0]
    holes = [i for i, p in enumerate(polys) if area(p) >= 0]
    groups = {o: [o] for o in outers}
    for h in holes:
        for o in sorted(outers, key=lambda o: abs(area(polys[o]))):
            if inside(polys[h][0], polys[o]):
                groups[o].append(h); break
    return list(groups.values())


def _pt_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1]), q


def dist(P, Q):
    """min distance between two polygons' outlines (+ the closest points);
    0 if they touch or one point lies inside the other."""
    best = (1e9, None, None)
    for poly_a, poly_b, flip in ((P, Q, False), (Q, P, True)):
        n = len(poly_b)
        for p in poly_a:
            for k in range(n):
                d, q = _pt_seg(p, poly_b[k], poly_b[(k + 1) % n])
                if d < best[0]:
                    best = (d, p, q) if not flip else (d, q, p)
    return best


def flat(pts, fl, k=8):
    from crotch import to_segments, ev
    out = []
    for s in to_segments(pts, fl):
        if s[0] == 'L':
            out.append(list(s[1]))
        else:
            out += [list(ev(s, t / k)) for t in range(k)]
    return out


def keep_apart(src_c, new_c, protect=False, fixed=()):
    """src_c/new_c: lists of (pts, flags) in the same contour order.
    Moves pieces of new_c (in place) so designed gaps stay open."""
    if protect or len(src_c) < 2:
        return 0
    src_polys = [flat(p, f) for p, f in src_c]
    new_flat = [flat(p, f) for p, f in new_c]
    new_polys = [p for p, _ in new_c]
    groups = pieces(src_polys)
    if len(groups) < 2:
        return 0
    moved = 0
    for a in range(len(groups)):
        for b in range(a + 1, len(groups)):
            ga, gb = groups[a], groups[b]
            if set(ga) & set(fixed) or set(gb) & set(fixed):
                continue          # Faculty diamond dots stay where they are
            d0 = dist(src_polys[ga[0]], src_polys[gb[0]])[0]
            if d0 < 3:
                continue          # designed to touch: a join
            small, big = (ga, gb) if abs(area(new_flat[ga[0]])) < abs(area(new_flat[gb[0]])) else (gb, ga)
            # direction: from the closest point on big to the closest point on small (source geometry)
            _, qb, qs = dist(src_polys[big[0]], src_polys[small[0]])
            vx, vy = qs[0] - qb[0], qs[1] - qb[1]; L = math.hypot(vx, vy) or 1
            ux, uy = vx / L, vy / L
            for _ in range(40):
                d = dist(new_flat[big[0]], new_flat[small[0]])[0]
                if d >= GAP:
                    break
                for i in small:
                    new_polys[i][:] = [[x + ux * 1.0, y + uy * 1.0] for x, y in new_polys[i]]
                    new_flat[i][:] = [[x + ux * 1.0, y + uy * 1.0] for x, y in new_flat[i]]
                moved += 1
    return moved
