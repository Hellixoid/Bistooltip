import os.path

from bs4 import BeautifulSoup
from selenium import webdriver

from src.general import phases
from src.wh import whPhases, whSpecs

URL_PREFIX = 'https://www.wowhead.com/cata/guide/classes/'
URL_SUFFIX = '-bis-gear-'


def collect_specs_data(data_dir):
    options = webdriver.ChromeOptions()
    options.add_argument(r"--user-data-dir=C:\Users\User\AppData\Local\Google\Chrome\User Data")
    options.add_argument(r'--profile-directory=Profile 2')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    for spec in whSpecs.specs:
        print("Collecting spec " + spec)
        for phase_id in phases.phases.values():
            print("Phase: " + str(phase_id))
            collected_flag = False
            while collected_flag is not True:
                try:
                    save_spec_page(data_dir, spec, phase_id, driver)
                    collected_flag = True
                except Exception as e:
                    print("Failed to load page: %s" % (e))


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
