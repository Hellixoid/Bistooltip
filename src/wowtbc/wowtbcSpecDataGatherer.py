import json
import os.path

import requests

from src.wowtbc.wowtbcSpecs import specs

URL_PREFIX = 'https://wowtbc.gg/page-data/wotlk/bis-list/'
URL_SUFFIX = '/page-data.json'


def collect_specs_data(data_dir):
    for spec in specs:
        print("Collecting spec " + spec)
        save_spec_page(data_dir, spec)


def save_spec_page(data_dir, spec_name):
    url = URL_PREFIX + spec_name + URL_SUFFIX
    r = requests.get(url)
    file_path = os.path.join(data_dir, spec_name + '.json')

    with open(file_path, 'w') as output_file:
        json.dump(r.json(), output_file, ensure_ascii=False, indent=2)
