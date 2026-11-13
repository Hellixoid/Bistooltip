"""Build the BiS-Tooltip item/enchant reference DBs from a WoW Forever install.

Reads the client's CASC storage directly (no external tools) and regenerates:

    data/items/list.json                 equippable items  {entry, name, ItemLevel, InventoryType}
    data/items/consumablesAndQuest.json  non-equippable    {entry, name}
    data/items/ench_spells.json          permanent enchants {entry, name}

Gems are intentionally skipped (WoW Forever has none).

Fully scriptable / re-runnable: point it at the install and run. Nothing is
cached or manual.

    python -m forever.buildForeverDb                         # from src/, default install path
    python src/forever/buildForeverDb.py --base "D:\\bnet\\World of Warcraft"
"""

from __future__ import annotations

import argparse
import json
import os

from . import casc, dbd, wdc5

# FileDataIDs (stable per path across builds; from the community listfile).
FDID_ITEMSPARSE = 1572924
FDID_SPELLNAME = 1990283
FDID_SPELLEFFECT = 1140088

DEFAULT_BASE = r"D:\bnet\World of Warcraft"
DEFAULT_PRODUCT = "wowf"

# SpellEffect.Effect values that apply a *permanent* item enchantment.
ENCHANT_EFFECTS = {53}  # SPELL_EFFECT_ENCHANT_ITEM

_DEFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defs")
# repo_root/data/items  (src/forever/buildForeverDb.py -> up 3)
_DEFAULT_OUT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "items"))

# Obvious non-player placeholder/test enchant names to drop (keeps name
# collisions down; items are left unfiltered to match the existing data).
_ENCH_JUNK = ("DONOTREUSE", "[PH]", "(TEST)", "QAENCHANT", "QA TEST", "TEST)",
              "DEPRECATED", "(OLD)", "UNUSED", "NYI", "PH]", "OLDENCHANT")


def _load_table(build: casc.Build, fdid: int, def_name: str) -> list[dict]:
    """Extract a DB2 from CASC and decode it with its vendored .dbd schema."""
    table = wdc5.read(build.open_by_fdid(fdid))
    with open(os.path.join(_DEFS_DIR, def_name + ".dbd"), encoding="utf-8") as f:
        defn = dbd.parse(f.read())
    version = dbd.select(defn, table.layout_hash, build.build_number)
    return wdc5.decode(table, version, defn.column_definitions)


def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _clean_ench_name(name: str) -> str:
    for prefix in ("Enchant: ", "Enchant "):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _is_junk_ench(name: str) -> bool:
    upper = name.upper()
    if upper.startswith("QA"):
        return True
    return any(tok in upper for tok in _ENCH_JUNK)


def build_items(build: casc.Build, out_dir: str) -> tuple[int, int]:
    rows = _load_table(build, FDID_ITEMSPARSE, "ItemSparse")
    items, cons = [], []
    for r in rows:
        name = r.get("Display_lang") or ""
        if not name:
            continue
        entry = r["ID"]
        inv = r.get("InventoryType", 0)
        if inv != 0:
            items.append({"entry": entry, "name": name,
                          "ItemLevel": r.get("ItemLevel", 0), "InventoryType": inv})
        else:
            cons.append({"entry": entry, "name": name})
    items.sort(key=lambda x: x["entry"])
    cons.sort(key=lambda x: x["entry"])
    _write_json(os.path.join(out_dir, "list.json"), items)
    _write_json(os.path.join(out_dir, "consumablesAndQuest.json"), cons)
    return len(items), len(cons)


def build_enchants(build: casc.Build, out_dir: str) -> int:
    effects = _load_table(build, FDID_SPELLEFFECT, "SpellEffect")
    names = _load_table(build, FDID_SPELLNAME, "SpellName")
    name_by_id = {r["ID"]: (r.get("Name_lang") or "") for r in names}

    spell_ids = sorted({r["SpellID"] for r in effects if r.get("Effect") in ENCHANT_EFFECTS})
    out = []
    for sid in spell_ids:
        raw = name_by_id.get(sid)
        if not raw or _is_junk_ench(raw):
            continue
        out.append({"entry": sid, "name": _clean_ench_name(raw)})
    out.sort(key=lambda x: x["entry"])
    _write_json(os.path.join(out_dir, "ench_spells.json"), out)
    return len(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build BiS-Tooltip DBs from a WoW Forever install.")
    ap.add_argument("--base", default=DEFAULT_BASE,
                    help=r"WoW install root (contains .build.info and Data\). "
                         f"Default: {DEFAULT_BASE}")
    ap.add_argument("--product", default=DEFAULT_PRODUCT,
                    help=f"Product tag in .build.info. Default: {DEFAULT_PRODUCT}")
    ap.add_argument("--out", default=_DEFAULT_OUT,
                    help=f"Output directory for the JSON files. Default: {_DEFAULT_OUT}")
    args = ap.parse_args(argv)

    print(f"Opening {args.product} at {args.base} ...")
    build = casc.Build(args.base, args.product)
    print(f"  build {build.entry.version}")

    n_items, n_cons = build_items(build, args.out)
    print(f"  list.json                : {n_items} equippable items")
    print(f"  consumablesAndQuest.json : {n_cons} non-equippable items")

    n_ench = build_enchants(build, args.out)
    print(f"  ench_spells.json         : {n_ench} permanent enchants")

    print(f"Done -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
