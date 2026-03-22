from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error, json, time

# --- CONFIGURATION ---
TOKEN = "a729a0ed3b8f5ca37e5b8f95a9fa61d0"
TARGET = "https://24hcode2026.plaiades.fr"
PORT = 8765

class HackathonProxy(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def _proxy(self, method):
        # Lecture du corps de la requête venant du JS
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else None

        # Préparation de la requête vers le serveur officiel
        req = urllib.request.Request(
            TARGET + self.path,
            data=body,
            method=method,
            headers={
                'Authorization': f'Bearer {TOKEN}',
                'Content-Type': 'application/json'
            }
        )

        try:
            with urllib.request.urlopen(req) as r:
                data = r.read()
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(data)
            print(f"✅ {method} {self.path} - SUCCESS")
        except urllib.error.HTTPError as e:
            err_msg = e.read()
            self.send_response(e.code); self._cors(); self.end_headers()
            self.wfile.write(err_msg)
            print(f"❌ {method} {self.path} - ERROR {e.code}: {err_msg.decode()}")

    def do_GET(self): self._proxy('GET')
    def do_POST(self): self._proxy('POST')

if __name__ == "__main__":
    print(f"🚀 PROXY ACTIF sur http://localhost:{PORT}")
    print(f"📡 Cible : {TARGET}")
    HTTPServer(('localhost', PORT), HackathonProxy).serve_forever()