import time
import re
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
    index: int
    name: str
    price: float
    cps: float


BUILDING_BASE_CPS = {
    0: 0.1,  # Cursor
    1: 1,  # Grandma
    2: 8,  # Farm
    3: 47,  # Mine
    4: 260,  # Factory
    5: 1400,  # Bank
    6: 7800,  # Temple
    7: 44000,  # Wizard Tower
    8: 260000,  # Shipment
    9: 1600000,  # Alchemy Lab
}


def parse_cookie_number(text: str) -> float:
    """Parse Cookie Clicker number formats like '1.2 million', '3.4 billion', etc."""
    if not text:
        return 0.0

    text = text.strip().replace(",", "").lower()

    multipliers = {
        "million": 1e6,
        "billion": 1e9,
        "trillion": 1e12,
        "quadrillion": 1e15,
        "quintillion": 1e18,
        "sextillion": 1e21,
        "septillion": 1e24,
    }

    for suffix, mult in multipliers.items():
        if suffix in text:
            number_part = text.replace(suffix, "").replace("cookies", "").strip()
            try:
                return float(number_part) * mult
            except ValueError:
                pass

    cleaned = re.sub(r"[^\d.]", "", text)
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def setup_driver() -> webdriver.Chrome:
    """Initialize Chrome driver and load Cookie Clicker."""
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    driver.get("https://orteil.dashnet.org/cookieclicker/")

    wait = WebDriverWait(driver, 30)

    # Wait for big cookie to appear
    wait.until(EC.presence_of_element_located((By.ID, "bigCookie")))
    print("✅ Cookie Clicker loaded!")

    # Wait for loader to disappear
    try:
        wait.until_not(EC.presence_of_element_located((By.ID, "loader")))
        print("✅ Loader gone!")
    except:
        print("✅ No loader found")

    # Click language selection (English)
    try:
        lang_btn = driver.find_element(By.ID, "langSelect-EN")
        if lang_btn.is_displayed():
            lang_btn.click()
            print("🌍 Selected English language")
            time.sleep(2)
    except:
        print("✅ No language selection needed")

    # Wait for overlay to disappear
    try:
        darken = driver.find_element(By.ID, "darken")
        if darken.value_of_css_property("display") != "none":
            wait.until(
                lambda d: d.find_element(By.ID, "darken").value_of_css_property(
                    "display"
                )
                == "none"
            )
            print("✅ Overlay gone!")
    except:
        print("✅ No overlay")

    return driver


def get_cookie_element(driver: webdriver.Chrome):
    """Get the big cookie element."""
    return driver.find_element(By.ID, "bigCookie")


def get_current_cookies(driver: webdriver.Chrome) -> float:
    """Get current cookie count."""
    try:
        text = driver.find_element(By.ID, "cookies").text
        first_line = text.split("\n")[0]
        return parse_cookie_number(first_line)
    except:
        return 0.0


def get_current_cps(driver: webdriver.Chrome) -> float:
    """Get current cookies per second."""
    try:
        text = driver.find_element(By.ID, "cookies").text
        lines = text.split("\n")
        if len(lines) > 1:
            cps_line = lines[1]
            cps_text = cps_line.replace("per second:", "").strip()
            return parse_cookie_number(cps_text)
    except:
        pass
    return 0.0


def get_buildings(driver: webdriver.Chrome) -> List[BuildingInfo]:
    """Get list of buyable buildings."""
    buildings = []

    try:
        elements = driver.find_elements(
            By.CSS_SELECTOR, "#products .product.unlocked.enabled"
        )

        for elem in elements:
            try:
                elem_id = elem.get_attribute("id") or ""

                # Extract index from id (product0 -> 0)
                index = -1
                if elem_id.startswith("product"):
                    try:
                        index = int(elem_id.replace("product", ""))
                    except:
                        pass

                # Get name
                name = ""
                try:
                    name = elem.find_element(By.CLASS_NAME, "title").text.strip()
                except:
                    try:
                        name = elem.find_element(
                            By.CLASS_NAME, "productName"
                        ).text.strip()
                    except:
                        name = f"Building {index}"

                if not name or name == "???":
                    continue

                # Get price
                price = 0.0
                try:
                    price_elem = elem.find_element(By.CLASS_NAME, "price")
                    price = parse_cookie_number(price_elem.text)
                except:
                    pass

                if price <= 0:
                    continue

                # Get CPS from mapping
                cps = BUILDING_BASE_CPS.get(index, 0.1)

                buildings.append(
                    BuildingInfo(
                        element=elem, index=index, name=name, price=price, cps=cps
                    )
                )

            except:
                continue
    except:
        pass

    return buildings


def get_available_upgrades(driver: webdriver.Chrome) -> list:
    """Get list of buyable upgrades."""
    try:
        return driver.find_elements(By.CSS_SELECTOR, "#upgrades .upgrade.enabled")
    except:
        return []


def is_click_upgrade(upgrade) -> bool:
    """Check if upgrade is click-related."""
    try:
        title = (upgrade.get_attribute("title") or "").lower()
        return "per click" in title or "clicking" in title or "mouse" in title
    except:
        return False


def get_upgrade_price(upgrade) -> float:
    """Extract price from upgrade element."""
    try:
        price_elem = upgrade.find_element(By.CLASS_NAME, "price")
        return parse_cookie_number(price_elem.text)
    except:
        pass

    # Try to extract from title
    try:
        title = upgrade.get_attribute("title") or ""
        if "cost" in title.lower():
            # Look for number after "Cost:"
            match = re.search(
                r"cost[:\s]*([0-9,.]+\s*(?:million|billion|trillion)?)",
                title,
                re.IGNORECASE,
            )
            if match:
                return parse_cookie_number(match.group(1))
    except:
        pass

    return 0.0


