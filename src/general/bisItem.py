from src.general import specs
from src.general.phases import phases


class BisItem:
    def __init__(self, item_id, source_name):
        self.id = item_id
        self.source_name = source_name
        self.specs = {}

    def add_bis_statement(self, spec_id, item_suffix, slot_name, phase_name, ordinal):
        spec = self.specs.get(spec_id)
        if spec is None:
            spec = Spec(spec_id)
            self.specs[spec_id] = spec
        spec.add_bis_statement(item_suffix, slot_name, phase_name, ordinal)

    def sort_specs(self):
        new_specs_dict = {}
        for spec in specs.specs:
            if self.specs.get(spec):
                new_specs_dict[spec] = self.specs.get(spec)

        self.specs = new_specs_dict

    def __str__(self):
        self_str = f'Bistooltip_{self.source_name}_items[{self.id}] = {{'
        i = 1
        for spec in self.specs.values():
            self_str += f' [{i}] = {spec}'
            if i < (len(self.specs.keys())):
                self_str += ','
            i += 1
        self_str += " }"
        return self_str


class Spec:
    def __init__(self, spec_id):
        self.spec_id = spec_id
        self.slots = {}

    def add_bis_statement(self, item_suffix, slot_name, phase_name, ordinal):
        slot = self.slots.get(slot_name)
        if slot is None:
            slot = Slot(slot_name)
            self.slots[slot_name] = slot
        slot.add_bis_statement(item_suffix, phase_name, ordinal)

    def __str__(self):
        self_str = f'{{ ["class_name"] = "{specs.spec_to_class[self.spec_id]}", ' \
                   f'["spec_name"] = "{specs.spec_to_spec_name[self.spec_id]}", ["slots"] = {{'
        i = 1
        for slot in self.slots.values():
            self_str += f' [{i}] = {slot}'
            if i < (len(self.slots.keys())):
                self_str += ','
            i += 1
        self_str += " } }"
        return self_str


class Slot:
    def __init__(self, slot_name):
        self.name = slot_name
        self.phases = []
        self.suffix = ""
        for _ in phases.keys():
            self.phases.append('-')

    def add_bis_statement(self, item_suffix, phase_name, ordinal):
        phase_index = phases.get(phase_name)
        if phase_index is None:
            return
        if self.phases[phase_index] == '-' or self.phases[phase_index] > ordinal:
            self.phases[phase_index] = ordinal
            self.suffix = item_suffix

    def phase_bis_str(self):
        phase_bis_str = ""
        for i in range(len(phases.keys())):
            if i != 0:
                phase_bis_str += " / "
            phase_bis_str += str(self.phases[i])
        return phase_bis_str
        pass

    def __str__(self):
        return f'{{ ["name"] = "{self.name}", ["suffix"] = "{self.suffix}", ["ranks"] = "{self.phase_bis_str()}" }}'
