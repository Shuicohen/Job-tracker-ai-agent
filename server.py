import os
import http.server
import socketserver
import threading
from scheduler import main as scheduler_main

# Get port from environment variable (Render sets this for us)
PORT = int(os.environ.get("PORT", 8080))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'LinkedIn Job Application Tracker is running')

def run_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server running at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=scheduler_main)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Run the HTTP server (keeps the app alive on Render)
    run_server() 