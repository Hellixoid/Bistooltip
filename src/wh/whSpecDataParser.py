import os
import re

from bs4 import BeautifulSoup

from src.general import phases
from src import dirsAndFiles
from src.general.sortedSpec import SortedSpec, Item

_ITEM_RE = re.compile(r'item=(\d+)')
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
    """Parses the Wowhead WoW Forever BiS pages (markup-table layout): for each
    slot a heading 'Best in Slot <Slot> for <Spec>...' is followed by a table of
    ranked items. Items are read straight from the item=<id> hrefs; the first
    ranked row is BiS. The Forever pages carry no enchant/gem data."""

    def parse(self, spec_id):
        sorted_spec = SortedSpec(spec_id)
        for phase_id in phases.phases.values():
            file_path = os.path.join(dirsAndFiles.wh_spec_data_dir, spec_id + "." + str(phase_id))
            with open(file_path, "r", encoding="utf-8") as html_file:
                soup = BeautifulSoup(html_file.read(), 'html.parser')
                doc = soup.find("div", {"id": "guide-body"})
                self.extract_spec_data(doc, phases.id_to_phase[phase_id], sorted_spec)
        return sorted_spec

    def extract_spec_data(self, doc, phase_name, sorted_spec):
        if doc is None:
            return
        current_slot = None
        for el in doc.find_all(['h3', 'table']):
            if el.name == 'h3':
                m = _SLOT_RE.search(el.get_text())
                current_slot = _map_slot(m.group(1) if m else el.get_text())
            elif el.name == 'table' and current_slot is not None:
                self.parse_table(el, current_slot, phase_name, sorted_spec)
                current_slot = None

    def parse_table(self, table, slot_name, phase_name, sorted_spec):
        is_bis = True
        for row in table.find_all('tr'):
            link = row.find('a', href=_ITEM_RE)
            if link is None:
                continue  # header / rows without an item link
            item_id = int(_ITEM_RE.search(link['href']).group(1))
            sorted_spec.add_item(slot_name, phase_name, Item(item_id, 0, None), is_bis)
            is_bis = False
