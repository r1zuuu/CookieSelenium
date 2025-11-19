import time
from dataclasses import dataclass
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class BuildingInfo:
    element: object
    price: float
    cps: float
    name: str


BUILDING_BASE_CPS = {
    0: 0.1,
    1: 1,
    2: 5,
    3: 47,
    4: 260,
    5: 1400,
    6: 7800,
    7: 44000,
    8: 260000,
    9: 1600000,
    10: 10000000,
    11: 65000000,
    12: 430000000,
    13: 2900000000,
    14: 21000000000,
    15: 150000000000,
    16: 1100000000000,
    17: 8300000000000,
    18: 64000000000000,
}


def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    driver = webdriver.Chrome(options=options)
    driver.get("https://orteil.dashnet.org/cookieclicker/")

    wait = WebDriverWait(driver, 30)
    try:
        lang_btn = wait.until(EC.element_to_be_clickable((By.ID, "langSelect-EN")))
        lang_btn.click()
    except Exception:
        pass

    wait.until(EC.presence_of_element_located((By.ID, "bigCookie")))
    return driver


def get_cookie_element(driver: webdriver.Chrome):
    return driver.find_element(By.ID, "bigCookie")


def parse_float(value: Optional[str]) -> float:
    if not value:
        return 0.0
    cleaned = "".join(ch for ch in value if ch.isdigit() or ch == ".")
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def get_current_cookies(driver: webdriver.Chrome) -> float:
    cookies_text = driver.find_element(By.ID, "cookies").text.split("\n")[0]
    number_part = cookies_text.split(" ")[0]
    return parse_float(number_part)


def get_buildings(driver: webdriver.Chrome) -> List[BuildingInfo]:
    buildings = []
    product_elements = driver.find_elements(By.CSS_SELECTOR, "#products .product")
    for element in product_elements:
        classes = element.get_attribute("class") or ""
        if "toggled" in classes:
            # Hidden products when store is collapsed.
            continue
        price_attr = element.get_attribute("data-price")
        price = parse_float(price_attr) if price_attr else 0.0
        element_id = element.get_attribute("id") or ""
        index = None
        name = element.find_element(By.CLASS_NAME, "title").text
        if element_id.startswith("product"):
            try:
                index = int(element_id.replace("product", ""))
            except ValueError:
                index = None
        cps = BUILDING_BASE_CPS.get(index, max(BUILDING_BASE_CPS.values()))
        buildings.append(BuildingInfo(element=element, price=price, cps=cps, name=name))
    return buildings


def choose_best_building(
    buildings: List[BuildingInfo], current_cookies: float
) -> Optional[BuildingInfo]:
    affordable = [b for b in buildings if b.price and b.price <= current_cookies]
    if not affordable:
        return None
    return max(affordable, key=lambda b: b.cps / b.price)


def buy_best_building(driver: webdriver.Chrome, last_purchase: List[str]):
    cookies = get_current_cookies(driver)
    buildings = get_buildings(driver)
    best = choose_best_building(buildings, cookies)
    if best is None:
        return
    try:
        best.element.click()
        last_purchase.append(f"Building: {best.name} ({best.price:.0f})")
    except Exception:
        pass


def buy_upgrades(driver: webdriver.Chrome, last_purchase: List[str]):
    upgrades = driver.find_elements(By.CSS_SELECTOR, "#upgrades .upgrade.enabled")
    if not upgrades:
        return
    cookies = get_current_cookies(driver)
    for upgrade in upgrades:
        price_attr = upgrade.get_attribute("data-price")
        price = parse_float(price_attr)
        if price and price <= cookies:
            try:
                upgrade.click()
                last_purchase.append(f"Upgrade ({price:.0f})")
                cookies -= price
            except Exception:
                continue


def click_golden_cookies(driver: webdriver.Chrome):
    golden_cookies = driver.find_elements(By.CLASS_NAME, "shimmer")
    for cookie in golden_cookies:
        try:
            cookie.click()
        except Exception:
            continue


def main_loop(driver: webdriver.Chrome, runtime_seconds: int = 600):
    cookie = get_cookie_element(driver)
    start_time = time.time()
    next_building_check = start_time
    next_upgrade_check = start_time
    next_report = start_time + 60
    last_purchase: List[str] = []

    while time.time() - start_time < runtime_seconds:
        cookie.click()
        click_golden_cookies(driver)

        now = time.time()
        if now >= next_building_check:
            buy_best_building(driver, last_purchase)
            next_building_check = now + 1.5
        if now >= next_upgrade_check:
            buy_upgrades(driver, last_purchase)
            next_upgrade_check = now + 3
        if now >= next_report:
            cookies = get_current_cookies(driver)
            cps_text = driver.find_element(By.ID, "cps").text
            info = last_purchase[-1] if last_purchase else "Nothing recently"
            print(f"[Status] Cookies: {cookies:.0f}, {cps_text}, Last: {info}")
            next_report = now + 60


def main():
    driver = setup_driver()
    try:
        main_loop(driver)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
