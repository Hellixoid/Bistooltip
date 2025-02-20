import json
import os
import re

import bs4

from src.general import phases
from src import dirsAndFiles
from bs4 import BeautifulSoup

from src.general.randomItemSuffixes import find_suffix
from src.general.sortedSpec import SortedSpec, Item
from src.wh import whSlots


class WhSpecDataParser:

    def __init__(self, consumables_file_path, ench_spells_file_path, horde_to_ali_file_path):
        self.ench_items_id_set = set()
        self.ench_spells_id_set = set()

        self.fill_enchantment_id_set(self.ench_items_id_set, consumables_file_path)
        self.fill_enchantment_id_set(self.ench_spells_id_set, ench_spells_file_path)
        with open(horde_to_ali_file_path) as json_file:
            self.horde_to_ali_dict = json.load(json_file)
        pass

    def fill_enchantment_id_set(self, id_set: set, data_file_path):
        with open(data_file_path) as json_file:
            data = json.load(json_file)
            for item in data:
                item_id = int(item.get('entry'))
                id_set.add(item_id)

    def parse(self, spec_id):
        sorted_spec = SortedSpec(spec_id)
        for phase_id in phases.phases.values():
            file_path = os.path.join(dirsAndFiles.wh_spec_data_dir, spec_id + "." + str(phase_id))
            with open(file_path, "r", encoding="utf-8") as html_file:
                soup = BeautifulSoup(html_file.read(), 'html.parser')
                doc = soup.find("div", {"id": "guide-body"})

                self.extract_spec_data(doc, phase_id, sorted_spec, spec_id)

        return sorted_spec

    def extract_spec_data(self, doc, phase_id, sorted_spec, spec_id):
        if phase_id == phases.phases.get("Pre-Bis-workaround"):
            tbody_tag = doc.findNext("tbody")
            self.parse_pr_table(tbody_tag, phase_id, sorted_spec, spec_id)
        else:
            h4_tags = doc.findChildren(["h4", "h3"])
            for h4_tag in h4_tags:
                tag_text = h4_tag.text.strip()
                slot_name = self.normalize_slot_name(self.parse_slot(tag_text), spec_id)
                if slot_name is not None:
                    print(slot_name)
                    notable = self.check_no_table_in_block(h4_tag)
                    if not notable:
                        tbody_tag = h4_tag.findNext("tbody")
                        self.parse_table(tbody_tag, slot_name, phase_id, sorted_spec)
                        self.find_ench(h4_tag, slot_name, phase_id, sorted_spec)

    def parse_table(self, tbody_tag, slot_name, phase_id, sorted_spec):
        tr_tags = tbody_tag.findChildren("tr")
        tr_tags_list = self.rs_to_list(tr_tags)
        header_columns = self.parse_header(tr_tags_list[0])
        for i in range(1, len(tr_tags_list)):

            row = tr_tags_list[i]
            columns = self.rs_to_list(row.findChildren("td"))

            item_column = columns[header_columns.get("Item")]
            item_links = item_column.findChildren("a", href=True)
            item_id = None
            for item_link in item_links:
                try:
                    item_id = self.get_item_id(item_link)
                    suffix = find_suffix(item_column.text)

                    sorted_spec.add_item(slot_name,
                                         phases.id_to_phase[phase_id],
                                         Item(item_id, 0, None, suffix[1]),
                                         False)
                except Exception as e:
                    continue
                break
            if item_id is None:
                print("Failed to parse item for phase " + str(phase_id) + " slot " + str(slot_name))
            if i == 1 and "Sockets" in header_columns:
                sockets_column = columns[header_columns.get("Sockets")]
                item_links = sockets_column.findChildren("a", href=True)
                for link in item_links:
                    gem_id = self.get_item_id(link)
                    sorted_spec.add_gem(slot_name, phases.id_to_phase[phase_id], gem_id)

    def parse_pr_table(self, tbody_tag, phase_id, sorted_spec, spec_id):
        tr_tags = tbody_tag.findChildren("tr")
        tr_tags_list = self.rs_to_list(tr_tags)
        header_columns = self.parse_header(tr_tags_list[0])
        is_no_header_table = False
        while not "Slot" in header_columns:
            if len(header_columns.keys()) == 0 and spec_id in ["demonology-warlock", "destruction-warlock"]:
                header_columns = {
                    "Slot": 0,
                    "Item": 1,
                    "Gems": 2,
                    "Enchant": 3,
                    "Source": 4
                }
                is_no_header_table = True
                break
            tbody_tag = tbody_tag.findNext("tbody")
            tr_tags = tbody_tag.findChildren("tr")
            tr_tags_list = self.rs_to_list(tr_tags)
            header_columns = self.parse_header(tr_tags_list[0])

        for i in range(0 if is_no_header_table else 1, len(tr_tags_list)):

            row = tr_tags_list[i]
            columns = self.rs_to_list(row.findChildren("td"))
            slot_name = self.normalize_slot_name(columns[header_columns.get("Slot")].text, spec_id)
            item_column = columns[header_columns.get("Item")]
            item_link = item_column.find("a", href=True)
            item_id = self.get_item_id(item_link)
            sorted_spec.add_item(slot_name, phases.id_to_phase[phase_id], Item(item_id, 0, None), False)

            if "Gems" in header_columns:
                sockets_column = columns[header_columns.get("Gems")]
                item_links = sockets_column.findChildren("a", href=True)
                for link in item_links:
                    gem_id = self.get_item_id(link)
                    sorted_spec.add_gem(slot_name, phases.id_to_phase[phase_id], gem_id)
            if "Enchant" in header_columns:
                self.find_ench(columns[header_columns.get("Enchant")], slot_name, phase_id, sorted_spec, True)
        pass

    def parse_header(self, header):
        header_dict = dict()
        b_tags = header.findChildren("b")
        index = 0
        for tag in b_tags:
            header_dict[tag.text] = index
            index += 1
        pass
        return header_dict

    def check_no_table_in_block(self, block):
        no_table = True
        next_node = block
        while True:
            next_node = next_node.nextSibling
            if next_node is None:
                return no_table
            tag_name = next_node.name
            if tag_name == "h4" or tag_name == "h3":
                break
            elif tag_name == "table":
                no_table = False
                break
            elif tag_name == "div":
                if "markup-table-wrapper" in next_node.attrs['class']:
                    no_table = False
                    break
                children = next_node.findChildren("table", True)
                if len(children) > 0:
                    no_table = False
                    break
        return no_table

    def rs_to_list(self, result_set):
        result_list = list()
        for elem in result_set:
            result_list.append(elem)

        return result_list

    def get_item_id(self, link):
        group = re.search(r".+=i?(\d+){1}(/{1}.+)?", link["href"]).group(1)
        item_id = int(group)
        if str(item_id) in self.horde_to_ali_dict:
            return int(self.horde_to_ali_dict[str(item_id)])
        return item_id

    def get_ench(self, link):
        groups = re.search(r".+(spell|item)=i?(\d+){1}(/{1}.+)?", link["href"])
        if groups is None:
            return None
        return (groups[1], groups[2])

    def parse_slot(self, text):
        if " options for " in text:
            return text[:text.index(" options for ")]
        if " for " in text:
            return text[:text.index(" for ")]
        return text

    def normalize_slot_name(self, slot, spec_id):
        slot = slot.lower()
        if slot in whSlots.spec_to_slots.get(spec_id):
            return whSlots.spec_to_slots.get(spec_id).get(slot)
        if slot in whSlots.slot_to_slot_name:
            return whSlots.slot_to_slot_name[slot]
        print(slot)
        return None

    def find_ench(self, tag: bs4.element.Tag, slot_name, phase_id, sorted_spec: SortedSpec, lookup_only_child=False):
        tags = []
        if not lookup_only_child:
            tags = tag.findAllNext(["h3", "h4", "script", "a"])
        else:
            tags = tag.findChildren("a")

        self.find_ench_in_tags(tags, slot_name, phase_id, sorted_spec)
        return

    def find_ench_in_tags(self, tags, slot_name, phase_id, sorted_spec: SortedSpec):
        counter = 0
        for tag in tags:
            tag_name = tag.name
            if tag_name == "h4" or tag_name == "h3" or tag_name == "script":
                return
            elif tag_name == "a":
                ench = self.get_ench(tag)
                if ench is not None:
                    if ench[0] == "item":
                        if int(ench[1]) in self.ench_items_id_set:
                            added = sorted_spec.add_enchant(slot_name, phases.id_to_phase[phase_id],
                                                            {"id": int(ench[1]), "type": ench[0]})
                            if added is True:
                                counter = counter + 1
                            if counter == 3:
                                return
                    elif ench[0] == "spell":
                        if int(ench[1]) in self.ench_spells_id_set:
                            added = sorted_spec.add_enchant(slot_name, phases.id_to_phase[phase_id],
                                                            {"id": int(ench[1]), "type": ench[0]})
                            if added is True:
                                counter = counter + 1
                            if counter == 3:
                                return
