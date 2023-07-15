from src.general.phases import phases


def validate_slot(slot_name):
    if slot_name == "Finger 1":
        return "Finger"
    if slot_name == "Finger 2":
        return None
    if slot_name == "Trinket 1":
        return "Trinket"
    if slot_name == "Trinket 2":
        return None
    return slot_name


class SortedSpec:
    def __init__(self, spec_id):
        self.id = spec_id
        self.slots = {}

    def add_item(self, slot_name, phase, item, isbis):
        slot_name = slot_name.capitalize()

        if slot_name[-1] == '2' and isbis:
            slot_name = slot_name[:-2]

            slot = self.slots.get(slot_name)
            if slot is None:
                slot = Slot(slot_name)
                self.slots[slot_name] = slot
            slot.add_second_bis(phase, item)
            return

        slot_name = validate_slot(slot_name)
        if slot_name is None:
            return

        slot = self.slots.get(slot_name)
        if slot is None:
            slot = Slot(slot_name)
            self.slots[slot_name] = slot
        slot.add_item(phase, item, isbis)

    def add_gem(self, slot_name, phase, gem_id):
        slot_name = slot_name.capitalize()
        slot_name = validate_slot(slot_name)
        if slot_name is None:
            return

        slot = self.slots.get(slot_name)
        if slot is None:
            slot = Slot(slot_name)
            self.slots[slot_name] = slot
        slot.add_gem(phase, gem_id)

    def add_enchant(self, slot_name, phase, enchantment):
        slot_name = slot_name.capitalize()
        slot_name = validate_slot(slot_name)
        if slot_name is None:
            return

        slot = self.slots.get(slot_name)
        if slot is None:
            slot = Slot(slot_name)
            self.slots[slot_name] = slot
        return slot.add_enchant(phase, enchantment)


class Slot:
    def __init__(self, name):
        self.name = name
        l_phases = []
        for x in phases.keys():
            l_phases.append(Phase(x))
        self.phases = l_phases

    def add_item(self, phase, item, isbis):
        phase_index = phases.get(phase)
        if phase_index is None:
            return

        self.phases[phase_index].add_item(item, isbis)

    def add_second_bis(self, phase, item):
        phase_index = phases.get(phase)
        if phase_index is None:
            return

        self.phases[phase_index].add_second_bis(item)

    def add_gem(self, phase, gem_id):
        phase_index = phases.get(phase)
        if phase_index is None:
            return

        self.phases[phase_index].add_gem(gem_id)

    def add_enchant(self, phase, enchantment):
        phase_index = phases.get(phase)
        if phase_index is None:
            return

        return self.phases[phase_index].add_enchant(enchantment)


class Phase:
    def __init__(self, name):
        self.items = []
        self.second_bis = None
        self.name = name
        self.enhs = []
        self.gems = []

    def add_item(self, item, isbis):
        if item in self.items:
            return
        if isbis:
            self.items.insert(0, item)
        else:
            self.items.append(item)

    def add_second_bis(self, item):
        self.second_bis = item

    def add_gem(self, gem_id):
        self.gems.append({
            "type": "item",
            "id": gem_id
        })

    def add_enchant(self, enchant):
        for i in range(len(self.enhs)):
            if self.enhs[i]["type"] == enchant["type"] and self.enhs[i]["id"] == enchant["id"]:
                return None

        self.enhs.append(enchant)
        return True


class Item:
    def __init__(self, item_id, value, name):
        self.id = item_id
        self.value = value
        self.name = name
