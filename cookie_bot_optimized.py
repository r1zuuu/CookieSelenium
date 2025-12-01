import time
from dataclasses import dataclass
from typing import List, Optional
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import re

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


# Base CPS values for buildings (approximation, doesn't include upgrades)
BUILDING_BASE_CPS = {
    0: 0.1,  # Cursor
    1: 1,  # Grandma
    2: 5,  # Farm
    3: 47,  # Mine
    4: 260,  # Factory
    5: 1400,  # Bank
    6: 7800,  # Temple
    7: 44000,  # Wizard Tower
    8: 260000,  # Shipment
    9: 1600000,  # Alchemy Lab
    10: 10000000,  # Portal
    11: 65000000,  # Time Machine
    12: 430000000,  # Antimatter Condenser
    13: 2900000000,  # Prism
    14: 21000000000,  # Chancemaker
    15: 150000000000,  # Fractal Engine
    16: 1100000000000,  # Javascript Console
    17: 8300000000000,  # Idleverse
    18: 64000000000000,  # Cortex Baker
}


def start_local_server(port=8000):
    """Start HTTP server for Cookie Clicker files in background"""

    def run_server():
        server_dir = os.path.abspath("../cookieclicker")
        if not os.path.exists(server_dir):
            print(f"ERROR: Cookie Clicker directory not found: {server_dir}")
            return

        print(f"Starting HTTP server in: {server_dir}")
        os.chdir(server_dir)

        class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

        server = HTTPServer(("localhost", port), QuietHTTPRequestHandler)
        print(f"HTTP server running on http://localhost:{port}")
        server.serve_forever()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    return f"http://localhost:{port}"


def accept_cookies(driver: webdriver.Chrome, timeout: float = 3.0) -> None:
    """Try to accept cookie/consent dialogs that appear on the page."""
    xpaths = [
        "//button[normalize-space()='Consent']",
        "//button[normalize-space()='Got it!']",
        "//a[normalize-space()='Got it!']",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(., 'Accept all')]",
    ]

    try:
        for xp in xpaths:
            try:
                el = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xp))
                )
                el.click()
                time.sleep(0.4)
                return
            except Exception:
                continue

        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in iframes:
            try:
                driver.switch_to.frame(frame)
                for xp in xpaths:
                    try:
                        el = WebDriverWait(driver, timeout).until(
                            EC.element_to_be_clickable((By.XPATH, xp))
                        )
                        el.click()
                        time.sleep(0.4)
                        driver.switch_to.default_content()
                        return
                    except Exception:
                        continue
            except Exception:
                pass
            finally:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
    except Exception:
        return


def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("detach", True)

    server_url = start_local_server(8000)
    driver = webdriver.Chrome(options=options)

    game_url = f"{server_url}/index.html"
    print(f"Loading Cookie Clicker from: {game_url}")
    driver.get(game_url)

    wait = WebDriverWait(driver, 30)
    try:
        wait.until(EC.presence_of_element_located((By.ID, "bigCookie")))
        print("✅ Cookie Clicker loaded successfully!")

        print("🔄 Waiting for game to finish loading...")
        try:
            wait.until_not(EC.presence_of_element_located((By.ID, "loader")))
            print("✅ Game fully loaded!")
        except:
            print("✅ No loader found, game ready!")

        try:
            lang_btn = driver.find_element(By.ID, "langSelect-EN")
            if lang_btn and lang_btn.is_displayed():
                print("🌍 Selecting English language...")
                lang_btn.click()
                time.sleep(1)
        except:
            print("✅ No language selection needed")

        try:
            darken = driver.find_element(By.ID, "darken")
            if darken and darken.value_of_css_property("display") != "none":
                print("⏳ Waiting for overlay to disappear...")
                wait.until(
                    lambda d: d.find_element(By.ID, "darken").value_of_css_property(
                        "display"
                    )
                    == "none"
                )
                print("✅ Overlay gone!")
        except:
            print("✅ No overlay found")

    except Exception as e:
        print(f"❌ Failed to find bigCookie element: {e}")
        print(f"Page title: {driver.title}")
        print("Page source snippet:")
        print(driver.page_source[:500])
        raise
    return driver


def get_cookie_element(driver: webdriver.Chrome):
    return driver.find_element(By.ID, "bigCookie")


