import json
import os.path

from src.general.phases import phases
from src.wowtbc.wowtbcSpecs import specs


def read_specs_items(specs_dir):
    items_dict = {

    }
    for spec in specs:
        spec_path = os.path.join(specs_dir, spec + '.json')

        with open(spec_path) as json_file:
            data = json.load(json_file)
            bis_list = data['result']['pageContext']['bisList']
            for item in bis_list:
                name = item.get('name')
                if name is not None:
                    if items_dict.get(name) is None:
                        items_dict[name] = 0
    return items_dict


def read_specs_gems(specs_dir):
    gems_dict = {

    }
    for spec in specs:
        spec_path = os.path.join(specs_dir, spec + '.json')

        with open(spec_path) as json_file:
            data = json.load(json_file)
            bis_list = data['result']['pageContext']['bisList']
            for item in bis_list:
                for phase in phases:
                    phase_data = item.get(phase.lower())
                    if phase_data is not None and phase_data.get('bis') is True:
                        gems_data = phase_data.get('gems')
                        if gems_data is not None:
                            for gem in gems_data:
                                name = gem.get('name')
                                if gems_dict.get(name) is None:
                                    gems_dict[name] = 0
    return gems_dict


def read_specs_enchs(specs_dir):
    enchs_dict = {

    }
    for spec in specs:
        spec_path = os.path.join(specs_dir, spec + '.json')

        with open(spec_path) as json_file:
            data = json.load(json_file)
            bis_list = data['result']['pageContext']['bisList']
            for item in bis_list:
                for phase in phases:
                    phase_data = item.get(phase.lower())
                    if phase_data is not None and phase_data.get('bis') is True:
                        ench_data = phase_data.get('enchant')
                        if ench_data is not None:
                            name = ench_data.get('name')
                            if name is not None:
                                if enchs_dict.get(name) is None:
                                    enchs_dict[name] = None
    return enchs_dict


def fill_dict_ids(dictionary, collection_file):
    with open(collection_file) as json_file:
        data = json.load(json_file)
        for item in data:
            item_name = item.get('name')
            item_id = item.get('entry')
            if item_name is not None and item_id is not None and item_name in dictionary:
                if dictionary[item_name] != 0:
                    print('item duplicate found: "' + str(item_name) + '", id1: ' + str(
                        dictionary[item_name]) + ', id2: ' + str(item_id))
                else:
                    dictionary[item_name] = item_id


def fill_ench_ids(dictionary, collection_file, type):
    with open(collection_file) as json_file:
        data = json.load(json_file)
        for item in data:
            item_name = item.get('name')
            item_id = item.get('entry')
            if item_name is not None and item_id is not None and item_name in dictionary:
                if dictionary[item_name] is not None:
                    print('ench duplicate found: "' + str(item_name) + '", id1: ' + str(
                        dictionary[item_name]) + ', id2: ' + str({"id": item_id, "type": type}))
                else:
                    dictionary[item_name] = {"id": item_id, "type": type}


def save_dict(path, dictionary):
    check_dict(dictionary)
    with open(path, 'w') as outfile:
        json.dump(dictionary, outfile)


def collect_item_ids(specs_dir, item_ids_file, items_collection_file):
    items_dict = read_specs_items(specs_dir)
    fill_dict_ids(items_dict, items_collection_file)
    save_dict(item_ids_file, items_dict)
    return 0


def collect_gem_ids(specs_dir, gems_ids_file, gems_collection_file):
    gems = read_specs_gems(specs_dir)
    fill_dict_ids(gems, gems_collection_file)
    save_dict(gems_ids_file, gems)
    return 0


def collect_ench_ids(specs_dir, ench_ids_file, cons_quest_collection_file, ench_spells_collection_file):
    enchs = read_specs_enchs(specs_dir)
    fill_ench_ids(enchs, cons_quest_collection_file, "item")
    fill_ench_ids(enchs, ench_spells_collection_file, "spell")
    save_dict(ench_ids_file, enchs)
    return 0


def check_dict(dictionary):
    for key, value in dictionary.items():
        if value is None or value == 0:
            print("No id for dictionary entry with key: " + str(key))
