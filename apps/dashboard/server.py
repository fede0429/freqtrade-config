import http.server
import socketserver
import json
import os
from pathlib import Path

PORT = 9000
ROOT_DIR = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = Path(__file__).resolve().parent
REPORTS_DIR = ROOT_DIR / "reports" / "operations" / "daily"

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self):
        if self.path == '/api/latest-report':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Find the latest JSON report
            reports = list(REPORTS_DIR.glob("*.json"))
            if not reports:
                self.wfile.write(json.dumps({"error": "No reports found"}).encode())
                return
            
            latest_report = max(reports, key=lambda p: p.stat().st_mtime)
            self.wfile.write(latest_report.read_bytes())
        else:
            return super().do_GET()

with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
    actual_port = httpd.socket.getsockname()[1]
    print(f"Starting dashboard server at http://localhost:{actual_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()