def parse_cookie_number(text: str) -> float:
    """Parse Cookie Clicker number format with suffixes like 'million', 'billion', etc."""
    if not text:
        return 0.0

    # Clean the string - remove commas, extra spaces
    text = text.strip().replace(",", "").replace(" ", "")

    # Define multipliers
    multipliers = {
        "million": 1e6,
        "m": 1e6,
        "billion": 1e9,
        "b": 1e9,
        "trillion": 1e12,
        "t": 1e12,
        "quadrillion": 1e15,
        "q": 1e15,
        "quintillion": 1e18,
        "qi": 1e18,
        "sextillion": 1e21,
        "sx": 1e21,
    }

    # Try to match number with suffix
    pattern = r"^([\d.]+)([a-zA-Z]+)?$"
    match = re.match(pattern, text.lower())

    if match:
        number_str = match.group(1)
        suffix = match.group(2) or ""

        try:
            number = float(number_str)
            multiplier = multipliers.get(suffix, 1)
            return number * multiplier
        except ValueError:
            pass

    # Fallback: extract just digits and dots
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_price_from_element(element) -> float:
    """Extract numeric price from element using robust parsing."""
    # Try .price child element first (most reliable for Cookie Clicker)
    try:
        price_el = element.find_element(By.CLASS_NAME, "price")
        text = price_el.text.strip()
        if text:
            p = parse_cookie_number(text)
            if p > 0:
                return p
    except Exception:
        pass

    # Try data-price attribute
    try:
        price_attr = element.get_attribute("data-price")
        if price_attr:
            p = parse_cookie_number(price_attr)
            if p > 0:
                return p
    except Exception:
        pass

    # Try title attribute
    try:
        title = element.get_attribute("title")
        if title:
            p = parse_cookie_number(title)
            if p > 0:
                return p
    except Exception:
        pass

    # Fallback to element text
    try:
        text = element.text
        if text:
            p = parse_cookie_number(text)
            if p > 0:
                return p
    except Exception:
        pass

    return 0.0


def get_current_cookies(driver: webdriver.Chrome) -> float:
    """Get current cookie count, handling large number formatting."""
    try:
        cookies_text = driver.find_element(By.ID, "cookies").text.split("\n")[0]
        number_part = cookies_text.split(" ")[0]
        return parse_cookie_number(number_part)
    except Exception:
        return 0.0


def get_buildings(driver: webdriver.Chrome) -> List[BuildingInfo]:
    """Get list of available buildings with their prices and CPS."""
    buildings = []
    # Only get enabled products (buyable ones)
    product_elements = driver.find_elements(
        By.CSS_SELECTOR, "#products .product.enabled"
    )

    for element in product_elements:
        try:
            price = parse_price_from_element(element)
            if price <= 0:
                continue

            element_id = element.get_attribute("id") or ""

            # Try multiple ways to get building name
            name = ""
            try:
                name = element.find_element(By.CLASS_NAME, "title").text.strip()
            except:
                try:
                    name = element.find_element(
                        By.CSS_SELECTOR, ".productName"
                    ).text.strip()
                except:
                    try:
                        name = element.find_element(
                            By.ID, f"productName{element_id.replace('product', '')}"
                        ).text.strip()
                    except:
                        name = f"Unknown Product {element_id}"

            if not name or name.isspace():
                continue

            # Get building index for CPS lookup
            index = None
            if element_id.startswith("product"):
                try:
                    index = int(element_id.replace("product", ""))
                except ValueError:
                    pass

            cps = BUILDING_BASE_CPS.get(index, 0.1)  # Default to minimal CPS if unknown
            buildings.append(
                BuildingInfo(element=element, price=price, cps=cps, name=name)
            )
        except Exception:
            continue

    return buildings


def choose_best_building(
    buildings: List[BuildingInfo],
    current_cookies: float,
    next_building: Optional[BuildingInfo] = None,
) -> Optional[BuildingInfo]:
    """Choose optimal building using payback time analysis with simple banking logic."""
    affordable = [b for b in buildings if b.price <= current_cookies]
    if not affordable:
        return None

    # Calculate payback time for all affordable buildings
    def payback_time(building):
        return building.price / building.cps if building.cps > 0 else float("inf")

    # Find best affordable building
    best_affordable = min(affordable, key=payback_time)
    best_payback = payback_time(best_affordable)

    # Simple banking logic: check if we should wait for a better building
    if next_building and next_building.price > current_cookies:
        next_payback = payback_time(next_building)

        # If next building has significantly better payback time, consider waiting
        # Heuristic: wait if next building's payback time is 20% better
        if next_payback * 1.2 < best_payback:
            cookies_needed = next_building.price - current_cookies
            # Only wait if we're reasonably close (less than 2x current cookies needed)
            if cookies_needed < current_cookies * 2:
                print(
                    f"💰 Banking cookies for {next_building.name} (much better payback: {next_payback:.1f}s vs {best_payback:.1f}s)"
                )
                return None

    return best_affordable


def buy_best_building(driver: webdriver.Chrome, last_purchase: List[str]):
    """Buy the most optimal building based on payback time analysis."""
    try:
        cookies = get_current_cookies(driver)
        buildings = get_buildings(driver)

        if not buildings:
            return

        # Find next most expensive building for banking logic
        all_buildings = sorted(buildings, key=lambda b: b.price)
        affordable = [b for b in buildings if b.price <= cookies]

        next_building = None
        if affordable and len(all_buildings) > len(affordable):
            # Find cheapest unaffordable building
            unaffordable = [b for b in all_buildings if b.price > cookies]
            if unaffordable:
                next_building = min(unaffordable, key=lambda b: b.price)

        best = choose_best_building(buildings, cookies, next_building)

        if best is None:
            return

        # Attempt purchase
        cookies_before = cookies
        best.element.click()
        time.sleep(0.3)  # Wait for game to process

        cookies_after = get_current_cookies(driver)

        if cookies_after < cookies_before:
            payback = best.price / best.cps if best.cps > 0 else 0
            print(
                f"🏗️ Bought {best.name} for {best.price:.0f} cookies (CPS: {best.cps}, Payback: {payback:.1f}s)"
            )
            last_purchase.append(f"Building: {best.name} ({best.price:.0f})")

    except Exception as e:
        print(f"❌ Error buying building: {e}")


