"""Extract a dataset pack from a mod plugin, using our own validated
dataset as the Rosetta stone.

Reads INGR and MGEF records straight out of TES5 SE plugin files. The
vanilla masters (Skyrim.esm + DLC) are aligned against the app's own
ingredient dataset: every vanilla ingredient we already know gives four
(effect form id -> effect slug) pairs, cross-validated over the whole
set, with no dependence on localized string tables. The target plugin's
ingredient records are then translated through that table - overrides of
vanilla records become effect remaps, plugin-own records become new
ingredients, and plugin-own magic effects referenced by any of them
become new pack effects.

Output is a DRAFT pack JSON plus a report; a human verifies against the
in-game alchemy menu before it ships in data/packs/.

Usage:
  python scripts/extract_pack.py <plugin> --game-data <SkyrimSE/Data> \
      --pack-id caco --pack-name "..." --out draft.json
"""
import argparse
import json
import re
import sys
import zlib
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alchemy_helper.data.loader import load_dataset

VANILLA = ("Skyrim.esm", "Update.esm", "Dawnguard.esm",
           "HearthFires.esm", "Dragonborn.esm")
COMPRESSED = 0x00040000
LOCALIZED = 0x00000080
DETRIMENTAL = 0x00000004


def subrecords(data):
    pos, override_size = 0, None
    while pos < len(data):
        stype = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 6], "little")
        pos += 6
        if stype == b"XXXX":
            override_size = int.from_bytes(data[pos:pos + 4], "little")
            pos += 4
            continue
        if override_size is not None:
            size, override_size = override_size, None
        yield stype, data[pos:pos + size]
        pos += size


def zstring(b):
    return b.split(b"\0", 1)[0].decode("cp1252")


class Plugin:
    def __init__(self, path: Path, wanted=(b"INGR", b"MGEF")):
        self.path = path
        self.name = path.name
        data = path.read_bytes()
        if data[:4] != b"TES4":
            raise SystemExit(f"{path}: not a TES4/5 plugin")
        hdr_size = int.from_bytes(data[4:8], "little")
        self.flags = int.from_bytes(data[8:12], "little")
        self.localized = bool(self.flags & LOCALIZED)
        self.masters = [zstring(payload)
                        for stype, payload in subrecords(data[24:24 + hdr_size])
                        if stype == b"MAST"]
        self.records = defaultdict(list)  # rtype -> [(formid_raw, subrecs)]
        pos = 24 + hdr_size
        while pos < len(data):
            if data[pos:pos + 4] != b"GRUP":
                raise SystemExit(f"{path}: expected GRUP at {pos}")
            gsize = int.from_bytes(data[pos + 4:pos + 8], "little")
            label = data[pos + 8:pos + 12]
            if label in wanted:
                self._scan_group(data, pos + 24, pos + gsize)
            pos += gsize

    def _scan_group(self, data, pos, end):
        while pos < end:
            rtype = data[pos:pos + 4]
            dsize = int.from_bytes(data[pos + 4:pos + 8], "little")
            if rtype == b"GRUP":
                pos += dsize  # nested group: dsize is total size
                continue
            rflags = int.from_bytes(data[pos + 8:pos + 12], "little")
            formid = int.from_bytes(data[pos + 12:pos + 16], "little")
            payload = data[pos + 24:pos + 24 + dsize]
            if rflags & COMPRESSED:
                payload = zlib.decompress(payload[4:])
            self.records[rtype.decode()].append(
                (formid, list(subrecords(payload))))
            pos += 24 + dsize

    def resolve(self, formid):
        """Raw form id -> (owner plugin name, local id)."""
        idx = formid >> 24
        if idx == 0xFE:
            raise SystemExit(f"{self.name}: light-master reference "
                             f"{formid:08X} not supported yet")
        if idx >= len(self.masters):        # the plugin's own record
            return self.name, formid & 0xFFFFFF
        return self.masters[idx], formid & 0xFFFFFF


