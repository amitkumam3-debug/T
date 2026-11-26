
import json
import math
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

# Render needs 0.0.0.0
HOST = "0.0.0.0"

# Render provides PORT automatically
PORT = int(os.environ.get("PORT", 8000))

PAGE = Path(__file__).resolve().parent / "index.html"


def valid_imei(imei):
    """Check for a valid 15-digit IMEI using the Luhn algorithm."""
    if not re.fullmatch(r"[0-9]{15}", imei):
        return False

    total = 0

    for i, char in enumerate(imei):
        n = int(char)

        if i % 2:
            n *= 2
            if n > 9:
                n -= 9

        total += n

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
        self.send(
            status,
            json.dumps(data).encode("utf-8")
        )

    def do_GET(self):

        url = urlsplit(self.path)

        # Serve index.html
        if url.path in ("/", "/index.html"):
            try:
                return self.send(
                    200,
                    PAGE.read_bytes(),
                    "text/html; charset=utf-8"
                )
            except OSError:
                return self.reply(
                    404,
                    {
                        "error":
                        "index.html not found next to app.py"
                    }
                )

        # Receive GPS coordinates
        if url.path == "/location":
            return self.location(parse_qs(url.query))

        return self.reply(
            404,
            {"error": "not found"}
        )

    def location(self, query):

        try:
            imei = query["imei"][0]
            lat = float(query["lat"][0])
            lon = float(query["lon"][0])

        except (KeyError, ValueError):
            return self.reply(
                400,
                {
                    "error":
                    "imei, lat and lon are required"
                }
            )

        # Validate data
        if not (
            valid_imei(imei)
            and math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            return self.reply(
                400,
                {"error": "invalid values"}
            )

        # Google Maps link
        maps = (
            f"https://www.google.com/maps"
            f"?q={lat},{lon}"
        )

        print(
            "\nLocation received"
            f"\nIMEI : {imei}"
            f"\nGPS  : {lat:.6f}, {lon:.6f}"
            f"\nMap  : {maps}",
            flush=True
        )

        return self.reply(
            200,
            {
                "ok": True,
                "map": maps
            }
        )

    def log_message(self, *args):
        # Keep terminal logs clean
        pass


def open_browser(url):

    # Render does not have a local browser
    if os.environ.get("RENDER") == "true":
        return

    if shutil.which("termux-open-url"):
        subprocess.run(
            ["termux-open-url", url],
            check=False
        )
    else:
        webbrowser.open(url)


def main():

    try:

        server = ThreadingHTTPServer(
            (HOST, PORT),
            Handler
        )

    except (ValueError, OverflowError, OSError) as error:

        sys.exit(
            f"Could not start server: {error}"
        )

    # Check frontend exists
    if not PAGE.is_file():

        sys.exit(
            "index.html not found. "
            "Keep it in the same folder as app.py."
        )

    print(
        f"Server running on {HOST}:{PORT}",
        flush=True
    )

    # Only opens browser when running locally
    open_browser(
        f"http://localhost:{PORT}"
    )

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print(
            "\nServer stopped.",
            flush=True
        )

    finally:

        server.server_close()


if __name__ == "__main__":
    main()
