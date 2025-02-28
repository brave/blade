#!/usr/bin/python3

import ssl
import json
import csv
import os
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer


class MyHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, output_folder=None, **kwargs):
        self.output_folder = output_folder
        super().__init__(*args, **kwargs)

    def _send_cors_headers(self):
        """Helper function to add CORS headers to the response."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        """Handle POST requests."""
        self._send_cors_headers()

        # Read the content length to retrieve the data
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            # Parse the JSON data
            data = json.loads(post_data)

            # Validate all required fields
            required_fields = [
                "browser", "url", "loadTime",
                "requestStart", "responseEnd", "domInteractive",
                "domContentLoadedEventStart", "domContentLoadedEventEnd",
                "domComplete", "loadEventStart", "loadEventEnd", "duration",
                "lcpClassName", "lcpLoadTime", "lcpRenderTime"
            ]
            
            if not all(field in data for field in required_fields):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Missing required fields in JSON data')
                return

            # Get the browser name
            browser_name = data['browser']
            sanitized_browser_name = "".join(
                c if c.isalnum() or c in "-_." else "_" for c in browser_name
            )

            # Determine the filename based on browser name
            csv_filename = f"measurements_pageload_{sanitized_browser_name}.csv"

            # Resolve the output folder
            if self.output_folder:
                os.makedirs(self.output_folder, exist_ok=True)
                csv_filepath = os.path.join(self.output_folder, csv_filename)
            else:
                csv_filepath = csv_filename

            # Check if file exists
            file_exists = os.path.isfile(csv_filepath)

            # Write to the CSV file
            with open(csv_filepath, mode='a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=required_fields)
                if not file_exists:
                    writer.writeheader()

                writer.writerow({field: data[field] for field in required_fields})

            # Send a success response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')

        except Exception as e:
            # Handle errors gracefully
            print(f"Error processing request: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal server error')


def run(server_class=HTTPServer, handler_class=MyHandler, port=8443, cert="cert.pem", key="key.pem", output_folder=None):
    server_address = ('', port)

    # Custom handler to include output_folder
    def handler_factory(*args, **kwargs):
        return handler_class(*args, output_folder=output_folder, **kwargs)

    httpd = server_class(server_address, handler_factory)

    # Create SSL context and wrap the socket with SSL
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    print(f"Loading SSL certificate and key from {cert} and {key}")
    context.load_cert_chain(certfile=cert, keyfile=key)

    # Wrap the server socket with SSL
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"Starting HTTPS server on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    # To create certificates: openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
    parser = argparse.ArgumentParser(description="Start an HTTPS server.")
    parser.add_argument("--port", type=int, default=8443, help="Port to run the HTTPS server on.")
    parser.add_argument("--cert", type=str, default="cert.pem", help="Path to SSL certificate.")
    parser.add_argument("--key", type=str, default="key.pem", help="Path to SSL private key.")
    parser.add_argument("-o", "--output", type=str, help="Output folder for page load data.")
    args = parser.parse_args()

    run(port=args.port, cert=args.cert, key=args.key, output_folder=args.output)
