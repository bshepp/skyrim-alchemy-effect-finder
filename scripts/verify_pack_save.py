"""Verify a dataset pack against a live save: clean-room protocol step 4
(docs/cleanroom-plan.md), the other half of gen_give_bat.py.

The round trip being asserted: gen_give_bat.py granted one of every
ingredient the dataset (plus the save's active packs) knows, using
runtime form ids computed from the save's own load order. After the
`bat` ran in-game and the player saved, every one of those forms must
parse back out of the save as the SAME dataset ingredient it was granted
as. Anything that comes back as an unknown form is a pack bug (wrong
plugin name, wrong form id, wrong light/regular assumption).

Usage:
  python scripts/verify_pack_save.py <save2.ess>
      [--baseline <save1.ess>] [--eaten ING_ID ...] [--count N]

  --baseline  the save from BEFORE the bat ran; makes the check a true
              diff (granted = count went up) instead of "count >= 1".
  --eaten     ingredient ids the player ate in-game; each must now show
              slot 0 as known (eating discovers the first effect).
  --count     what gen_give_bat.py was told to grant (default 1).

Exit status 0 = PASS, 1 = FAIL. Every failure is listed by name.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alchemy_helper.data.loader import (load_dataset, load_packs,
                                        packs_for_plugins)
from alchemy_helper.saveparser.api import parse_save
from alchemy_helper.saveparser.body import parse_plugins, read_body
from alchemy_helper.saveparser.header import parse_header


def load_order(save_path: Path):
    data = save_path.read_bytes()
    body = read_body(data, parse_header(data))
    plugin_list, _ = parse_plugins(body)
    return list(plugin_list.plugins), list(plugin_list.light_plugins)


def expected_grants(dataset, regular, light):
    """Mirror gen_give_bat.py's filter exactly: which ingredients it
    could have granted given this load order."""
    reg = {p.lower() for p in regular}
    lit = {p.lower() for p in light}
    granted, skipped = [], []
    for ing in dataset.ingredients.values():
        key = ing.plugin.lower()
        if key in reg:
            granted.append(ing)
        elif key in lit:
            if ing.form_id > 0xFFF:
                skipped.append((ing.id, "form id too wide for light slot"))
            else:
                granted.append(ing)
        else:
            skipped.append((ing.id, f"plugin not in load order: {ing.plugin}"))
    return granted, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("save2", type=Path)
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--eaten", nargs="*", default=[])
    ap.add_argument("--count", type=int, default=1)
    args = ap.parse_args()

    regular, light = load_order(args.save2)
    packs = load_packs()
    active = packs_for_plugins(packs.values(), regular + light)
    dataset = load_dataset(packs=[p.id for p in active])
    print(f"save: {args.save2.name}")
    print(f"load order: {len(regular)} regular + {len(light)} light")
    print(f"packs active: {[p.id for p in active] or 'none'}")
    print(f"dataset: {len(dataset.ingredients)} ingredients, "
          f"{len(dataset.effects)} effects")

    state2 = parse_save(args.save2, dataset)
    state1 = parse_save(args.baseline, dataset) if args.baseline else None
    inv1 = state1.inventory if state1 else {}
    known1 = state1.known_effects if state1 else {}
    if state1:
        print(f"baseline: {args.baseline.name} "
              f"({len(inv1)} ingredient kinds carried before the bat)")

    if not state2.inventory:
        print()
        print('the save carries NO ingredients at all - the give bat did '
              'not run in this save (or you saved before running it). '
              'Nothing to verify yet.')
        return 1

    failures: list[str] = []

    # 1. Every granted form came back as the right ingredient.
    granted, skipped = expected_grants(dataset, regular, light)
    missing, short = [], []
    for ing in granted:
        if ing.id in args.eaten:
            continue  # eating consumes it; the --eaten slot-0 check covers it
        before, after = inv1.get(ing.id, 0), state2.inventory.get(ing.id, 0)
        if after == 0:
            missing.append(ing)
        elif state1 is not None and after < before + args.count:
            short.append((ing, before, after))
    print(f"\ngranted-form round trip: {len(granted) - len(missing)}"
          f"/{len(granted)} resolved back to the right ingredient")
    for ing in missing:
        failures.append(f"MISSING  {ing.id:32s} {ing.plugin} "
                        f"0x{ing.form_id:06X} - granted, not in inventory")
    for ing, b, a in short:
        failures.append(f"SHORT    {ing.id:32s} carried {b} before, {a} "
                        f"after; expected >= {b + args.count}")
    for sid, why in skipped:
        print(f"  (not granted by design: {sid} - {why})")

    # 2. Nothing the parser saw was a form the dataset cannot name.
    if state2.unknown_forms:
        print(f"\nunknown forms: {len(state2.unknown_forms)} "
              f"(each is an ingredient the packs do not name correctly)")
        for uf in state2.unknown_forms:
            failures.append(f"UNKNOWN  {uf.plugin} 0x{uf.form_id:06X} - "
                            f"parsed from the save but not in the dataset")
    else:
        print("\nunknown forms: none")

    # 3. Per-pack breakdown, so a bad pack is named, not just a bad row.
    for pk in active:
        ids = {i.id for i in pk.ingredients}
        ok = sum(1 for i in ids if state2.inventory.get(i, 0) > 0)
        print(f"  pack {pk.id:14s} {ok:4d}/{len(ids):<4d} ingredients "
              f"present in the save")

    # 4. Discovery: newly-known effect slots, and the ones you claim to
    #    have eaten.
    newly = {}
    for iid, slots in state2.known_effects.items():
        new = slots - known1.get(iid, frozenset())
        if new:
            newly[iid] = new
    if newly:
        print(f"\nnewly discovered effect slots since baseline: {len(newly)}")
        for iid, slots in sorted(newly.items()):
            ing = dataset.ingredients.get(iid)
            names = ", ".join(f"slot {s} = {ing.effects[s] if ing else '?'}"
                              for s in sorted(slots))
            print(f"  {iid:32s} {names}")
    for iid in args.eaten:
        if iid not in dataset.ingredients:
            failures.append(f"EATEN?   {iid} is not a dataset ingredient id")
        elif 0 not in state2.known_effects.get(iid, frozenset()):
            failures.append(f"NOTEATEN {iid:32s} slot 0 not known - "
                            f"eating should have discovered it")
        else:
            print(f"  eaten OK: {iid} slot 0 = "
                  f"{dataset.ingredients[iid].effects[0]}")

    print()
    if failures:
        print(f"FAIL - {len(failures)} problem(s):")
        for f in failures:
            print("  " + f)
        return 1
    print(f"PASS - {len(granted)} granted forms round-tripped, "
          f"no unknown forms"
          + (f", {len(args.eaten)} eaten ingredient(s) discovered"
             if args.eaten else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
