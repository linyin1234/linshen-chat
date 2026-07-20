#!/usr/bin/env python3
"""Simple HTTP server for web_search + web_fetch on port 3005"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, urllib.request, re, sys

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        
        if self.path == '/web_search':
            q = body.get('query', '')
            url = "https://html.duckduckgo.com/html/?q=" + urllib.request.quote(q)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read().decode(errors='replace')
            results = []
            parts = html.split('class="result__body"')
            for p in parts[1:8]:
                tm = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)<', p)
                sm = re.search(r'class="result__snippet"[^>]*>([^<]+)<', p)
                if tm:
                    results.append({"title": tm.group(2).strip(), "url": tm.group(1),
                                   "snippet": sm.group(1).strip()[:200] if sm else ""})
            self.send_json({"results": results})
            
        elif self.path == '/web_fetch':
            u = body.get('url', '')
            if not u.startswith('http'):
                self.send_json({"error": "invalid url"})
                return
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode(errors='replace')
            text = re.sub(r'<script[\s\S]*?</script>', '', raw)
            text = re.sub(r'<style[\s\S]*?</style>', '', text)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            self.send_json({"content": text[:3000], "url": u, "size": len(raw)})
        else:
            self.send_json({"error": "not found"}, 404)

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

HTTPServer(('127.0.0.1', 3005), Handler).serve_forever()
