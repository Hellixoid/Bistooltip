import json
import os
import shutil

from src.general import cleaner, phases
from src import dirsAndFiles
import dataSources
from src.wh import whSpecs, whSpecDataGatherer
from src.wowtbc import wowtbcItemsIdsCollector, wowtbcSpecDataGatherer, wowtbcSpecs
from src.general.bisListConstructor import BisListConstructor
from src.general.idResolver import IdResolver
from src.general.itemListConstructor import ItemListConstructor
from src.wh.whSpecDataParser import WhSpecDataParser
from src.wowtbc.wowtbcSpecDataParser import WowtbcSpecDataParser

data_collection = None


class SourceConfig:
    """Per-source paths used by the shared gather/convert/save pipeline steps."""

    def __init__(self, name, spec_data_dir, items_data_file, addon_items_data_file,
                 bislists_data_file, addon_bislists_data_file):
        self.name = name
        self.spec_data_dir = spec_data_dir
        self.items_data_file = items_data_file
        self.addon_items_data_file = addon_items_data_file
        self.bislists_data_file = bislists_data_file
        self.addon_bislists_data_file = addon_bislists_data_file


wowtbc_config = SourceConfig(
    dataSources.wowtbc,
    dirsAndFiles.wowtbc_spec_data_dir,
    dirsAndFiles.Bistooltip_wowtbc_items_data_file,
    dirsAndFiles.addon_Bistooltip_wowtbc_items_data_file,
    dirsAndFiles.Bistooltip_wowtbc_bislists_data_file,
    dirsAndFiles.addon_Bistooltip_wowtbc_bislists_data_file)

wh_config = SourceConfig(
    dataSources.wh,
    dirsAndFiles.wh_spec_data_dir,
    dirsAndFiles.Bistooltip_wh_items_data_file,
    dirsAndFiles.addon_Bistooltip_wh_items_data_file,
    dirsAndFiles.Bistooltip_wh_bislists_data_file,
    dirsAndFiles.addon_Bistooltip_wh_bislists_data_file)


def gather_spec_data(spec_data_dir, gather_fn):
    cleaner.delete_folder(spec_data_dir)
    os.mkdir(spec_data_dir)
    gather_fn(spec_data_dir)


def convert_sorted_spec_to_item_list(config, sorted_specs):
    item_list_constructor = ItemListConstructor(config.name)
    for spec in sorted_specs:
        item_list_constructor.add_sorted_spec(spec)
    item_list_constructor.add_horde_ali_mapping(dirsAndFiles.horde_to_ali_file)
    item_list_constructor.add_tokens(dirsAndFiles.tokens_file)
    item_list_constructor.save_data(config.items_data_file, config.name)
    # item_list_constructor.save_csv(config.name)
    shutil.copyfile(config.items_data_file, config.addon_items_data_file)


def save_bislist(config, sorted_specs):
    bis_list_constructor = BisListConstructor(sorted_specs)
    bis_list_constructor.save_data(config.bislists_data_file, config.name)
    shutil.copyfile(config.bislists_data_file, config.addon_bislists_data_file)


def collect_wowtbc_item_ids():
    cleaner.delete_file(dirsAndFiles.item_ids_file)
    cleaner.delete_file(dirsAndFiles.gem_ids_file)
    cleaner.delete_file(dirsAndFiles.ench_ids_file)
    wowtbcItemsIdsCollector.collect_item_ids(
        dirsAndFiles.wowtbc_spec_data_dir, dirsAndFiles.item_ids_file, dirsAndFiles.items_collection_file)
    wowtbcItemsIdsCollector.collect_gem_ids(
        dirsAndFiles.wowtbc_spec_data_dir, dirsAndFiles.gem_ids_file, dirsAndFiles.gems_collection_file)
    wowtbcItemsIdsCollector.collect_ench_ids(
        dirsAndFiles.wowtbc_spec_data_dir, dirsAndFiles.ench_ids_file,
        dirsAndFiles.cons_quest_collection_file, dirsAndFiles.ench_spells_collection_file)


def collect_wowtbc_sorted_spec_data():
    sorted_specs = []
    id_resolver = IdResolver(dirsAndFiles.item_ids_file, dirsAndFiles.gem_ids_file,
                             dirsAndFiles.ench_ids_file, dirsAndFiles.horde_to_ali_file)
    spec_data_parser = WowtbcSpecDataParser(id_resolver)
    for spec in wowtbcSpecs.specs:
        print(f'\nParsing spec {dataSources.wowtbc}: {spec}')
        file_path = os.path.join(dirsAndFiles.wowtbc_spec_data_dir, spec + '.json')
        sorted_specs.append(spec_data_parser.parse(file_path))
    return sorted_specs


def collect_wh_sorted_spec_data():
    sorted_specs = []
    spec_data_parser = WhSpecDataParser(
        dirsAndFiles.cons_quest_collection_file,
        dirsAndFiles.ench_spells_collection_file,
        dirsAndFiles.horde_to_ali_file,
        dirsAndFiles.soo_wf_gear_file)
    for spec in whSpecs.specs:
        print(f'\nParsing spec {dataSources.wh}: {spec}')
        sorted_specs.append(spec_data_parser.parse(spec))
    return sorted_specs


def process_wowtbc():
    if data_collection is True:
        gather_spec_data(wowtbc_config.spec_data_dir, wowtbcSpecDataGatherer.collect_specs_data)
    collect_wowtbc_item_ids()
    spec_data = collect_wowtbc_sorted_spec_data()
    convert_sorted_spec_to_item_list(wowtbc_config, spec_data)
    save_bislist(wowtbc_config, spec_data)


def process_wh():
    if data_collection is True:
        gather_spec_data(wh_config.spec_data_dir, whSpecDataGatherer.collect_specs_data)
    spec_data = collect_wh_sorted_spec_data()
    convert_sorted_spec_to_item_list(wh_config, spec_data)
    save_bislist(wh_config, spec_data)


def build_ali_to_horde_mapping():
    with open(dirsAndFiles.horde_to_ali_file) as json_file:
        data = json.load(json_file)

    with open(dirsAndFiles.Bistooltip_horde_to_ali_data_file, 'w') as file:
        file.write('Bistooltip_horde_to_ali = {};\n')
        for hordeId in data:
            aliId = data[hordeId]
            file.write('Bistooltip_horde_to_ali[' + aliId + '] = ' + hordeId + ';\n')

    shutil.copyfile(
        dirsAndFiles.Bistooltip_horde_to_ali_data_file, dirsAndFiles.addon_Bistooltip_horde_to_ali_data_file)


if __name__ == '__main__':
    data_collection = True
    # process_wowtbc()
    process_wh()
    # build_ali_to_horde_mapping()