def buy_upgrades(driver: webdriver.Chrome, last_purchase: List[str]):
    """Buy all affordable upgrades (they're generally always good value)."""
    try:
        # Only get enabled upgrades
        upgrades = driver.find_elements(By.CSS_SELECTOR, "#upgrades .upgrade.enabled")
        if not upgrades:
            return

        cookies = get_current_cookies(driver)
        bought_count = 0

        for upgrade in upgrades:
            try:
                price = parse_price_from_element(upgrade)

                if price > 0 and price <= cookies:
                    upgrade_name = (
                        upgrade.get_attribute("title")
                        or upgrade.get_attribute("id")
                        or "Upgrade"
                    )

                    upgrade.click()
                    bought_count += 1
                    cookies -= price
                    last_purchase.append(f"Upgrade: {upgrade_name} ({price:.0f})")

            except Exception:
                continue

        if bought_count > 0:
            print(f"⬆️ Bought {bought_count} upgrades")

    except Exception as e:
        print(f"❌ Error in buy_upgrades: {e}")


def click_golden_cookies(driver: webdriver.Chrome):
    """Click golden cookies and other shimmers."""
    try:
        golden_cookies = driver.find_elements(By.CLASS_NAME, "shimmer")
        for cookie in golden_cookies:
            try:
                cookie.click()
                print("✨ Clicked golden cookie!")
            except Exception:
                continue
    except Exception:
        pass


def main_loop(driver: webdriver.Chrome, runtime_seconds: int = 600):
    """Main game loop with optimized timing and decision making."""
    cookie = get_cookie_element(driver)
    start_time = time.time()
    next_building_check = start_time
    next_upgrade_check = start_time
    next_report = start_time + 15  # First report after 15 seconds
    last_purchase: List[str] = []
    click_count = 0

    print(f"🚀 Starting optimized Cookie Clicker bot for {runtime_seconds} seconds!")

    while time.time() - start_time < runtime_seconds:
        # Click the big cookie with small delay to prevent CPU spam
        try:
            cookie.click()
            click_count += 1
        except Exception as e:
            print(f"❌ Error clicking cookie: {e}")
            try:
                cookie = get_cookie_element(driver)
            except:
                print("❌ Lost connection to cookie element!")
                break

        # Minimal delay to prevent CPU/browser spam
        time.sleep(0.003)  # 3ms delay

        # Click golden cookies
        click_golden_cookies(driver)

        now = time.time()

        # Check for building purchases every 8 seconds (reduced frequency)
        if now >= next_building_check:
            buy_best_building(driver, last_purchase)
            next_building_check = now + 8.0

        # Check for upgrades every 12 seconds
        if now >= next_upgrade_check:
            buy_upgrades(driver, last_purchase)
            next_upgrade_check = now + 12.0

        # Status report
        if now >= next_report:
            try:
                cookies = get_current_cookies(driver)
                cps_element = driver.find_element(By.ID, "cookies")
                cps_text = (
                    cps_element.text.split("\n")[1]
                    if "\n" in cps_element.text
                    else "CPS: Unknown"
                )

                info = last_purchase[-1] if last_purchase else "Nothing yet"
                elapsed = now - start_time

                print(f"\n📊 [Status after {elapsed:.0f}s]")
                print(f"🍪 Cookies: {cookies:.0f}")
                print(f"⚡ {cps_text}")
                print(f"🖱️ Manual clicks: {click_count}")
                print(f"🛒 Last purchase: {info}")
                print(f"⏰ Time remaining: {runtime_seconds - elapsed:.0f}s\n")

            except Exception as e:
                print(f"❌ Error in status report: {e}")

            next_report = now + 45  # Report every 45 seconds


def main():
    """Main entry point."""
    print("🍪 Optimized Cookie Clicker Bot Starting...")
    driver = setup_driver()

    try:
        print("\n📋 Initial game state:")
        cookies = get_current_cookies(driver)
        print(f"🍪 Starting cookies: {cookies:.0f}")

        buildings = get_buildings(driver)
        print(f"🏗️ Available buildings: {len(buildings)}")

        upgrades = driver.find_elements(By.CSS_SELECTOR, "#upgrades .upgrade.enabled")
        print(f"⬆️ Available upgrades: {len(upgrades)}")

        print(f"\n🎯 Starting optimized automated play...")
        main_loop(driver, 600)  # Run for 10 minutes

    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user.")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
    finally:
        print("\n🔚 Closing browser...")
        driver.quit()
        print("✅ Bot finished!")


if __name__ == "__main__":
    main()
