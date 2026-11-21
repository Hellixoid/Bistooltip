import json
import traceback

from src.general import phases
from src.general.sortedSpec import SortedSpec, Item

# wowtbc.gg warcraftforever "gear"/enchant slot key -> app canonical slot name.
# The pre-raid gear list splits the two rings/trinkets ("finger 1"/"finger 2",
# "trinket 1"/"trinket 2"); the addon's add_item logic keys off those names to
# pick the primary item and the second-bis ring/trinket.
_SLOT_MAP = {
    "head": "Head",
    "neck": "Neck",
    "shoulder": "Shoulder",
    "back": "Back",
    "chest": "Chest",
    "wrist": "Wrist",
    "hands": "Hands",
    "waist": "Waist",
    "legs": "Legs",
    "feet": "Feet",
    "finger": "Finger",
    "finger 1": "Finger 1",
    "finger 2": "Finger 2",
    "trinket": "Trinket",
    "trinket 1": "Trinket 1",
    "trinket 2": "Trinket 2",
    "ranged": "Ranged",
    "thrown": "Ranged",
    "weapon": "Weapon",
    "main-hand": "Weapon",
    "main hand": "Weapon",
    "one-hand": "Weapon",
    "two-hand": "Weapon",
    "off-hand": "Off hand",
    "off hand": "Off hand",
    "relic": "Relic",
}

# WoW Forever is a single endgame phase; the caps map's level-60 bracket is the
# fallback item source when a spec has no pre-raid gear list.
_CAP = "60"


class WowtbcSpecDataParser:
    """Parses the wowtbc.gg warcraftforever page-data (Classic+ schema).

    Items: pageContext.bisList['pre-raid'].gear[<slot>] = [{id, name,
    alternative}, ...]. This is the list the site shows by default (the first
    entry, alternative=False, is the BiS pick and the rest are alternatives in
    priority order), and it splits the two rings/trinkets into finger 1/finger 2
    and trinket 1/trinket 2. Item ids are used directly (no name resolution).
    If a spec has no pre-raid gear list, the caps[<level-cap>] bracket lists are
    used as a fallback.

    Enchants: pageContext.bisList['pre-raid'].enchants[<slot>] = {id, name}. The
    id is the enchant spell id (the client renders it via SetSpellByID), so it
    is emitted as a type="spell" enhancement, like the wowhead source.

    Both items and enchants come from the single 'pre-raid' section (falling
    back to 'pre-raid-realistic' if pre-raid is absent); there is no per-cap
    enchant set."""

    def parse(self, spec_path):
        with open(spec_path, encoding="utf-8") as json_file:
            data = json.load(json_file)

        pc = data['result']['pageContext']
        spec_id = pc['spec']
        bis = pc['bisList']
        sorted_spec = SortedSpec(spec_id)
        phase_name = phases.id_to_phase[0]

        section = bis.get('pre-raid') or bis.get('pre-raid-realistic') or {}
        gear = section.get('gear')
        if isinstance(gear, dict) and gear:
            self._parse_gear(gear, spec_id, phase_name, sorted_spec)
        else:
            self._parse_caps(bis.get('caps') or {}, spec_id, phase_name, sorted_spec)

        self._parse_enchants(section, spec_id, phase_name, sorted_spec)
        return sorted_spec

    def _parse_gear(self, gear, spec_id, phase_name, sorted_spec):
        for raw_slot, items in gear.items():
            slot_name = _SLOT_MAP.get(str(raw_slot).lower())
            if slot_name is None or not isinstance(items, list):
                continue
            for i, item in enumerate(items):
                item_id = item.get('id') if isinstance(item, dict) else item
                if item_id is None:
                    continue
                try:
                    sorted_spec.add_item(slot_name, phase_name, Item(int(item_id), 0, None), i == 0)
                except Exception:
                    print("failed at:", spec_id, raw_slot, item)
                    traceback.print_exc()

    def _parse_caps(self, caps, spec_id, phase_name, sorted_spec):
        cap = caps.get(_CAP)
        if cap is None and caps:
            cap = caps[max(caps, key=lambda k: int(k))]  # fall back to the highest cap
        if not cap:
            return
        for raw_slot, item_ids in cap.items():
            slot_name = _SLOT_MAP.get(str(raw_slot).lower())
            if slot_name is None:
                continue
            for i, item_id in enumerate(item_ids):
                try:
                    sorted_spec.add_item(slot_name, phase_name, Item(int(item_id), 0, None), i == 0)
                except Exception:
                    print("failed at:", spec_id, raw_slot, item_id)
                    traceback.print_exc()

    def _parse_enchants(self, section, spec_id, phase_name, sorted_spec):
        enchants = section.get('enchants') or {}
        for raw_slot, ench in enchants.items():
            slot_name = _SLOT_MAP.get(str(raw_slot).lower())
            if slot_name is None or not isinstance(ench, dict):
                continue
            ench_id = ench.get('id')
            if ench_id is None:
                continue
            try:
                sorted_spec.add_enchant(slot_name, phase_name, {"type": "spell", "id": int(ench_id)})
            except Exception:
                print("failed enchant at:", spec_id, raw_slot, ench)
                traceback.print_exc()
