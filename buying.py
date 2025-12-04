"""
Logika kupowania - wybór najlepszych ulepszeń i budynków
"""

from config import MAX_PAYBACK_SECONDS
from game_api import get_upgrades, get_buildings, buy_upgrade, buy_building


def buy_best_upgrade(driver, cookies, cps):
    """kupuje pierwsze dostępne ulepszenie"""
    upgrades = get_upgrades(driver)
    if not upgrades:
        return False

    # bierzemy te które możemy kupić
    affordable = [u for u in upgrades if u.get("canBuy")]
    if not affordable:
        return False

    # kupujemy pierwsze z brzegu (są posortowane w grze)
    best = affordable[0]
    if buy_upgrade(driver, best):
        print(f"Kupiłem ulepszenie!")
        return True
    return False


def buy_best_building(driver, cookies, cps):
    """kupuje najtańszy budynek na który nas stać"""
    buildings = get_buildings(driver)
    if not buildings:
        return False

    # tylko te które możemy kupić
    affordable = [
        b
        for b in buildings
        if b.get("canBuy") and b.get("price", float("inf")) <= cookies
    ]
    if not affordable:
        return False

    # najtańszy
    best = min(affordable, key=lambda b: b["price"])

    if buy_building(driver, best):
        print(f"Kupiłem {best['name']} ({best['price']:,.0f})")
        return True
    return False
