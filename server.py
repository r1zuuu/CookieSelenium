"""
Serwer HTTP do hostowania gry lokalnie
"""

import os
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

from config import SERVER_PORT, GAME_PATH


class QuietHandler(SimpleHTTPRequestHandler):
    """handler który nie spamuje logami w konsoli"""

    def log_message(self, format, *args):
        pass


def start_local_server(port=SERVER_PORT):
    """odpala lokalny serwer HTTP żeby gra mogła się załadować"""

    def run_server():
        server_dir = os.path.abspath(GAME_PATH)
        if not os.path.exists(server_dir):
            print(f"ERROR: nie znaleziono folderu: {server_dir}")
            return

        print(f"Startuję serwer w: {server_dir}")
        os.chdir(server_dir)

        server = HTTPServer(("localhost", port), QuietHandler)
        print(f"Serwer działa na http://localhost:{port}")
        server.serve_forever()

    # daemon=True -> thread umrze razem z głównym procesem
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    return f"http://localhost:{port}"
