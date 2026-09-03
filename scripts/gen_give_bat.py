"""Generate a Skyrim console batch file granting one of every ingredient
the dataset (plus the save's active packs) knows, with runtime form ids
computed from the save's own load order - clean-room protocol step 2
(docs/cleanroom-plan.md).

Usage: python scripts/gen_give_bat.py <save.ess> <out.txt> [count]
Then in-game: open console, `bat <out-basename-without-extension>`
(the file goes next to SkyrimSE.exe).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alchemy_helper.data.loader import (load_dataset, load_packs,
                                        packs_for_plugins)
from alchemy_helper.saveparser.body import parse_plugins, read_body
from alchemy_helper.saveparser.header import parse_header


def main(save_path: Path, out_path: Path, count: int = 1):
    data = save_path.read_bytes()
    body = read_body(data, parse_header(data))
    plugin_list, _ = parse_plugins(body)
    regular = {p.lower(): i for i, p in enumerate(plugin_list.plugins)}
    light = {p.lower(): i for i, p in enumerate(plugin_list.light_plugins)}

    packs = load_packs()
    active = packs_for_plugins(
        packs.values(),
        list(plugin_list.plugins) + list(plugin_list.light_plugins))
    dataset = load_dataset(packs=[p.id for p in active])
    print(f"load order: {len(regular)} regular + {len(light)} light; "
          f"packs active: {[p.id for p in active]}")

    lines, skipped = [], []
    for ing in dataset.ingredients.values():
        key = ing.plugin.lower()
        if key in regular:
            fid = (regular[key] << 24) | ing.form_id
        elif key in light:
            if ing.form_id > 0xFFF:
                skipped.append((ing.id, "form id too wide for light slot"))
                continue
            fid = 0xFE000000 | (light[key] << 12) | ing.form_id
        else:
            skipped.append((ing.id, f"plugin not in load order: "
                                    f"{ing.plugin}"))
            continue
        lines.append(f"player.additem {fid:08X} {count}")

    out_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"{len(lines)} additem lines -> {out_path}")
    for s in skipped:
        print("  skipped:", s)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]),
         int(sys.argv[3]) if len(sys.argv) > 3 else 1)
