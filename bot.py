"""
Cookie Clicker Bot v4.0
Algorytm NPV (Net Present Value) z uwzględnieniem horyzontu czasowego
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


# =============================================================================
# FORMATOWANIE
# =============================================================================

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


# =============================================================================
# ALGORYTM DECYZYJNY v4.0 - NPV (Net Present Value)
# =============================================================================

# Bazowy CPS dla każdego typu budynku (Cookie Clicker wiki)
# Indeks = ID budynku: 0=Cursor, 1=Grandma, 2=Farm, 3=Mine, 4=Factory, 5=Bank...
BASE_CPS = [
    0.1,        # 0: Cursor
    1,          # 1: Grandma  
    8,          # 2: Farm
    47,         # 3: Mine
    260,        # 4: Factory
    1400,       # 5: Bank
    7800,       # 6: Temple
    44000,      # 7: Wizard Tower
    260000,     # 8: Shipment
    1600000,    # 9: Alchemy Lab
    10000000,   # 10: Portal
    65000000,   # 11: Time Machine
    430000000,  # 12: Antimatter Condenser
    2900000000, # 13: Prism
    21000000000 # 14: Chancemaker
]


def get_building_cps(building_id):
    """Zwraca bazowy CPS dla budynku"""
    if building_id < len(BASE_CPS):
        return BASE_CPS[building_id]
    # Dla nieznanych budynków - ekstrapolacja
    return BASE_CPS[-1] * (2 ** (building_id - len(BASE_CPS) + 1))


def evaluate_building(building, remaining_time, current_cps, current_cookies):
    """
    Oblicza NPV (Net Present Value) budynku w pozostałym horyzoncie.
    
    NPV = zysk_do_końca - cena
        = (remaining_time - payback_time) * cps_gain - price
        = remaining_time * cps_gain - price - payback_time * cps_gain
        = remaining_time * cps_gain - price - price  (bo payback = price/cps_gain)
        = remaining_time * cps_gain - 2 * price
    
    Ale prostsze: NPV = (czas_po_zwrocie) * cps_gain
    
    Returns: dict z score, payback, npv, reason
    """
    price = building.get("price", float("inf"))
    building_id = building.get("id", 0)
    name = building.get("name", f"Building_{building_id}")
    
    if price <= 0 or price == float("inf"):
        return {"score": -float("inf"), "reason": "invalid price"}
    
    cps_gain = get_building_cps(building_id)
    
    # Czas zwrotu
    payback = price / cps_gain if cps_gain > 0 else float("inf")
    
    # Ile czasu budynek będzie "zarabiać" po zwrocie
    earning_time = remaining_time - payback
    
    if earning_time <= 0:
        # Budynek nie zdąży się zwrócić
        return {
            "score": -float("inf"),
            "name": name,
            "price": price,
            "payback": payback,
            "npv": -price,  # Czysta strata
            "reason": f"payback {payback:.0f}s > remaining {remaining_time:.0f}s"
        }
    
    # NPV = ile cookies NETTO zarobi do końca horyzontu
    npv = earning_time * cps_gain - price
    
    # Alternatywna metryka: % horyzontu który będzie zarabiać
    efficiency = earning_time / remaining_time if remaining_time > 0 else 0
    
    # Score łączy NPV z efektywnością
    # Preferujemy wysokie NPV, ale też krótki payback (szybszy compound)
    score = npv * efficiency
    
    return {
        "score": score,
        "name": name,
        "price": price,
        "cps_gain": cps_gain,
        "payback": payback,
        "npv": npv,
        "efficiency": efficiency,
        "earning_time": earning_time,
        "reason": "ok"
    }


def evaluate_waiting(buildings, remaining_time, current_cps, current_cookies):
    """
    Sprawdza czy warto poczekać na droższy budynek.
    
    Porównuje: kupić teraz vs poczekać X sekund i kupić lepszy.
    """
    best_wait_option = None
    best_wait_score = -float("inf")
    
    # Szacunkowy przychód na sekundę (CPS + klikanie ~15/s * 1 cookie/click)
    income_per_sec = current_cps + 15
    
    for building in buildings:
        price = building.get("price", float("inf"))
        if price == float("inf") or price <= current_cookies:
            continue  # Już nas stać lub invalid
        
        # Ile sekund musimy czekać
        wait_time = (price - current_cookies) / income_per_sec if income_per_sec > 0 else float("inf")
        
        if wait_time > remaining_time * 0.3:
            continue  # Za długo czekać
        
        # Oceń budynek po czasie czekania
        future_remaining = remaining_time - wait_time
        eval_result = evaluate_building(building, future_remaining, current_cps, price)
        
        if eval_result["score"] > best_wait_score:
            best_wait_score = eval_result["score"]
            best_wait_option = {
                "building": building,
                "wait_time": wait_time,
                "eval": eval_result
            }
    
    return best_wait_option


def find_best_purchase(driver, cookies, cps, remaining_time):
    """
    Główna funkcja decyzyjna v4.0
    
    Strategia:
    1. Ulepszenia ZAWSZE mają priorytet (mnożniki są OP)
    2. Dla budynków: wybierz ten z najwyższym NPV score
    3. Sprawdź czy warto poczekać na lepszy budynek
    4. Nie kupuj jeśli payback > 50% remaining_time
    """
    
    # === 1. ULEPSZENIA - PRIORYTET ===
    upgrades = get_upgrades(driver)
    affordable_upgrades = [u for u in upgrades if u.get("canBuy")]
    
    if affordable_upgrades:
        return ("upgrade", affordable_upgrades[0], {"reason": "upgrade priority"})
    
    # === 2. OCEŃ BUDYNKI ===
    buildings = get_buildings(driver)
    affordable = [b for b in buildings if b.get("canBuy") and b.get("price", float("inf")) <= cookies]
    
    if not affordable:
        return (None, None, {"reason": "nothing affordable"})
    
    # Oceń wszystkie dostępne budynki
    evaluations = []
    for building in affordable:
        eval_result = evaluate_building(building, remaining_time, cps, cookies)
        eval_result["building"] = building
        evaluations.append(eval_result)
    
    # Sortuj po score (malejąco)
    evaluations.sort(key=lambda x: x["score"], reverse=True)
    
    # Loguj top 3 dla debugowania
    # (zakomentowane w produkcji)
    # for i, e in enumerate(evaluations[:3]):
    #     print(f"  #{i+1} {e['name']}: score={e['score']:.0f}, npv={e['npv']:.0f}, payback={e['payback']:.0f}s")
    
    best = evaluations[0] if evaluations else None
    
    if not best or best["score"] <= 0:
        return (None, None, {"reason": f"best score {best['score'] if best else 'N/A'} <= 0"})
    
    # === 3. SPRAWDŹ CZY WARTO CZEKAĆ ===
    wait_option = evaluate_waiting(buildings, remaining_time, cps, cookies)
    
    if wait_option:
        wait_score = wait_option["eval"]["score"]
        wait_time = wait_option["wait_time"]
        
        # Czekaj jeśli: lepszy score I czekanie < 30s I score > 1.5x obecny
        if wait_score > best["score"] * 1.5 and wait_time < 30:
            return (None, None, {
                "reason": f"waiting {wait_time:.0f}s for {wait_option['building'].get('name')} (score {wait_score:.0f} vs {best['score']:.0f})"
            })
    
    # === 4. FILTR BEZPIECZEŃSTWA ===
    # Nie kupuj jeśli payback > 50% remaining_time
    max_payback = remaining_time * 0.5
    if best["payback"] > max_payback:
        return (None, None, {
            "reason": f"payback {best['payback']:.0f}s > limit {max_payback:.0f}s (50% of {remaining_time:.0f}s)"
        })
    
    return ("building", best["building"], best)


# =============================================================================
# WĄTEK KLIKAJĄCY
# =============================================================================

def clicker_thread(driver, running_flag, click_count):
    """Osobny wątek do ciągłego klikania"""
    cookie = None
    
    while running_flag[0]:
        try:
            if cookie is None:
                cookie = driver.find_element("id", "bigCookie")
            
            for _ in range(CLICK_BATCH):
                if not running_flag[0]:
                    break
                cookie.click()
                click_count[0] += 1
                
        except Exception:
            cookie = None
            time.sleep(0.01)


# =============================================================================
# GŁÓWNA PĘTLA
# =============================================================================

def main_loop(driver, runtime=RUNTIME_SECONDS):
    """główna pętla bota"""
    print("\n" + "=" * 60)
    print("COOKIE CLICKER BOT v4.0 (NPV Algorithm)")
    print("=" * 60)
    print(f"Horyzont: {'bez limitu' if runtime <= 0 else f'{runtime}s ({runtime//60}min)'}")
    print(f"Klikniec na batch: {CLICK_BATCH}")
    print(f"Strategia: NPV (Net Present Value) z lookahead")
    print("=" * 60 + "\n")

    start = time.time()
    last_status = start
    last_buy = start
    click_count = [0]
    running_flag = [True]
    
    total_spent = 0
    buildings_bought = 0
    upgrades_bought = 0
    decisions_skipped = 0

    # Uruchom wątek klikający
    clicker = threading.Thread(target=clicker_thread, args=(driver, running_flag, click_count), daemon=True)
    clicker.start()
    print("Watek klikajacy uruchomiony!")

    try:
        while runtime <= 0 or (time.time() - start) < runtime:
            now = time.time()
            elapsed = now - start
            remaining = runtime - elapsed if runtime > 0 else 3600  # default 1h jeśli bez limitu

            # Zbieraj złote ciastka
            try:
                golden = click_golden_cookies(driver)
                if golden > 0:
                    print(f"*** ZLOTE CIASTKO! ***")
            except:
                pass

            # Sprawdzamy zakupy
            if now - last_buy >= BUY_CHECK_INTERVAL:
                last_buy = now
                
                try:
                    cookies = get_cookies_count(driver)
                    cps = get_cps(driver)
                    
                    # Znajdź najlepszy zakup z uwzględnieniem horyzontu
                    purchase_type, item, info = find_best_purchase(driver, cookies, cps, remaining)
                    
                    if purchase_type == "upgrade":
                        if buy_upgrade(driver, item):
                            upgrades_bought += 1
                            print(f">> UPGRADE kupiony!")
                    
                    elif purchase_type == "building":
                        price = item.get("price", 0)
                        name = item.get("name", "?")
                        payback = info.get("payback", 0)
                        npv = info.get("npv", 0)
                        
                        if buy_building(driver, item):
                            buildings_bought += 1
                            total_spent += price
                            print(f"+ {name} ({format_number(price)}) [zwrot: {payback:.0f}s, NPV: {format_number(npv)}]")
                    
                    else:
                        # Decyzja: nie kupować (czekamy lub nie opłaca się)
                        decisions_skipped += 1
                        # Opcjonalnie: loguj powód co 10 pominięć
                        # if decisions_skipped % 10 == 1:
                        #     print(f"   [skip] {info.get('reason', '?')}")
                        
                except Exception as e:
                    pass

            # Status co jakiś czas
            if now - last_status >= STATUS_INTERVAL:
                last_status = now
                try:
                    cookies = get_cookies_count(driver)
                    cps = get_cps(driver)
                    cps_display = format_number(cps) if cps else "0"
                    clicks_per_sec = click_count[0] / elapsed if elapsed > 0 else 0
                    remaining_display = format_time(remaining) if runtime > 0 else "inf"
                    
                    print(f"[{format_time(elapsed)}] Cookies: {format_number(cookies)} | CpS: {cps_display}/s | Klik/s: {clicks_per_sec:.0f} | B:{buildings_bought} U:{upgrades_bought} | Left: {remaining_display}")
                except:
                    pass

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
        print(f"Budynkow: {buildings_bought}")
        print(f"Ulepszen: {upgrades_bought}")
        print(f"Wydano: {format_number(total_spent)}")
        print(f"Pominiete decyzje: {decisions_skipped}")
    except:
        pass
    print("=" * 60)


def main():
    print("Cookie Clicker Bot v4.0 (NPV Algorithm)")
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
