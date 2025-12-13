"""
Cookie Clicker Bot v3.3
Zoptymalizowana wersja - ciągłe klikanie + inteligentne kupowanie
"""

import time
import threading

from config import RUNTIME_SECONDS, CLICK_BATCH, STATUS_INTERVAL, BUY_CHECK_INTERVAL
from browser import setup_driver
from game_api import (
    click_cookie,
    click_golden_cookies,
    get_cookies_count,
    get_cps,
    get_buildings,
    get_upgrades,
    buy_building,
    buy_upgrade,
)


def format_time(seconds):
    """formatuje sekundy na 5m30s albo 1h05m"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def format_number(n):
    """formatuje liczby czytelnie"""
    if n >= 1e12:
        return f"{n/1e12:.2f}T"
    elif n >= 1e9:
        return f"{n/1e9:.2f}B"
    elif n >= 1e6:
        return f"{n/1e6:.2f}M"
    elif n >= 1e3:
        return f"{n/1e3:.1f}K"
    else:
        return f"{n:.0f}"


def calculate_efficiency(building, cps):
    """
    Oblicza efektywność budynku według algorytmu:
    Efficiency = estimated_CPS / price
    
    Im wyższa wartość, tym lepszy zakup.
    """
    price = building.get("price", float("inf"))
    if price <= 0:
        return 0
    
    # Szacowany CPS gain na podstawie typu budynku
    building_id = building.get("id", 0)
    
    # Bazowy CPS dla każdego typu budynku (przybliżone wartości z gry)
    base_cps = [0.1, 1, 8, 47, 260, 1400, 7800, 44000, 260000, 1600000]
    
    if building_id < len(base_cps):
        estimated_cps = base_cps[building_id]
    else:
        estimated_cps = base_cps[-1] * (2 ** (building_id - len(base_cps) + 1))
    
    # Efektywność = CPS / cena
    efficiency = estimated_cps / price
    
    return efficiency


def find_best_purchase(driver, cookies, cps):
    """
    Znajduje najlepszy zakup (budynek lub ulepszenie).
    Priorytet:
    1. Ulepszenia (mnożniki) - jeśli są dostępne
    2. Budynek z najlepszą efektywnością (CPS/cena)
    """
    best_building = None
    best_efficiency = 0
    
    # Sprawdź budynki
    buildings = get_buildings(driver)
    affordable_buildings = [b for b in buildings if b.get("canBuy") and b.get("price", float("inf")) <= cookies]
    
    for building in affordable_buildings:
        eff = calculate_efficiency(building, cps)
        if eff > best_efficiency:
            best_efficiency = eff
            best_building = building
    
    # Sprawdź ulepszenia - ulepszenia mają priorytet (mnożniki są bardzo opłacalne)
    upgrades = get_upgrades(driver)
    affordable_upgrades = [u for u in upgrades if u.get("canBuy")]
    
    if affordable_upgrades:
        return ("upgrade", affordable_upgrades[0])
    
    if best_building:
        return ("building", best_building)
    
    return (None, None)


def clicker_thread(driver, running_flag, click_count):
    """Osobny wątek do ciągłego klikania - maksymalna szybkość"""
    cookie = None
    while running_flag[0]:
        try:
            if cookie is None:
                cookie = driver.find_element("id", "bigCookie")
            
            # Klikaj szybko w pętli
            for _ in range(CLICK_BATCH):
                if not running_flag[0]:
                    break
                cookie.click()
                click_count[0] += 1
        except:
            cookie = None
            time.sleep(0.01)


def main_loop(driver, runtime=RUNTIME_SECONDS):
    """główna pętla bota"""
    print("\n" + "=" * 60)
    print("COOKIE CLICKER BOT v3.3 (Optimized)")
    print("=" * 60)
    print(f"Czas działania: {'bez limitu' if runtime <= 0 else f'{runtime}s ({runtime//60}min)'}")
    print(f"Kliknięć na batch: {CLICK_BATCH}")
    print("=" * 60 + "\n")

    start = time.time()
    last_status = start
    last_buy = start
    click_count = [0]  # lista żeby można było modyfikować w wątku
    running_flag = [True]
    
    total_spent = 0
    buildings_bought = 0
    upgrades_bought = 0

    # Uruchom wątek klikający
    clicker = threading.Thread(target=clicker_thread, args=(driver, running_flag, click_count), daemon=True)
    clicker.start()
    print("Watek klikajacy uruchomiony!")

    try:
        while runtime <= 0 or (time.time() - start) < runtime:
            now = time.time()
            elapsed = now - start

            # Zbieraj złote ciastka
            try:
                golden = click_golden_cookies(driver)
                if golden > 0:
                    print(f"Zlote ciastko zebrane!")
            except:
                pass

            # Sprawdzamy zakupy co BUY_CHECK_INTERVAL
            if now - last_buy >= BUY_CHECK_INTERVAL:
                last_buy = now
                
                try:
                    cookies = get_cookies_count(driver)
                    cps = get_cps(driver)
                    
                    # Znajdź najlepszy zakup
                    purchase_type, item = find_best_purchase(driver, cookies, cps)
                    
                    if purchase_type == "upgrade":
                        if buy_upgrade(driver, item):
                            upgrades_bought += 1
                            print(f"Kupilem ulepszenie!")
                    
                    elif purchase_type == "building":
                        price = item.get("price", 0)
                        name = item.get("name", "?")
                        if buy_building(driver, item):
                            buildings_bought += 1
                            total_spent += price
                            print(f"Kupilem {name} ({format_number(price)})")
                except:
                    pass

            # Status co jakiś czas
            if now - last_status >= STATUS_INTERVAL:
                last_status = now
                try:
                    cookies = get_cookies_count(driver)
                    cps = get_cps(driver)
                    cps_display = format_number(cps) if cps else "0"
                    clicks_per_sec = click_count[0] / elapsed if elapsed > 0 else 0
                    
                    print(f"[{format_time(elapsed)}] Cookies: {format_number(cookies)} | CpS: {cps_display}/s | Klik/s: {clicks_per_sec:.0f} | Budynki: {buildings_bought} | Ulepszenia: {upgrades_bought}")
                except:
                    pass

            # Mały delay żeby nie przeciążać CPU
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nZatrzymano (Ctrl+C)")
    finally:
        running_flag[0] = False

    # Podsumowanie
    print("\n" + "=" * 60)
    print("KONIEC SESJI")
    print("=" * 60)
    try:
        cookies = get_cookies_count(driver)
        cps = get_cps(driver)
        total_time = time.time() - start
        print(f"Czas gry: {format_time(total_time)}")
        print(f"Cookies: {format_number(cookies)}")
        print(f"CpS: {format_number(cps)}/s")
        print(f"Klikniec: {format_number(click_count[0])} ({click_count[0]/total_time:.0f}/s)")
        print(f"Budynkow kupionych: {buildings_bought}")
        print(f"Ulepszen kupionych: {upgrades_bought}")
        print(f"Wydano: {format_number(total_spent)}")
    except:
        pass
    print("=" * 60)


def main():
    print("Cookie Clicker Bot v3.3 (Optimized)")
    print("Ctrl+C zeby zatrzymac\n")

    driver = setup_driver()
    try:
        main_loop(driver, RUNTIME_SECONDS)
    except Exception as e:
        print(f"Blad: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nEnter zeby zamknac przegladarke...")
        input()
        driver.quit()


if __name__ == "__main__":
    main()
