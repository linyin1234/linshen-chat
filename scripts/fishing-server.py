#!/usr/bin/env python3
"""Fishing game server - keeps state in memory, exposes HTTP API"""
import sys, os, json, http.server
from urllib.parse import unquote

# Add game to path
sys.path.insert(0, '/opt/linshen/scripts')

# Load once, keep in memory
try:
    import fishing
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("fishing", "/opt/linshen/scripts/fishing.py")
    fishing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fishing)

PORT = 3005

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
            return
        cmd = unquote(self.path[1:] if self.path.startswith('/') else self.path)
        if not cmd:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'no command')
            return
        try:
            result = fishing.cmd(cmd)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(result.encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'error: {e}'.encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # quiet

httpd = http.server.HTTPServer(('127.0.0.1', PORT), Handler)
print(f'Fishing server :{PORT}')
httpd.serve_forever()
