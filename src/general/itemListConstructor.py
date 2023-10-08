import json

from src.general import phases, cleaner
from src.general.bisItem import BisItem
from src.general.sortedSpec import SortedSpec, Slot
from src.general import specs


class ItemListConstructor:
    def __init__(self, source_name):
        self.source_name = source_name
        self.item_list = {}

    def add_bis_statement(self, item_id, spec_id, slot_name, phase_name, ordinal):
        if item_id == -2:
            return
        if ordinal == "-":
            return
        ordinal = int(ordinal)

        item = self.item_list.get(item_id)
        if item is None:
            item = BisItem(item_id, self.source_name)
            self.item_list[item_id] = item
        item.add_bis_statement(spec_id, slot_name, phase_name, ordinal)

    def add_sorted_spec(self, spec: SortedSpec):
        for slot in spec.slots.values():
            slot: Slot = slot
            for phase in slot.phases:
                for i in range(min(len(phase.items), 9)):
                    item = phase.items[i]
                    if item.id < 0:
                        print("Item without ID: " + item.name)
                    self.add_bis_statement(item.id, spec.id, slot.name, phase.name, i + 1)

    def add_tokens(self, tokens_file_path):
        with open(tokens_file_path) as json_file:
            data = json.load(json_file)
            for tokenId in data:
                items = data[tokenId]
                for itemId in items:
                    bis_item = self.item_list.get(int(itemId))
                    if bis_item is None:
                        continue
                    for spec_id in bis_item.specs:
                        spec = bis_item.specs[spec_id]
                        for slot_name in spec.slots:
                            slot = spec.slots[slot_name]
                            for i in range(len(phases.phases.keys())):
                                self.add_bis_statement(
                                    int(tokenId), spec_id, slot_name, phases.id_to_phase[i], slot.phases[i])

    def add_horde_ali_mapping(self, horde_to_ali_file_path):
        with open(horde_to_ali_file_path) as json_file:
            data = json.load(json_file)
            for hordeId in data:
                aliId = data[hordeId]
                bis_item = self.item_list.get(int(aliId))
                if bis_item is None:
                    continue
                for spec_id in bis_item.specs:
                    spec = bis_item.specs[spec_id]
                    for slot_name in spec.slots:
                        slot = spec.slots[slot_name]
                        for i in range(len(phases.phases.keys())):
                            self.add_bis_statement(
                                int(hordeId), spec_id, slot_name, phases.id_to_phase[i], slot.phases[i])

    def save_data(self, addon_data_file, source_name):
        with open(addon_data_file, 'w') as file:
            file.write('Bistooltip_' + source_name + '_items = {};\n')
            for item in self.item_list.values():
                item.sort_specs()
                file.write(str(item))
                file.write('\n')

    def save_csv(self, source_name):
        path = "../" + source_name + "_items.csv"
        cleaner.delete_file(path)
        phase_index = 3
        with open(path, 'w') as file:
            for item in self.item_list.values():
                for spec in item.specs.values():
                    for slot in spec.slots.values():
                        if slot.phases[phase_index] != "-":
                            file.write(str(item.id) + ","
                                       + str(specs.spec_to_class[spec.spec_id]) + ","
                                       + str(specs.spec_to_spec_name[spec.spec_id]) + ","
                                       + str(slot.name) + ","
                                       + str(slot.phases[phase_index]) + "\n")
