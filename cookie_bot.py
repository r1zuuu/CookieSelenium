import time
import os
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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
        c = driver.execute_script(
            "var c=0;if(Game.shimmers)for(var i=Game.shimmers.length-1;i>=0;i--){Game.shimmers[i].pop();c++;}return c;"
        )
        if c and c > 0:
            print(f"Golden cookie clicked!")
    except:
        pass


def get_upgrades(driver):
    try:
        return (
            driver.execute_script(
                "var r=[];for(var i in Game.UpgradesInStore){var u=Game.UpgradesInStore[i];if(u.pool!=='toggle'&&u.pool!=='tech')r.push({id:u.id,name:u.name,price:u.getPrice(),canBuy:u.canBuy()});}return r;"
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
                "var r=[];for(var i in Game.ObjectsById){var b=Game.ObjectsById[i];if(b.locked===0)r.push({id:b.id,name:b.name,price:b.getPrice(),amount:b.amount,cps:b.storedCps||0.1});}return r;"
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
                "return{cookies:Game.cookies,cps:Game.cookiesPs,earned:Game.cookiesEarned,buildings:Game.BuildingsOwned,upgrades:Game.UpgradesOwned};"
            )
            or {}
        )
    except:
        return {}


def main_loop(driver, runtime=600):
    print("\n" + "=" * 50)
    print("COOKIE CLICKER BOT - JS API")
    print("=" * 50 + "\n")
    start = time.time()
    last_status = start
    last_buy = start
    has_cursor = False
    while time.time() - start < runtime:
        try:
            click_cookie(driver, 10)
            click_golden(driver)
            cookies = get_cookies(driver)
            if time.time() - last_buy >= 0.5:
                last_buy = time.time()
                if not has_cursor:
                    for b in get_buildings(driver):
                        if b["id"] == 0:
                            if cookies >= b["price"]:
                                if buy_building(driver, 0):
                                    has_cursor = True
                                    print(f"Bought Cursor for {b['price']:.0f}!")
                            break
                else:
                    for u in get_upgrades(driver):
                        if u["canBuy"] and cookies >= u["price"]:
                            if buy_upgrade(driver, u["id"]):
                                print(f"Bought upgrade: {u['name']} ({u['price']:.0f})")
                                cookies -= u["price"]
                    best = None
                    best_pb = float("inf")
                    for b in get_buildings(driver):
                        if b["price"] <= cookies and b["cps"] > 0:
                            pb = b["price"] / b["cps"]
                            if pb < best_pb:
                                best_pb = pb
                                best = b
                    if best and best_pb < 300:
                        if buy_building(driver, best["id"]):
                            print(
                                f"Bought {best['name']} ({best['price']:.0f}, pb:{best_pb:.0f}s)"
                            )
            if time.time() - last_status >= 10:
                last_status = time.time()
                s = get_stats(driver)
                print(
                    f"[{time.time()-start:.0f}s] Cookies:{cookies:,.0f} CpS:{get_cps(driver):,.1f} B:{s.get('buildings',0)} U:{s.get('upgrades',0)}"
                )
            time.sleep(0.05)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
    print("\nSession complete!")
    s = get_stats(driver)
    print(f"Earned: {s.get('earned',0):,.0f}")


def main():
    print("Cookie Clicker Bot v2.0")
    driver = setup_driver()
    try:
        main_loop(driver, 600)
    except:
        pass
    finally:
        print("Press Enter to close...")
        input()
        driver.quit()


if __name__ == "__main__":
    main()
