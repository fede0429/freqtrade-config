import http.server
import socketserver
from pathlib import Path

PORT = 9000
ROOT_DIR = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = Path(__file__).resolve().parent
VALIDATION_PAYLOAD = ROOT_DIR / "reports" / "operations" / "validation" / "validation_dashboard_latest.json"


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self):
        if self.path in {"/api/validation-summary", "/data/validation_dashboard_latest.json"}:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            if not VALIDATION_PAYLOAD.exists():
                self.wfile.write(b'{"error":"validation payload not found"}')
                return

            self.wfile.write(VALIDATION_PAYLOAD.read_bytes())
            return

        return super().do_GET()


with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
    actual_port = httpd.socket.getsockname()[1]
    print(f"Starting dashboard server at http://localhost:{actual_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()