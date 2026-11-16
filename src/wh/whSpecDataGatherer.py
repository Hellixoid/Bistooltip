import os.path
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src.wh import whSpecs

# The BiS items are rendered by the gear-planner widget, which hydrates (and
# pulls its item links in via JS) after the initial page load. These are the
# elements we wait on before reading page_source.
_PLANNER_WRAPPER = "div.gear-planner-slots-wrapper"
_PLANNER_ITEM = "div.wow-gear-slot a.wow-gear-slot-icon[href*='item=']"

URL_PREFIX = 'https://www.wowhead.com/forever/guide/classes/'

# WoW Forever currently publishes a single BiS page per spec (Phase 1), so there is
# no per-phase URL. The page is saved under phase id 0 to match the parser.
PHASE_ID = 0


def collect_specs_data(data_dir):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-infobars')
    options.add_argument(r'--user-data-dir=D:\code')
    options.add_argument('--profile-directory=Profile 2')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    for spec in whSpecs.specs:
        print("Collecting spec " + spec)
        collected_flag = False
        while collected_flag is not True:
            try:
                save_spec_page(data_dir, spec, driver)
                collected_flag = True
            except Exception as e:
                print("Failed to load page: %s" % (e))
    try:
        driver.close()
    except Exception as e:
        print("Failed to close driver: %s" % (e))


def save_spec_page(data_dir, spec_id, driver):
    url = get_url(spec_id)
    file_path = os.path.join(data_dir, spec_id + '.' + str(PHASE_ID))

    driver.get(url)
    _wait_for_gear_planner(driver)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    doc = soup.find("div", {"id": "guide-body"})

    with open(file_path, 'w', encoding="utf-8") as output_file:
        output_file.write(str(doc).replace("><", ">\n<").replace("\n</", "</"))


def _wait_for_gear_planner(driver):
    """Wait for the gear-planner widget to render and populate its item links.

    Every wait is best-effort: a spec whose guide has no BiS items never grows
    any item links, so on timeout we simply save whatever rendered rather than
    failing (which would retry forever in collect_specs_data)."""
    try:
        WebDriverWait(driver, 20).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, _PLANNER_WRAPPER))
    except TimeoutException:
        return
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, _PLANNER_ITEM))
    except TimeoutException:
        return  # guide has no gear-planner items (unfilled spec)
    # The whole set hydrates together; give the remaining slots a moment to fill.
    time.sleep(1.0)


def get_url(spec_id):
    return URL_PREFIX + whSpecs.spec_to_wh_bis_path[spec_id]
