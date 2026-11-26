"""Local server for index.html. Run: python Track.py  (optional: python Track.py 8080)"""
import json
import math
import re
import shutil
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
 
HOST = "127.0.0.1"  # only this device can connect
PAGE = Path(__file__).resolve().parent / "index.html"
 
 
def valid_imei(imei):
    """15 digits that pass the Luhn check (same rule as the web page)."""
    if not re.fullmatch(r"[0-9]{15}", imei):
        return False
    total = 0
    for i, char in enumerate(imei):
        n = int(char) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0
 
 
class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
 
    def reply(self, status, data):
        self.send(status, json.dumps(data).encode())
 
    def do_GET(self):
        # Reject requests that arrive under any other host name
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("localhost", "127.0.0.1"):
            return self.reply(403, {"error": "localhost only"})
 
        url = urlsplit(self.path)
        if url.path in ("/", "/index.html"):
            try:
                return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            except OSError:
                return self.reply(404, {"error": "index.html not found next to Track.py"})
        if url.path == "/location":
            return self.location(parse_qs(url.query))
        self.reply(404, {"error": "not found"})
 
    def location(self, query):
        try:
            imei = query["imei"][0]
            lat = float(query["lat"][0])
            lon = float(query["lon"][0])
        except (KeyError, ValueError):
            return self.reply(400, {"error": "imei, lat and lon are required"})
        if not (valid_imei(imei) and math.isfinite(lat) and math.isfinite(lon)
                and -90 <= lat <= 90 and -180 <= lon <= 180):
            return self.reply(400, {"error": "invalid values"})
 
        maps = f"https://www.google.com/maps?q={lat},{lon}"
        print(f"\n\033[92mLocation received\033[0m\n  IMEI : {imei}"
              f"\n  GPS  : {lat:.6f}, {lon:.6f}\n  Map  : {maps}", flush=True)
        self.reply(200, {"ok": True, "map": maps})
 
    def log_message(self, *args):
        pass  # keep the terminal clean
 
 
def open_browser(url):
    if shutil.which("termux-open-url"):
        subprocess.run(["termux-open-url", url], check=False)
    else:
        webbrowser.open(url)
 
 
def main():
    try:
        port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
        server = ThreadingHTTPServer((HOST, port), Handler)
    except (ValueError, OverflowError, OSError) as error:
        sys.exit(f"Could not start server: {error}\nTry another port: python Track.py 8080")
    if not PAGE.is_file():
        sys.exit("index.html not found. Keep it in the same folder as Track.py.")
 
    url = f"http://localhost:{port}"
    print(f"IMEI Tracker running at {url}\nPress Ctrl+C to stop.", flush=True)
    open_browser(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
 
 
if __name__ == "__main__":
    main()
