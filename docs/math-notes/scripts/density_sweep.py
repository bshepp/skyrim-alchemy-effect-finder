"""Sweep the effects-ring radius and ask: does inner-disc ink density
ever equal the annulus's, for this graph's actual angular layout?"""
import json
import math

d = json.load(open(r'docs\math-notes\anim\plans-uesp.json'))
R = 10.0
ang = {}
for n in d['nodes']:
    x, y = n['pos']
    ang[n['id']] = math.atan2(y, x)
edges = [(ang[e['ing']], ang[e['eff']]) for e in d['edges']]


def ratio(r):
    len_in = len_out = 0.0
    for a_ing, a_eff in edges:
        ax, ay = R * math.cos(a_ing), R * math.sin(a_ing)
        bx, by = r * math.cos(a_eff), r * math.sin(a_eff)
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        a = dx * dx + dy * dy
        b = 2 * (ax * dx + ay * dy)
        c = ax * ax + ay * ay - r * r
        disc = b * b - 4 * a * c
        inside = 0.0
        if disc > 0:
            t1 = (-b - math.sqrt(disc)) / (2 * a)
            t2 = (-b + math.sqrt(disc)) / (2 * a)
            lo, hi = max(0.0, min(t1, t2)), min(1.0, max(t1, t2))
            if hi > lo:
                inside = (hi - lo) * L
        len_in += inside
        len_out += L - inside
    di = len_in / (math.pi * r * r)
    do = len_out / (math.pi * (R * R - r * r))
    return di / do


print(' r/R   disc/annulus density ratio')
best = None
for k in range(2, 100):
    r = R * k / 100
    q = ratio(r)
    if best is None or abs(q - 1) < abs(best[1] - 1):
        best = (r, q)
    if k % 7 == 0 or k >= 95:
        print(f'{r/R:5.2f}  {q:8.3f}')
print(f'closest approach to equality: r/R = {best[0]/R:.2f} '
      f'with ratio {best[1]:.3f}')

# the r -> R theoretical limit from the gap distribution
s = [abs(math.sin(((ae - ai + math.pi) % (2 * math.pi) - math.pi) / 2))
     for ai, ae in edges]
lim = 4 * sum(s) / sum(1 / x for x in s if x > 1e-9)
print(f'r->R limit from gap distribution: {lim:.3f}')
