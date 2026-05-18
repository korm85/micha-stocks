#!/usr/bin/env python3
"""Simple static file server that strips a URL prefix for reverse proxy compatibility.

Usage: python3 serve_deck.py [port=8515] [prefix=/deck/]
Serves files from the deck/dist/ directory, stripping /deck/ from request paths.
"""
import os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8515
PREFIX = sys.argv[2] if len(sys.argv) > 2 else '/deck/'

DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')

class DeckHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Strip the prefix from the request path
        if path.startswith(PREFIX):
            path = path[len(PREFIX.rstrip('/')):]
        # Ensure we serve from dist/
        rel_path = SimpleHTTPRequestHandler.translate_path(self, path)
        return rel_path

    def do_GET(self):
        # Handle trailing slash → serve index.html
        if self.path == PREFIX or self.path == PREFIX.rstrip('/'):
            self.path = PREFIX.rstrip('/') + '/index.html'
        return super().do_GET()

    def log_message(self, format, *args):
        # Quieter logging
        sys.stderr.write(f"[deck] {self.client_address[0]} - {format % args}\n")

os.chdir(DIST_DIR)
server = HTTPServer(('0.0.0.0', PORT), DeckHandler)
print(f"Serving deck from {DIST_DIR} on port {PORT} with prefix '{PREFIX}'")
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.shutdown()
