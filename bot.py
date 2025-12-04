"""
Cookie Clicker Bot v3.2
Główny plik - wersja pure Python (bez JS)
"""

import time

from config import RUNTIME_SECONDS, CLICK_BATCH, STATUS_INTERVAL, BUY_CHECK_INTERVAL
from browser import setup_driver
from game_api import (
    get_game_state,
    get_cursor_price,
    get_stats,
    get_buildings,
    buy_building,
)
from buying import buy_best_upgrade, buy_best_building


def format_time(seconds):
    """formatuje sekundy na 5m30s albo 1h05m"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def main_loop(driver, runtime=RUNTIME_SECONDS):
    """główna pętla bota"""
    print("\n" + "=" * 60)
    print("COOKIE CLICKER BOT v3.2 (Pure Python)")
    print("=" * 60)
    print(
        f"Czas działania: {'bez limitu' if runtime <= 0 else f'{runtime}s ({runtime//60}min)'}"
    )
    print(f"Kliknięć na cykl: {CLICK_BATCH}")
    print("=" * 60 + "\n")

    start = time.time()
    last_status = start
    last_buy = start
    last_cursor_msg = 0

    has_cursor = False
    cursor_price = get_cursor_price(driver)

    try:
        while runtime <= 0 or (time.time() - start) < runtime:
            now = time.time()
            elapsed = now - start

            # klika ciastko, zbiera golden cookies, pobiera stan
            state = get_game_state(driver)
            cookies, cps = state["cookies"], state["cps"]

            if state["golden"] > 0:
                print("Złote ciastko zebrane!")

            # sprawdzamy zakupy
            if now - last_buy >= BUY_CHECK_INTERVAL:
                last_buy = now

                if not has_cursor:
                    # na początku zbieramy na pierwszy kursor
                    if cookies >= cursor_price:
                        buildings = get_buildings(driver)
                        if buildings:
                            cursor = buildings[0]  # pierwszy budynek to Cursor
                            if buy_building(driver, cursor):
                                has_cursor = True
                                print(f"Kupiłem pierwszy Cursor za {cursor_price:.0f}!")
                    elif now - last_cursor_msg >= 5:
                        last_cursor_msg = now
                        print(f"Zbieram na Cursor: {cookies:.0f}/{cursor_price:.0f}")
                else:
                    # mamy kursor - kupujemy co najlepsze
                    buy_best_upgrade(driver, cookies, cps)
                    buy_best_building(driver, cookies, cps)

            # status co jakiś czas
            if now - last_status >= STATUS_INTERVAL:
                last_status = now
                stats = get_stats(driver)
                print(
                    f"[{format_time(elapsed)}] Cookies: {cookies:,.0f} | CpS: {cps:,.1f} | Budynki: {stats.get('buildings', 0)} | Ulepszenia: {stats.get('upgrades', 0)}"
                )

            # mały delay między iteracjami
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nZatrzymano (Ctrl+C)")

    # podsumowanie
    print("\n" + "=" * 60)
    print("KONIEC SESJI")
    print("=" * 60)
    stats = get_stats(driver)
    print(f"Czas gry: {format_time(time.time() - start)}")
    print(f"Cookies: {stats.get('cookies', 0):,.0f}")
    print(f"CpS: {stats.get('cps', 0):,.1f}")
    print(f"Budynków: {stats.get('buildings', 0)}")
    print(f"Ulepszeń: {stats.get('upgrades', 0)}")
    print("=" * 60)


def main():
    print("Cookie Clicker Bot v3.2 (Pure Python)")
    print("Ctrl+C żeby zatrzymać\n")

    driver = setup_driver()
    try:
        main_loop(driver, RUNTIME_SECONDS)
    except Exception as e:
        print(f"Błąd: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\nEnter żeby zamknąć przeglądarkę...")
        input()
        driver.quit()


if __name__ == "__main__":
    main()
