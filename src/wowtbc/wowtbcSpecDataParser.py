import json
import traceback

from src.general.idResolver import IdResolver
from src.general.phases import phases
from src.general.sortedSpec import SortedSpec, Item, Slot


class WowtbcSpecDataParser:
    def __init__(self, id_resolver: IdResolver):
        self.id_resolver = id_resolver

    def parse(self, spec_path):
        with open(spec_path) as json_file:
            data = json.load(json_file)
            spec_id = data['result']['pageContext']['spec']
            item_list = data['result']['pageContext']['bisList']
            sorted_spec = SortedSpec(spec_id)
            for item in item_list:
                try:
                    try:
                        item_name = item['name']
                    except Exception as e:
                        print('\tSkipping empty item')
                        continue

                    item_slot_name = item['slot']
                    try:
                        item_value = item['value']
                    except:
                        item_value = 0
                    item_bis_phases = item['phase']
                    for phase in phases:
                        if spec_id == "blood-dps-death-knight" and phase != "T10" and phase != "T10.5":
                            continue
                        phase_data = item.get(phase.lower())
                        if phase_data is not None and "bis" in phase_data and phase_data['bis']:
                            i = Item(self.id_resolver.get_item_id(item_name), item_value, item_name)
                            sorted_spec.add_item(item_slot_name, phase, i, True)

                            ench_data = phase_data.get('enchant')
                            if ench_data is not None:
                                name = ench_data.get('name')
                                if name is not None:
                                    sorted_spec.add_enchant(item_slot_name, phase, self.id_resolver.get_enchant(name))

                            gems_data = phase_data.get('gems')
                            if gems_data is not None:
                                for gem in gems_data:
                                    name = gem.get('name')
                                    if name is not None:
                                        sorted_spec.add_gem(item_slot_name, phase, self.id_resolver.get_gem_id(name))

                        elif phase in item_bis_phases:
                            i = Item(self.id_resolver.get_item_id(item_name), item_value, item_name)
                            sorted_spec.add_item(item_slot_name, phase, i, False)
                except Exception as e:
                    print("failed at: ", spec_id, item_name)
                    traceback.print_exc()
                    pass

            for slot in sorted_spec.slots.values():
                slot: Slot = slot
                for phase in slot.phases:
                    if phase.second_bis is not None:
                        phase.items = list(filter(lambda itemx: itemx.id != phase.second_bis.id, phase.items))
                        phase.items.insert(1, phase.second_bis)

            return sorted_spec
