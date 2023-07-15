from src.general import specs, phases, classes
from src.general.slots import slots
from src.general.sortedSpec import SortedSpec


class BisListConstructor:
    def __init__(self, sorted_specs):
        self.sorted_specs = sorted_specs

    def save_data(self, output_file, source_name):
        with open(output_file, 'w') as file:
            file.write('Bistooltip_' + source_name + '_bislists = {};\n')
            for class_name in classes.classes:
                file.write(f'Bistooltip_{source_name}_bislists["{class_name}"] = {"{}"};\n')

            self.form_classes_and_phases(source_name, file)

            # sort slots
            for sorted_spec in self.sorted_specs:
                new_dict = {}
                sorted_spec: SortedSpec = sorted_spec
                slot_keys = sorted_spec.slots.keys()
                for slot_name in slots.keys():
                    slot_name = slot_name.capitalize()
                    if slot_name.capitalize() in slot_keys:
                        new_dict[slot_name] = sorted_spec.slots[slot_name]
                sorted_spec.slots = new_dict

            spec_dict = {}

            # items dict
            for sorted_spec in self.sorted_specs:
                spec_id = sorted_spec.id
                if not (spec_dict.get(spec_id)):
                    spec_dict[spec_id] = {
                    }
                    for slot in sorted_spec.slots.values():
                        for phase in slot.phases:
                            phase_name = phases.phase_to_name[phase.name]
                            if not (phase_name in spec_dict[spec_id]):
                                spec_dict[spec_id][phase_name] = {}
                            if not (slot.name in spec_dict[spec_id][phase_name]):
                                spec_dict[spec_id][phase_name][slot.name] = []
                            for i in range(6):
                                if len(phase.items) < i + 1:
                                    spec_dict[spec_id][phase_name][slot.name].append(-1)
                                else:
                                    spec_dict[spec_id][phase_name][slot.name].append(phase.items[i].id)

            enhancements_dict = {}
            # ench and gems dict
            for sorted_spec in self.sorted_specs:

                spec_id = sorted_spec.id
                if not (enhancements_dict.get(spec_id)):
                    enhancements_dict[spec_id] = {
                    }
                    for slot in sorted_spec.slots.values():
                        for phase in slot.phases:
                            phase_name = phases.phase_to_name[phase.name]
                            if not (phase_name in enhancements_dict[spec_id]):
                                enhancements_dict[spec_id][phase_name] = {}
                            enchs = [None] * 6
                            for i in range(len(phase.enhs)):
                                enchs[i * 2] = phase.enhs[i]
                            for i in range(min(len(phase.gems), 3)):
                                enchs[i * 2 + 1] = phase.gems[i]
                            for i in range(6):
                                if enchs[5 - i] is None:
                                    enchs.pop(5 - i)
                                else:
                                    break
                            enhancements_dict[spec_id][phase_name][slot.name] = enchs

            for spec_id, spec in spec_dict.items():
                class_name = specs.spec_to_class[spec_id]
                spec_name = specs.spec_to_spec_name[spec_id]

                file.write(f'Bistooltip_{source_name}_bislists["{class_name}"]["{spec_name}"] = {"{}"};\n')
                for phase in phases.phases:
                    file.write(
                        f'Bistooltip_{source_name}_bislists["{class_name}"]["{spec_name}"]["{phases.phase_to_name[phase]}"]'
                        f' = {"{}"};\n')

                for phase_name, phase in spec.items():
                    slot_i = 0
                    for slot_name, items in phase.items():
                        slot_i += 1
                        enchantments = enhancements_dict[spec_id][phase_name][slot_name]
                        enhs_str = "{ "
                        for idx, enhancement in enumerate(enchantments):
                            if enhancement is not None:
                                enhs_str += f'[{idx + 1}] = {{ ["type"] = "{enhancement["type"]}", ["id"] = {enhancement["id"]} }}'
                            else:
                                enhs_str += f'[{idx + 1}] = {{ ["type"] = "none", ["id"] = 0 }}'
                            if idx < len(enchantments) - 1:
                                enhs_str += ", "
                            else:
                                enhs_str += " "
                        enhs_str += "}"
                        file.write(f'Bistooltip_{source_name}_bislists'
                                   f'["{class_name}"]["{spec_name}"]["{phase_name}"][{slot_i}] = '
                                   f'{{ ["slot_name"] = "{slot_name.capitalize()}", '
                                   f'["enhs"] = {enhs_str}, '
                                   f'[1] = {items[0]}, [2] = {items[1]}, [3] = {items[2]}, '
                                   f'[4] = {items[3]}, [5] = {items[4]}, [6] = {items[5]} }}\n')

    def form_classes_and_phases(self, source_name, file):
        class_index = 1
        file.write(f'Bistooltip_{source_name}_classes = {{}};\n')
        for class_name in classes.classes:
            specs_array = []
            for sorted_spec in self.sorted_specs:
                spec_id = sorted_spec.id
                spec_class_name = specs.spec_to_class[spec_id]
                if spec_class_name == class_name:
                    spec_name = specs.spec_to_spec_name[spec_id]
                    specs_array.append(spec_name)
            file.write(
                f'Bistooltip_{source_name}_classes[{class_index}] = {{ ["name"] = "{class_name}", ["specs"] = {{ \n')
            spec_index = 1
            for specName in specs_array:
                file.write(f'    [{spec_index}] = "{specName}"')
                if spec_index == len(specs_array):
                    file.write('\n')
                else:
                    file.write(',\n')
                spec_index += 1
            file.write('}};\n')
            class_index += 1

        file.write('\n')

        file.write(f'Bistooltip_{source_name}_phases = {{ ')
        slot_vals = list(self.sorted_specs[0].slots.values())
        phase_index = 1
        for phase in slot_vals[0].phases:
            phase_name = phases.phase_to_name[phase.name]
            file.write(f'"{phase_name}"')
            if phase_index == len(slot_vals[0].phases):
                file.write(f' ')
            else:
                file.write(f', ')
            phase_index += 1
        pass
        file.write('};\n\n')
