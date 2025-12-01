"""
Cookie Clicker Bot v3.0 - with upgrade prioritization and smart buying
Uses JavaScript Game API for reliable interaction
"""

import time
import os
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

RUNTIME_SECONDS = 3600
CLICK_BATCH = 15
STATUS_INTERVAL = 10
BUY_CHECK_INTERVAL = 0.3
MAX_PAYBACK_SECONDS = 300

CLICK_KEYWORDS = [
    "cursor",
    "click",
    "finger",
    "mouse",
    "hand",
    "carpal",
    "ambidextrous",
    "thousand",
    "million",
    "billion",
    "trillion",
]
GOLDEN_KEYWORDS = ["golden", "lucky", "fortune", "chain"]
BUILDING_NAMES = [
    "cursor",
    "grandma",
    "farm",
    "mine",
    "factory",
    "bank",
    "temple",
    "wizard",
    "shipment",
    "alchemy",
    "portal",
    "time machine",
    "antimatter",
    "prism",
    "chancemaker",
    "fractal",
]


def start_local_server(port=8000):
    def run_server():
        server_dir = os.path.abspath("../cookieclicker")
        if not os.path.exists(server_dir):
            print(f"ERROR: Directory not found: {server_dir}")
            return
        print(f"Starting HTTP server in: {server_dir}")
        os.chdir(server_dir)

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

        server = HTTPServer(("localhost", port), QuietHandler)
        print(f"Server running on http://localhost:{port}")
        server.serve_forever()

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1)
    return f"http://localhost:{port}"


def setup_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("detach", True)
    server_url = start_local_server(8000)
    driver = webdriver.Chrome(options=options)
    driver.get(f"{server_url}/index.html")
    print("Loading Cookie Clicker...")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "bigCookie"))
    )
    print("Game loaded!")
    for _ in range(60):
        try:
            if driver.execute_script(
                "return typeof Game !== 'undefined' && Game.ready;"
            ):
                print("Game ready!")
                break
        except:
            pass
        time.sleep(0.5)
    try:
        lang = driver.find_element(By.ID, "langSelect-EN")
        if lang.is_displayed():
            lang.click()
            print("Selected English language")
            time.sleep(2)
    except:
        pass
    time.sleep(1)
    return driver


def get_cookies(driver):
    try:
        return driver.execute_script("return Game.cookies;") or 0.0
    except:
        return 0.0


def get_cps(driver):
    try:
        return driver.execute_script("return Game.cookiesPs;") or 0.0
    except:
        return 0.0


def click_cookie(driver, times=1):
    try:
        driver.execute_script(f"for(var i=0;i<{times};i++)Game.ClickCookie();")
    except:
        pass


def click_golden(driver):
    try:
        result = driver.execute_script(
            "var c=0;if(Game.shimmers)for(var i=Game.shimmers.length-1;i>=0;i--){Game.shimmers[i].pop();c++;}return c;"
        )
        if result and result > 0:
            print("Golden cookie clicked!")
        return result or 0
    except:
        return 0


def get_upgrades(driver):
    try:
        return (
            driver.execute_script(
                "var r=[];for(var i in Game.UpgradesInStore){var u=Game.UpgradesInStore[i];if(u.pool!=='toggle'&&u.pool!=='tech'&&u.pool!=='debug')r.push({id:u.id,name:u.name,desc:u.desc||'',price:u.getPrice(),canBuy:u.canBuy(),pool:u.pool||'',tier:u.tier||0,buildingTie:u.buildingTie?u.buildingTie.name:''});}return r;"
            )
            or []
        )
    except:
        return []


def buy_upgrade(driver, uid):
    try:
        return bool(
            driver.execute_script(
                f"var u=Game.UpgradesById[{uid}];if(u&&u.canBuy()){{u.buy();return true;}}return false;"
            )
        )
    except:
        return False


def get_buildings(driver):
    try:
        return (
            driver.execute_script(
                "var r=[];for(var i in Game.ObjectsById){var b=Game.ObjectsById[i];if(b.locked===0)r.push({id:b.id,name:b.name,price:b.getPrice(),amount:b.amount,cps:b.storedCps||0.1,totalCps:b.storedTotalCps||0});}return r;"
            )
            or []
        )
    except:
        return []


def buy_building(driver, bid):
    try:
        return bool(
            driver.execute_script(
                f"var b=Game.ObjectsById[{bid}];if(b&&Game.cookies>=b.getPrice()){{b.buy(1);return true;}}return false;"
            )
        )
    except:
        return False


def get_stats(driver):
    try:
        return (
            driver.execute_script(
                "return{cookies:Game.cookies,cps:Game.cookiesPs,earned:Game.cookiesEarned,buildings:Game.BuildingsOwned,upgrades:Game.UpgradesOwned,clicks:Game.cookieClicks||0};"
            )
            or {}
        )
    except:
        return {}


def classify_upgrade(upgrade):
    name = upgrade.get("name", "").lower()
    desc = upgrade.get("desc", "").lower()
    building_tie = upgrade.get("buildingTie", "").lower()
    for keyword in CLICK_KEYWORDS:
        if keyword in name or keyword in desc:
            return "click"
    for keyword in GOLDEN_KEYWORDS:
        if keyword in name or keyword in desc:
            return "golden"
    if building_tie:
        return "cps"
    for building in BUILDING_NAMES:
        if building in name or building in desc:
            return "cps"
    if "cookie" in desc and (
        "production" in desc or "twice" in desc or "double" in desc
    ):
        return "cps"
    return "other"


