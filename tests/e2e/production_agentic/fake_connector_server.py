import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class FakeConnectorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "success",
            "received": json.loads(post_data.decode("utf-8"))
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))

def run_server(port):
    server = HTTPServer(('127.0.0.1', port), FakeConnectorHandler)
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    run_server(port)
