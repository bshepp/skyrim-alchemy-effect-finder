"""What congestion ratios can ORDERING alone reach? Hill-climb the ring
permutations (even spacing kept) to minimize and to maximize the
disc/annulus ink-density ratio at the equal-area radius."""
import json
import math
import random

d = json.load(open(r'docs\math-notes\anim\plans-uesp.json'))
R = 10.0
r = R / math.sqrt(2)

ings = sorted({e['ing'] for e in d['edges']})
effs = sorted({e['eff'] for e in d['edges']})
cur_ang = {}
for n in d['nodes']:
    x, y = n['pos']
    cur_ang[n['id']] = math.atan2(y, x)
# start from the barycenter layout's ordering
ings.sort(key=lambda i: cur_ang[i])
effs.sort(key=lambda i: cur_ang[i])

edges = [(e['ing'], e['eff']) for e in d['edges']]
by_node = {}
for j, (a, b) in enumerate(edges):
    by_node.setdefault(a, []).append(j)
    by_node.setdefault(b, []).append(j)

AREA_IN = math.pi * r * r
AREA_OUT = math.pi * (R * R - r * r)


def seg(ai, ae):
    ax, ay = R * math.cos(ai), R * math.sin(ai)
    bx, by = r * math.cos(ae), r * math.sin(ae)
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
    return inside, L - inside


def climb(direction, iters=60000, seed=1):
    rng = random.Random(seed)
    slot_i = {n: 2 * math.pi * k / len(ings) for k, n in enumerate(ings)}
    slot_e = {n: 2 * math.pi * k / len(effs) for k, n in enumerate(effs)}
    ang = dict(slot_i)
    ang.update(slot_e)
    per = [seg(ang[a], ang[b]) for a, b in edges]
    tin = sum(p[0] for p in per)
    tout = sum(p[1] for p in per)

    def ratio(ti, to):
        return (ti / AREA_IN) / (to / AREA_OUT)

    for it in range(iters):
        ring = ings if rng.random() < 0.5 else effs
        u, v = rng.sample(ring, 2)
        ang[u], ang[v] = ang[v], ang[u]
        touched = set(by_node[u]) | set(by_node[v])
        old = [(j, per[j]) for j in touched]
        dti = dto = 0.0
        for j in touched:
            a, b = edges[j]
            ni = seg(ang[a], ang[b])
            dti += ni[0] - per[j][0]
            dto += ni[1] - per[j][1]
            per[j] = ni
        new_r = ratio(tin + dti, tout + dto)
        cur_r = ratio(tin, tout)
        better = new_r < cur_r if direction == 'min' else new_r > cur_r
        if better:
            tin += dti
            tout += dto
        else:
            ang[u], ang[v] = ang[v], ang[u]
            for j, p in old:
                per[j] = p
    return ratio(tin, tout)


base = climb('min', iters=0)
print(f'barycenter ordering, equal-area radius: ratio = {base:.3f}')
lo = climb('min')
hi = climb('max')
print(f'hill-climb MINIMUM ratio: {lo:.3f}')
print(f'hill-climb MAXIMUM ratio: {hi:.3f}')
print(f'achievable band by ordering alone: [{lo:.2f}, {hi:.2f}]')