def ingr_entries(plugin):
    """(owner, local_id, full_name_or_None, [effect (owner, local_id)])"""
    for formid, subs in plugin.records["INGR"]:
        owner, local = plugin.resolve(formid)
        full, efids = None, []
        for stype, payload in subs:
            if stype == b"FULL" and not plugin.localized:
                full = zstring(payload)
            elif stype == b"EFID":
                efids.append(plugin.resolve(
                    int.from_bytes(payload[:4], "little")))
        yield owner, local, full, efids


def mgef_entries(plugin):
    for formid, subs in plugin.records["MGEF"]:
        owner, local = plugin.resolve(formid)
        edid, full, desc, flags = None, None, "", 0
        for stype, payload in subs:
            if stype == b"EDID":
                edid = zstring(payload)
            elif stype == b"FULL" and not plugin.localized:
                full = zstring(payload)
            elif stype == b"DNAM" and not plugin.localized:
                desc = zstring(payload)
            elif stype == b"DATA":
                flags = int.from_bytes(payload[:4], "little")
        yield owner, local, edid, full, desc, flags


def edid_to_name(edid):
    """AlchFortifyBlock -> 'Fortify Block'. Editor ids are never
    localized, so they name effects whose display strings live in
    string tables we don't read. Draft quality; flagged for review."""
    e = re.sub(r"^(Alch|Mag|crMag)", "", edid)
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])",
                  " ", e).strip()


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def key(owner, local):
    return (owner.lower(), local)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plugin", type=Path)
    ap.add_argument("--game-data", type=Path, required=True)
    ap.add_argument("--pack-id", required=True)
    ap.add_argument("--pack-name", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    dataset = load_dataset()
    by_form = {key(i.plugin, i.form_id): i
               for i in dataset.ingredients.values()}

    # Rosetta: vanilla effect form id -> our effect slug, cross-validated.
    # Also keep every vanilla MGEF's editor id: effects that no vanilla
    # ingredient uses (spell effects a mod newly ingredient-izes) get
    # draft names from their EDIDs.
    rosetta = {}
    conflicts = []
    vanilla_mgefs = {}
    matched_vanilla = 0
    for esm in VANILLA:
        path = args.game_data / esm
        if not path.exists():
            print(f"note: {esm} not found, skipping")
            continue
        plugin = Plugin(path)
        for owner, local, edid, _full, _desc, flags in mgef_entries(plugin):
            if edid:
                vanilla_mgefs[key(owner, local)] = (edid, flags)
        for owner, local, _full, efids in ingr_entries(plugin):
            known = by_form.get(key(owner, local))
            if known is None or len(efids) != 4:
                continue
            matched_vanilla += 1
            for (eowner, elocal), slug in zip(efids, known.effects):
                k = key(eowner, elocal)
                if rosetta.get(k, slug) != slug:
                    conflicts.append((k, rosetta[k], slug, known.id))
                rosetta[k] = slug
    print(f"rosetta: {len(rosetta)} effect form ids from "
          f"{matched_vanilla} vanilla ingredient records; "
          f"{len(conflicts)} conflicts; {len(vanilla_mgefs)} vanilla "
          f"MGEF editor ids held in reserve")
    if conflicts:
        for c in conflicts[:10]:
            print("  CONFLICT:", c)
        raise SystemExit("rosetta inconsistent - slot-order assumption broken")

    target = Plugin(args.plugin)
    if target.localized:
        raise SystemExit(f"{target.name} is localized - names unavailable")
    print(f"{target.name}: masters={target.masters}")
    print(f"  INGR records: {len(target.records['INGR'])}, "
          f"MGEF records: {len(target.records['MGEF'])}")

    own_mgefs = {key(o, l): (full, desc, flags)
                 for o, l, _e, full, desc, flags in mgef_entries(target)
                 if o.lower() == target.name.lower()}

    new_effects = {}       # slug -> Effect dict
    used_slugs = set(dataset.effects)
    edid_named = []        # slugs whose names came from editor ids

    def add_effect(name, desc, flags, from_edid=False):
        slug = slugify(name)
        while slug in used_slugs and slug not in new_effects:
            slug += "-" + args.pack_id
        if slug not in new_effects:
            new_effects[slug] = {
                "id": slug, "name": name, "description": desc,
                "harmful": bool(flags & DETRIMENTAL)}
            used_slugs.add(slug)
            if from_edid:
                edid_named.append(slug)
        return slug

    def translate(eowner, elocal, context):
        k = key(eowner, elocal)
        if k in rosetta:
            return rosetta[k]
        if k in own_mgefs:
            full, desc, flags = own_mgefs[k]
            if full is None:
                unresolved.append((context, k, "own MGEF without name"))
                return None
            rosetta[k] = add_effect(full, desc, flags)
            return rosetta[k]
        if k in vanilla_mgefs:
            # A vanilla spell effect no vanilla ingredient carries; its
            # display name lives in localized string tables, so draft
            # the name from the editor id and flag it for review.
            edid, flags = vanilla_mgefs[k]
            rosetta[k] = add_effect(edid_to_name(edid), "", flags,
                                    from_edid=True)
            return rosetta[k]
        unresolved.append((context, k, "unknown effect form"))
        return None

    overrides, additions, unresolved, skipped = [], [], [], []
    for owner, local, full, efids in ingr_entries(target):
        if len(efids) != 4:
            skipped.append((owner, local, full, f"{len(efids)} effects"))
            continue
        is_own = owner.lower() == target.name.lower()
        base = by_form.get(key(owner, local))
        slugs = [translate(o, l, full or (base.id if base else f"{local:X}"))
                 for o, l in efids]
        if any(s is None for s in slugs):
            continue
        if base is not None:
            if tuple(slugs) == base.effects:
                continue  # override doesn't change effects; not pack-worthy
            overrides.append({
                "id": base.id, "name": base.name, "plugin": base.plugin,
                "form_id": base.form_id, "effects": slugs})
        else:
            # The record is the plugin's own, or injected into a master
            # (a record the master never shipped - saves still reference
            # it under the master's name). Either way: a new ingredient.
            if not full:
                skipped.append((owner, local, full, "no name"))
                continue
            entry = {"id": slugify(full), "name": full, "plugin": owner,
                     "form_id": local, "effects": slugs}
            if not is_own:
                entry["_injected"] = True
            additions.append(entry)

    # duplicate addition ids (same name twice) get form-id suffixes
    seen = defaultdict(int)
    for a in additions:
        seen[a["id"]] += 1
    for a in additions:
        if seen[a["id"]] > 1 or a["id"] in dataset.ingredients:
            a["id"] = f"{a['id']}-{a['form_id']:x}"

    pack = {
        "id": args.pack_id,
        "name": args.pack_name,
        "_source": (f"Extracted from {target.name} by scripts/"
                    f"extract_pack.py; DRAFT pending human verification."),
        "plugins": [target.name],
        # extend is the stricter contract (collisions error instead of
        # replacing); only claim overhaul when the plugin actually
        # overrides vanilla ingredient records.
        "mode": "overhaul" if overrides else "extend",
        "effects": sorted(new_effects.values(), key=lambda e: e["id"]),
        "ingredients": sorted(overrides + additions,
                              key=lambda i: i["id"]),
    }
    args.out.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    print(f"\npack draft -> {args.out}")
    print(f"  vanilla overrides with remapped effects: {len(overrides)}")
    print(f"  new ingredients: {len(additions)} "
          f"({sum(1 for a in additions if a.get('_injected'))} injected "
          f"into masters)")
    print(f"  new effects: {len(new_effects)}")
    print(f"  effect names drafted from editor ids (REVIEW): "
          f"{sorted(edid_named)}")
    print(f"  skipped: {len(skipped)}, unresolved effect refs: "
          f"{len(unresolved)}")
    for s in skipped[:8]:
        print("   skip:", s)
    for u in unresolved[:8]:
        print("   unresolved:", u)


if __name__ == "__main__":
    main()
