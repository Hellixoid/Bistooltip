import json
import traceback

from src.general import phases
from src.general.sortedSpec import SortedSpec, Item

# wowtbc.gg warcraftforever slot key -> app canonical slot name.
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
    "trinket": "Trinket",
    "ranged": "Ranged",
    "thrown": "Ranged",
    "main-hand": "Weapon",
    "main hand": "Weapon",
    "one-hand": "Weapon",
    "two-hand": "Weapon",
    "off-hand": "Off hand",
    "off hand": "Off hand",
    "relic": "Relic",
}

# WoW Forever is a single endgame phase; use the level-60 bracket from the caps map.
_CAP = "60"


class WowtbcSpecDataParser:
    """Parses the wowtbc.gg warcraftforever page-data (Classic+ schema): the BiS
    data lives in pageContext.bisList.caps[<level-cap>][<slot>] = [item_id, ...]
    in priority order, so item IDs are used directly (no name resolution)."""

    def parse(self, spec_path):
        with open(spec_path, encoding="utf-8") as json_file:
            data = json.load(json_file)

        pc = data['result']['pageContext']
        spec_id = pc['spec']
        caps = pc['bisList']['caps']
        sorted_spec = SortedSpec(spec_id)
        phase_name = phases.id_to_phase[0]

        cap = caps.get(_CAP)
        if cap is None and caps:
            cap = caps[max(caps, key=lambda k: int(k))]  # fall back to the highest cap
        if not cap:
            return sorted_spec

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
        return sorted_spec
