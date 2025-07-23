#!/usr/bin/python3

import ssl
import json
import csv
import os
import time
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

from libs import constants


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
        # Send response code first
        self.send_response(200)
        # Then send CORS headers
        self._send_cors_headers()
        self.end_headers()

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
                "lcpClassName", "lcpLoadTime", "lcpRenderTime", "timestamp"
            ]
            
            if not all(field in data for field in required_fields if field != "timestamp"):
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(b'Missing required fields in JSON data')
                return

            # Add timestamp
            data["timestamp"] = time.time()

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

            # Write the success response
            self.wfile.write(b'{"status": "success"}')

        except Exception as e:
            # Handle errors gracefully
            print(f"Error processing request: {e}")
            self.send_response(500)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b'Internal server error')


def run(port, cert, key, output_folder):

    # Check if output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # make paths relative to the script location
    script_location = os.path.dirname(os.path.abspath(__file__))
    cert = os.path.join(script_location, cert)
    key = os.path.join(script_location, key)

    # Check if cert and key exist
    if not os.path.exists(cert):
        raise FileNotFoundError(f"SSL certificate not found at {cert}")
    if not os.path.exists(key):
        raise FileNotFoundError(f"SSL key not found at {key}")

    server_address = ('', port)

    # Custom handler to include output_folder
    def handler_factory(*args, **kwargs):
        return MyHandler(*args, output_folder=output_folder, **kwargs)

    httpd = HTTPServer(server_address, handler_factory)

    # Create SSL context and wrap the socket with SSL
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # Enforce minimum TLS version 1.2, disabling deprecated versions
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    print(f"Loading SSL certificate and key from {cert} and {key}")
    context.load_cert_chain(certfile=cert, keyfile=key)

    # Wrap the server socket with SSL
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"Starting HTTPS server on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    # To create certificates: openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
    parser = argparse.ArgumentParser(description="Start an HTTPS server.")
    parser.add_argument("--port", type=int, default=constants.PROXY_DEFAULT_SERVER_PORT, help=f"Port to run the HTTPS server on. Default is {constants.PROXY_DEFAULT_SERVER_PORT}.")
    parser.add_argument("--cert", type=str, default=constants.PROXY_DEFAULT_CERTIFICATE_PATH, help=f"Path to SSL certificate. Default is '{constants.PROXY_DEFAULT_CERTIFICATE_PATH}'.")
    parser.add_argument("--key", type=str, default=constants.PROXY_DEFAULT_PRIVATE_KEY_PATH, help=f"Path to SSL private key. Default is '{constants.PROXY_DEFAULT_PRIVATE_KEY_PATH}'.")
    parser.add_argument("-o", "--output", type=str, help="Output folder for page load data.")
    args = parser.parse_args()

    run(port=args.port, cert=args.cert, key=args.key, output_folder=args.output)
