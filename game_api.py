"""
Funkcje do interakcji z grą - czysto przez Selenium, bez JS
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from config import CLICK_BATCH


def click_cookie(driver, times=CLICK_BATCH):
    """klika w duże ciastko określoną liczbę razy"""
    try:
        cookie = driver.find_element(By.ID, "bigCookie")
        for _ in range(times):
            cookie.click()
    except:
        pass


def click_golden_cookies(driver):
    """zbiera złote ciastka jeśli są"""
    clicked = 0
    try:
        # złote ciastka mają klasę "shimmer"
        shimmers = driver.find_elements(By.CSS_SELECTOR, ".shimmer")
        for shimmer in shimmers:
            try:
                shimmer.click()
                clicked += 1
            except:
                pass
    except:
        pass
    return clicked


def get_cookies_count(driver):
    """odczytuje liczbę ciastek z elementu na stronie"""
    try:
        cookies_el = driver.find_element(By.ID, "cookies")
        text = cookies_el.text.split("\n")[0]  # pierwsza linia to liczba
        # usuwamy tekst " cookies" i zamieniamy na liczbę
        text = text.replace(" cookies", "").replace(",", "").strip()
        # obsługa notacji typu "1.5 million"
        multipliers = {
            "million": 1e6,
            "billion": 1e9,
            "trillion": 1e12,
            "quadrillion": 1e15,
            "quintillion": 1e18,
        }
        for word, mult in multipliers.items():
            if word in text.lower():
                num = float(text.lower().replace(word, "").strip())
                return num * mult
        return float(text) if text else 0
    except:
        return 0


def get_cps(driver):
    """odczytuje CpS (cookies per second)"""
    try:
        cookies_el = driver.find_element(By.ID, "cookies")
        text = cookies_el.text
        # szukamy linii z "per second"
        for line in text.split("\n"):
            if "per second" in line.lower():
                # wyciągamy liczbę
                num_text = (
                    line.lower()
                    .replace("per second", "")
                    .replace(":", "")
                    .replace(",", "")
                    .strip()
                )
                multipliers = {
                    "million": 1e6,
                    "billion": 1e9,
                    "trillion": 1e12,
                    "quadrillion": 1e15,
                    "quintillion": 1e18,
                }
                for word, mult in multipliers.items():
                    if word in num_text:
                        num = float(num_text.replace(word, "").strip())
                        return num * mult
                return float(num_text) if num_text else 0
        return 0
    except:
        return 0


def get_game_state(driver):
    """pobiera stan gry i klika ciastko"""
    click_cookie(driver, CLICK_BATCH)
    golden = click_golden_cookies(driver)
    cookies = get_cookies_count(driver)
    cps = get_cps(driver)
    return {"cookies": cookies, "cps": cps, "golden": golden}


def get_cursor_price(driver):
    """zwraca cenę pierwszego budynku (Cursor)"""
    try:
        # cena jest w elemencie produktu
        product = driver.find_element(By.ID, "product0")
        price_el = product.find_element(By.CSS_SELECTOR, ".price")
        price_text = price_el.text.replace(",", "").strip()

        multipliers = {"million": 1e6, "billion": 1e9, "trillion": 1e12}
        for word, mult in multipliers.items():
            if word in price_text.lower():
                num = float(price_text.lower().replace(word, "").strip())
                return num * mult
        return float(price_text) if price_text else 15
    except:
        return 15


def get_upgrades(driver):
    """pobiera listę dostępnych ulepszeń ze sklepu"""
    upgrades = []
    try:
        upgrade_elements = driver.find_elements(By.CSS_SELECTOR, "#upgrades .upgrade")
        for i, el in enumerate(upgrade_elements):
            try:
                # sprawdzamy czy ulepszenie jest aktywne (można kupić)
                classes = el.get_attribute("class")
                can_buy = "enabled" in classes

                # pobieramy info z tooltipa przez najechanie
                upgrades.append({"id": i, "element": el, "canBuy": can_buy})
            except:
                pass
    except:
        pass
    return upgrades


def get_buildings(driver):
    """pobiera listę budynków"""
    buildings = []
    try:
        for i in range(20):  # max 20 typów budynków
            try:
                product = driver.find_element(By.ID, f"product{i}")

                # sprawdzamy czy jest odblokowany (widoczny)
                if not product.is_displayed():
                    continue

                # nazwa budynku
                name_el = product.find_element(By.CSS_SELECTOR, ".title")
                name = name_el.text if name_el else f"Building {i}"

                # cena
                price_el = product.find_element(By.CSS_SELECTOR, ".price")
                price_text = price_el.text.replace(",", "").strip()

                multipliers = {"million": 1e6, "billion": 1e9, "trillion": 1e12}
                price = 0
                for word, mult in multipliers.items():
                    if word in price_text.lower():
                        price = (
                            float(price_text.lower().replace(word, "").strip()) * mult
                        )
                        break
                else:
                    try:
                        price = float(price_text)
                    except:
                        price = float("inf")

                # ilość posiadanych
                owned_el = product.find_element(By.CSS_SELECTOR, ".owned")
                owned = int(owned_el.text) if owned_el.text else 0

                # czy można kupić
                classes = product.get_attribute("class")
                can_buy = "enabled" in classes

                buildings.append(
                    {
                        "id": i,
                        "name": name,
                        "price": price,
                        "amount": owned,
                        "canBuy": can_buy,
                        "element": product,
                    }
                )
            except:
                pass
    except:
        pass
    return buildings


def get_stats(driver):
    """pobiera statystyki"""
    return {
        "cookies": get_cookies_count(driver),
        "cps": get_cps(driver),
        "buildings": len([b for b in get_buildings(driver) if b["amount"] > 0]),
        "upgrades": len(
            driver.find_elements(By.CSS_SELECTOR, "#upgrades .upgrade.enabled")
        ),
    }


def buy_upgrade(driver, upgrade):
    """kupuje ulepszenie klikając w nie"""
    try:
        el = upgrade.get("element")
        if el:
            el.click()
            return True
    except:
        pass
    return False


def buy_building(driver, building):
    """kupuje budynek klikając w produkt"""
    try:
        el = building.get("element")
        if el:
            el.click()
            return True
    except:
        pass
    return False
