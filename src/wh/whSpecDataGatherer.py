import os.path

from bs4 import BeautifulSoup
from selenium import webdriver

from src.general import phases
from src.wh import whPhases, whSpecs

URL_PREFIX = 'https://www.wowhead.com/mop-classic/guide/classes/'
URL_SUFFIX = '-best-gear-bis-'


def collect_specs_data(data_dir):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--start-maximized')
    # options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument(r'--user-data-dir=D:\code')
    options.add_argument('--profile-directory=Profile 2')
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
    try:
        driver.close()
    except Exception as e:
        print("Failed to close driver: %s" % (e))


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
