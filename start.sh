#!/bin/bash
python3 bot.py

import threading
import http.server
import socketserver

def keep_alive():
    PORT = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

keep_alive()
