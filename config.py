"""
Konfiguracja bota - tu zmieniasz ustawienia
"""

# === GŁÓWNE USTAWIENIA ===
RUNTIME_SECONDS = 3600  # ile sekund ma działać bot (0 = bez limitu)
CLICK_BATCH = 15  # ile razy klikać ciastko na raz
STATUS_INTERVAL = 10  # co ile sekund pokazywać status
BUY_CHECK_INTERVAL = 0.3  # co ile sprawdzać czy coś kupić
MAX_PAYBACK_SECONDS = 300  # max czas zwrotu inwestycji dla budynków

# === SERWER ===
SERVER_PORT = 8000
GAME_PATH = "./cookieclicker"

# === TIMEOUTY ===
PAGE_LOAD_TIMEOUT = 30
GAME_READY_TIMEOUT = 30
