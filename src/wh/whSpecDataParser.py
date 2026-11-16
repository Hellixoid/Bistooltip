import os
import re

from bs4 import BeautifulSoup

from src.general import phases
from src import dirsAndFiles
from src.general.sortedSpec import SortedSpec, Item
from src.wh import whSlots

_ITEM_RE = re.compile(r'item=(\d+)')
_SPELL_RE = re.compile(r'spell=(\d+)')
_SLOT_RE = re.compile(r'Best in Slot\s+(.*?)\s+for\b', re.IGNORECASE)


def _map_slot(label: str):
    """Map a Wowhead BiS heading label (e.g. 'Head Armor', 'Ring Jewelry',
    'One-Handed Weapons', 'Shields') to the app's canonical slot name."""
    l = label.lower()
    if 'head' in l or 'helm' in l:
        return 'Head'
    if 'neck' in l:
        return 'Neck'
    if 'shoulder' in l:
        return 'Shoulder'
    if 'back' in l or 'cloak' in l:
        return 'Back'
    if 'chest' in l:
        return 'Chest'
    if 'wrist' in l or 'bracer' in l:
        return 'Wrist'
    if 'hand armor' in l or 'glove' in l or l.strip() == 'hands':
        return 'Hands'
    if 'waist' in l or 'belt' in l:
        return 'Waist'
    if 'leg' in l:
        return 'Legs'
    if 'feet' in l or 'boot' in l:
        return 'Feet'
    if 'ring' in l or 'finger' in l:
        return 'Finger'
    if 'trinket' in l:
        return 'Trinket'
    if 'shield' in l or 'off-hand' in l or 'off hand' in l or 'offhand' in l:
        return 'Off hand'
    if 'ranged' in l or 'wand' in l or 'bow' in l or 'gun' in l or 'thrown' in l:
        return 'Ranged'
    if 'relic' in l or 'idol' in l or 'totem' in l or 'libram' in l or 'sigil' in l:
        return 'Relic'
    if ('weapon' in l or 'one-hand' in l or 'two-hand' in l or 'one hand' in l
            or 'two hand' in l or 'main hand' in l or 'main-hand' in l or '1h' in l or '2h' in l):
        return 'Weapon'
    return None


class WhSpecDataParser:
    """Parses the Wowhead WoW Forever BiS pages.

    Two sources of data live on the page:

    * The per-slot markup tables ('Best in Slot <Slot> for <Spec>' headings
      followed by a ranked item table). When a guide is filled these give a
      ranked list of items per slot and are the preferred source.
    * The interactive gear-planner widget (``div.wow-gear-slot`` with a
      ``data-slot-id`` and an ``item=`` link, plus a ``spell=`` enchant link).
      Many Forever guides leave the tables as empty '-' placeholders, so the
      planner is used as a per-slot fallback for items.

    Items: table first, gear planner as fallback for any slot the tables leave
    empty. Enchants: always taken from the gear planner (its enchant links are
    spell ids the client can render directly)."""

    def parse(self, spec_id):
        sorted_spec = SortedSpec(spec_id)
        for phase_id in phases.phases.values():
            file_path = os.path.join(dirsAndFiles.wh_spec_data_dir, spec_id + "." + str(phase_id))
            with open(file_path, "r", encoding="utf-8") as html_file:
                soup = BeautifulSoup(html_file.read(), 'html.parser')
                doc = soup.find("div", {"id": "guide-body"}) or soup
                self.extract_spec_data(doc, phases.id_to_phase[phase_id], sorted_spec)
        return sorted_spec

    def extract_spec_data(self, doc, phase_name, sorted_spec):
        if doc is None:
            return

        table_items = self._parse_tables(doc)            # slot -> [item_id, ...] (ranked)
        gp_items, gp_enchants = self._parse_gear_planner(doc)  # slot -> [item_id]; slot -> [spell_id]

        # Items: tables are primary; the gear planner fills slots the tables leave empty.
        for slot_name in list(table_items.keys()) + [s for s in gp_items if s not in table_items]:
            ids = table_items.get(slot_name) or gp_items.get(slot_name) or []
            for i, item_id in enumerate(ids):
                sorted_spec.add_item(slot_name, phase_name, Item(item_id, 0, None), i == 0)

        # Enchants: always from the gear planner.
        for slot_name, spell_ids in gp_enchants.items():
            for spell_id in spell_ids:
                sorted_spec.add_enchant(slot_name, phase_name, {"type": "spell", "id": spell_id})

    def _parse_tables(self, doc):
        """Read the 'Best in Slot ...' heading + table layout into
        slot_name -> ranked [item_id, ...]. Slots whose table has no item links
        (the '-' placeholders) simply do not appear."""
        result = {}
        current_slot = None
        for el in doc.find_all(['h3', 'table']):
            if el.name == 'h3':
                m = _SLOT_RE.search(el.get_text())
                current_slot = _map_slot(m.group(1) if m else el.get_text())
            elif el.name == 'table' and current_slot is not None:
                for row in el.find_all('tr'):
                    link = row.find('a', href=_ITEM_RE)
                    if link is None:
                        continue  # header / '-' rows without an item link
                    item_id = int(_ITEM_RE.search(link['href']).group(1))
                    bucket = result.setdefault(current_slot, [])
                    if item_id not in bucket:
                        bucket.append(item_id)
                current_slot = None
        return result

    def _parse_gear_planner(self, doc):
        """Read the gear-planner widget into slot_name -> [item_id] and
        slot_name -> [enchant spell_id], in slot order."""
        items = {}
        enchants = {}
        for slot_div in doc.find_all('div', class_='wow-gear-slot'):
            slot_name = whSlots.gear_planner_slots.get(str(slot_div.get('data-slot-id')))
            if slot_name is None:
                continue
            link = slot_div.find('a', href=_ITEM_RE)
            if link is not None:
                item_id = int(_ITEM_RE.search(link['href']).group(1))
                items.setdefault(slot_name, []).append(item_id)
            for ench_a in slot_div.select('div.wow-gear-slot-enchant a[href*="spell="]'):
                m = _SPELL_RE.search(ench_a['href'])
                if m:
                    enchants.setdefault(slot_name, []).append(int(m.group(1)))
        return items, enchants
