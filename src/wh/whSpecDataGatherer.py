import os.path

from bs4 import BeautifulSoup
from selenium import webdriver

from src.general import phases
from src.wh import whPhases, whSpecs

URL_PREFIX = 'https://www.wowhead.com/wotlk/guide/classes/'
URL_SUFFIX = '-bis-gear-'


def collect_specs_data(data_dir):
    driver = webdriver.Chrome()

    for spec in whSpecs.specs:
        print("Collecting spec " + spec)
        for phase_id in phases.phases.values():
            save_spec_page(data_dir, spec, phase_id, driver)

    driver.close()


def save_spec_page(data_dir, spec_id, phase_id, driver):
    url = get_url(spec_id, phase_id)
    url = fix_url(url)
    file_path = os.path.join(data_dir, spec_id + '.' + str(phase_id))

    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    doc = soup.find("div", {"id": "guide-body"})

    with open(file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(str(doc).replace("><", ">\n<").replace("\n</", "</"))


def fix_url(url: str):
    return url.replace("mage/arcane/dps-bis-gear-pre-raid-pve-p3", "mage/arane/dps-bis-gear-pre-raid-pve-p3")


def get_url(spec_id, phase_id):
    return URL_PREFIX + whSpecs.spec_to_url_path[spec_id] + URL_SUFFIX + whPhases.id_to_url_path[phase_id]
