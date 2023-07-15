import json


class IdResolver:
    def __init__(self, item_dict_path, gem_dict_path, ench_dict_path, horde_to_ali_file_path):
        with open(item_dict_path) as json_file:
            self.item_data = json.load(json_file)
        with open(gem_dict_path) as json_file:
            self.gem_data = json.load(json_file)
        with open(ench_dict_path) as json_file:
            self.ench_data = json.load(json_file)
        with open(horde_to_ali_file_path) as json_file:
            self.horde_to_ali_dict = json.load(json_file)
        pass

    def get_item_id(self, name):
        item_id = self.item_data[name]
        if str(item_id) in self.horde_to_ali_dict:
            return int(self.horde_to_ali_dict[str(item_id)])
        return item_id

    def get_enchant(self, name):
        return self.ench_data[name]

    def get_gem_id(self, name):
        return self.gem_data[name]