def get_upgrade_priority(upgrade, cookies, cps):
    category = classify_upgrade(upgrade)
    price = upgrade.get("price", float("inf"))
    base_priority = {"click": 1, "golden": 2, "cps": 3, "other": 4}
    priority = base_priority.get(category, 5)
    if price <= cookies:
        priority -= 0.5
    if cps > 0:
        estimated_payback = price / (cps * 0.1)
        if estimated_payback < 60:
            priority -= 1
        elif estimated_payback > 300:
            priority += 1
        time_to_afford = price / cps
        if time_to_afford < 30:
            priority -= 0.3
        elif time_to_afford > 120:
            priority += 0.5
    return (priority, price)


def buy_best_upgrade(driver, cookies, cps):
    upgrades = get_upgrades(driver)
    if not upgrades:
        return False
    affordable = [
        u
        for u in upgrades
        if u.get("canBuy") and u.get("price", float("inf")) <= cookies
    ]
    if not affordable:
        return False
    affordable.sort(key=lambda u: get_upgrade_priority(u, cookies, cps))
    best = affordable[0]
    category = classify_upgrade(best)
    if buy_upgrade(driver, best["id"]):
        tag = {
            "click": "[CLICK]",
            "golden": "[GOLD]",
            "cps": "[CPS]",
            "other": "[OTHER]",
        }.get(category, "[UPG]")
        print(f"Bought {tag} {best['name']} ({best['price']:,.0f})")
        return True
    return False


def buy_best_building(driver, cookies, cps):
    buildings = get_buildings(driver)
    if not buildings:
        return False
    best = None
    best_payback = float("inf")
    for b in buildings:
        price = b.get("price", float("inf"))
        building_cps = b.get("cps", 0)
        if price <= cookies and building_cps > 0:
            payback = price / building_cps
            if payback < best_payback:
                best_payback = payback
                best = b
    if best and best_payback < MAX_PAYBACK_SECONDS:
        if buy_building(driver, best["id"]):
            print(
                f"Bought {best['name']} ({best['price']:,.0f}, payback: {best_payback:.0f}s)"
            )
            return True
    return False


def main_loop(driver, runtime=RUNTIME_SECONDS):
    print("\n" + "=" * 60)
    print("COOKIE CLICKER BOT v3.0 - Smart Upgrade Buying")
    print("=" * 60)
    print(
        f"Runtime: {'Infinite' if runtime <= 0 else f'{runtime}s ({runtime//60}min)'}"
    )
    print(f"Clicks per loop: {CLICK_BATCH}")
    print("=" * 60 + "\n")
    start = time.time()
    last_status = start
    last_buy = start
    has_cursor = False
    try:
        while runtime <= 0 or (time.time() - start) < runtime:
            elapsed = time.time() - start
            click_cookie(driver, CLICK_BATCH)
            click_golden(driver)
            cookies = get_cookies(driver)
            cps = get_cps(driver)
            if time.time() - last_buy >= BUY_CHECK_INTERVAL:
                last_buy = time.time()
                if not has_cursor:
                    buildings = get_buildings(driver)
                    for b in buildings:
                        if b["id"] == 0:
                            if cookies >= b["price"]:
                                if buy_building(driver, 0):
                                    has_cursor = True
                                    print(f"Bought first Cursor for {b['price']:.0f}!")
                            else:
                                if int(elapsed) % 5 == 0:
                                    print(
                                        f"Saving for Cursor: {cookies:.0f}/{b['price']:.0f}"
                                    )
                            break
                else:
                    if buy_best_upgrade(driver, cookies, cps):
                        cookies = get_cookies(driver)
                    buy_best_building(driver, cookies, cps)
            if time.time() - last_status >= STATUS_INTERVAL:
                last_status = time.time()
                stats = get_stats(driver)
                mins, secs = divmod(int(elapsed), 60)
                hours, mins = divmod(mins, 60)
                time_str = f"{hours}h{mins:02d}m" if hours else f"{mins}m{secs:02d}s"
                print(
                    f"[{time_str}] Cookies: {cookies:,.0f} | CpS: {cps:,.1f} | Buildings: {stats.get('buildings', 0)} | Upgrades: {stats.get('upgrades', 0)}"
                )
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopped by user")
    print("\n" + "=" * 60)
    print("SESSION COMPLETE")
    print("=" * 60)
    stats = get_stats(driver)
    elapsed = time.time() - start
    mins, secs = divmod(int(elapsed), 60)
    print(f"Time played: {mins}m {secs}s")
    print(f"Total earned: {stats.get('earned', 0):,.0f}")
    print(f"Final CpS: {stats.get('cps', 0):,.1f}")
    print(f"Buildings owned: {stats.get('buildings', 0)}")
    print(f"Upgrades owned: {stats.get('upgrades', 0)}")
    print(f"Total clicks: {stats.get('clicks', 0):,.0f}")
    print("=" * 60)


def main():
    print("Cookie Clicker Bot v3.0")
    print("Press Ctrl+C to stop at any time\n")
    driver = setup_driver()
    try:
        main_loop(driver, RUNTIME_SECONDS)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("\nPress Enter to close browser...")
        input()
        driver.quit()


if __name__ == "__main__":
    main()
