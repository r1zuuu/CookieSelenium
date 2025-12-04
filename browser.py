"""
Konfiguracja i inicjalizacja przeglądarki
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from config import PAGE_LOAD_TIMEOUT, GAME_READY_TIMEOUT, SERVER_PORT
from server import start_local_server


def setup_driver():
    """konfiguruje chrome'a i ładuje grę"""
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_experimental_option(
        "detach", True
    )  # nie zamykaj po zakończeniu skryptu

    server_url = start_local_server(SERVER_PORT)
    driver = webdriver.Chrome(options=options)

    # implicit wait - selenium będzie czekać na elementy
    driver.implicitly_wait(2)

    driver.get(f"{server_url}/index.html")
    print("Ładuję Cookie Clicker...")

    # czekamy na duże ciastko
    WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
        EC.presence_of_element_located((By.ID, "bigCookie"))
    )
    print("Gra załadowana!")

    # czekamy aż będzie można klikać w ciastko
    WebDriverWait(driver, GAME_READY_TIMEOUT).until(
        EC.element_to_be_clickable((By.ID, "bigCookie"))
    )
    print("Gra gotowa!")

    # wybieramy angielski jeśli jest wybór języka
    try:
        lang_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "langSelect-EN"))
        )
        lang_btn.click()
        print("Wybrałem język angielski")
        # czekamy aż strona się przeładuje
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "bigCookie"))
        )
    except TimeoutException:
        pass  # nie ma wyboru języka

    return driver