def click_golden_cookies(driver: webdriver.Chrome):
    """Click any golden cookies on screen."""
    try:
        shimmers = driver.find_elements(By.CLASS_NAME, "shimmer")
        for shimmer in shimmers:
            try:
                shimmer.click()
                print("✨ Clicked golden cookie!")
            except:
                pass
    except:
        pass


def main_loop(driver: webdriver.Chrome, runtime_seconds: int = 600) -> None:
    """Main game loop."""
    cookie = get_cookie_element(driver)
    start_time = time.time()

    # State flags
    click_upgrade_bought = False
    has_farm = False

    # Timing
    next_buy_check = start_time
    next_status = start_time + 15
    last_purchase = "Nothing yet"
    click_count = 0

    print(f"\n🚀 Starting Cookie Clicker bot for {runtime_seconds} seconds!")
    print("📋 Strategy: Click upgrade → Farm → Payback-based buying\n")

    while time.time() - start_time < runtime_seconds:
        # Click the big cookie
        try:
            cookie.click()
            click_count += 1
        except:
            try:
                cookie = get_cookie_element(driver)
            except:
                print("❌ Lost cookie element!")
                break

        # Small delay to not hammer CPU
        time.sleep(0.003)

        # Click golden cookies
        click_golden_cookies(driver)

        now = time.time()

        # Check for purchases every 3 seconds
        if now >= next_buy_check:
            cookies = get_current_cookies(driver)

            # ===== PHASE 1: Buy click upgrade first =====
            if not click_upgrade_bought:
                upgrades = get_available_upgrades(driver)
                for upgrade in upgrades:
                    if is_click_upgrade(upgrade):
                        price = get_upgrade_price(upgrade)
                        if price > 0 and cookies >= price:
                            try:
                                upgrade.click()
                                click_upgrade_bought = True
                                last_purchase = f"Click Upgrade ({price:.0f})"
                                print(
                                    f"⬆️ Bought click upgrade for {price:.0f} cookies!"
                                )
                                time.sleep(0.3)
                            except:
                                pass
                            break

            # ===== PHASE 2: Save for Farm =====
            elif not has_farm:
                buildings = get_buildings(driver)
                farm = None

                for b in buildings:
                    if b.index == 2 or "farm" in b.name.lower():
                        farm = b
                        break

                if farm and cookies >= farm.price:
                    try:
                        farm.element.click()
                        has_farm = True
                        last_purchase = f"Farm ({farm.price:.0f})"
                        print(f"🌾 Bought first Farm for {farm.price:.0f} cookies!")
                        time.sleep(0.3)
                    except:
                        pass
                elif farm:
                    print(f"💰 Saving for Farm: {cookies:.0f}/{farm.price:.0f}")

            # ===== PHASE 3: Payback-based buying =====
            else:
                # First check upgrades
                upgrades = get_available_upgrades(driver)
                for upgrade in upgrades:
                    price = get_upgrade_price(upgrade)
                    if price > 0 and cookies >= price:
                        try:
                            upgrade.click()
                            last_purchase = f"Upgrade ({price:.0f})"
                            print(f"⬆️ Bought upgrade for {price:.0f} cookies!")
                            cookies -= price
                            time.sleep(0.2)
                        except:
                            pass

                # Then check buildings with payback strategy
                buildings = get_buildings(driver)
                if buildings:
                    # Calculate payback for each building
                    best_building = None
                    best_payback = float("inf")

                    for b in buildings:
                        if b.price <= cookies and b.cps > 0:
                            payback = b.price / b.cps
                            if payback < best_payback:
                                best_payback = payback
                                best_building = b

                    # Buy if payback is reasonable (< 5 minutes)
                    if best_building and best_payback < 300:
                        try:
                            best_building.element.click()
                            last_purchase = f"{best_building.name} ({best_building.price:.0f}, payback: {best_payback:.0f}s)"
                            print(
                                f"🏗️ Bought {best_building.name} for {best_building.price:.0f} (payback: {best_payback:.0f}s)"
                            )
                            time.sleep(0.2)
                        except:
                            pass

            next_buy_check = now + 3.0

        # Status report every 30 seconds
        if now >= next_status:
            cookies = get_current_cookies(driver)
            cps = get_current_cps(driver)
            elapsed = now - start_time

            print(f"\n📊 [Status after {elapsed:.0f}s]")
            print(f"🍪 Cookies: {cookies:,.0f}")
            print(f"⚡ CPS: {cps:,.1f}")
            print(f"🖱️ Clicks: {click_count:,}")
            print(f"🛒 Last: {last_purchase}")
            print(
                f"📌 Phase: {'1-ClickUpgrade' if not click_upgrade_bought else '2-Farm' if not has_farm else '3-Payback'}"
            )
            print(f"⏰ Remaining: {runtime_seconds - elapsed:.0f}s\n")

            next_status = now + 30


def main():
    """Main entry point."""
    print("🍪 Cookie Clicker Bot v1.0")
    print("=" * 40)

    driver = setup_driver()

    try:
        main_loop(driver, runtime_seconds=600)
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user.")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
    finally:
        print("\n🔚 Closing browser...")
        driver.quit()
        print("✅ Done!")


if __name__ == "__main__":
    main()
