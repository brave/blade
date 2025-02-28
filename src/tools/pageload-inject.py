# Note:   Inject a script to collect page load time measurements (load time, in milliseconds) per app, using the performance.timing API
#
# This script is supposed to be loaded by mitmproxy: mitmdump -s pageload-inject.py --ssl-insecure -q &
# Before running the script, make sure to set the environment variables: BROWSER_NAME, SERVER_IP, SERVER_PORT
# To correctly intercept the requests, CA certificate should be installed on the device.
# To generate Android friendly CA certificate run: openssl x509 -inform PEM -outform DER -in ~/.mitmproxy/mitmproxy-ca-cert.pem -out mitmproxy-ca-cert.der
# Push it to the device: adb push mitmproxy-ca-cert.der /sdcard/
# CA certificate should be installed on the device manually: 
# Settings -> Security & Privacy -> More security & Privacy -> Encription & credentials -> Install a certificate -> CA certificate -> install mitmproxy-ca-cert.der from /sdcard/
# Chromium-based browsers (Chrome, Brave, Edge, etc) will trust user-installed certificates, but Firefox and DuckDuckGo will not. On Firefox we enable it with preference flag. DuckDuckGo does not support it at all, so mitmproxy CA certificate should be copied to the system CA store using Magisk module .
#
# Author: Artem Chaikin (achaikin@brave.com)
# Date:   22/11/2024


from mitmproxy import http
import os
import re

from libs import constants

# Fetch browser name, IP, and port from environment variables, browser_name should be updated before a new browser is going to be tested
browser_name = os.getenv("BROWSER_NAME", "Unknown")
server_ip = os.getenv("SERVER_IP", "127.0.0.1")
server_port = os.getenv("SERVER_PORT", "8443")

def response(flow: http.HTTPFlow) -> None:
    # Check if the response is HTML and not part of an iframe
    if "text/html" in flow.response.headers.get("content-type", "") and flow.request.headers.get("sec-fetch-dest", "") != "iframe":
        # Remove Content-Security-Policy header
        if "Content-Security-Policy" in flow.response.headers:
            del flow.response.headers["Content-Security-Policy"]
        # Remove CSP meta tag if present
        flow.response.text = re.sub(
            r'<meta[^>]*http-equiv=["\']Content-Security-Policy["\'][^>]*>',
            '',
            flow.response.text,
            flags=re.IGNORECASE
        )

        # Initial script to be injected after <head>
        fetch_save_script = """
        <script>
            var blade_domContentPerformance = null;
            var blade_lcp = null;

            // Initialize LCP observer
            const blade_observer = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                blade_lcp = entries[entries.length - 1]; // Use the latest LCP candidate
            });
            blade_observer.observe({ type: "largest-contentful-paint", buffered: true });
            window._originalFetch = window.fetch;
            window._originalPerformance = window.performance;
        </script>
        """
        
        # Collect measurements script
        script = f"""
        <script>
        (function() {{
            const browserName = "{browser_name}";

            window.onload = function() {{
                setTimeout(() => {{
                    const timing = _originalPerformance.timing;
                    const loadTime = timing.loadEventEnd - timing.navigationStart;
                    

                    blade_domContentPerformance = _originalPerformance.getEntriesByType("navigation")[0];

                    // Log all performance metrics
                    // console.log("Start Time:", timing.navigationStart);
                    // console.log("End Time:", timing.loadEventEnd);
                    // console.log("Page Load Time:", loadTime + " ms");
                    // console.log("Request Start:", blade_domContentPerformance.requestStart);
                    // console.log("Response End:", blade_domContentPerformance.responseEnd);
                    // console.log("DOM Interactive:", blade_domContentPerformance.domInteractive);
                    // console.log("DOM Content Loaded Start:", blade_domContentPerformance.domContentLoadedEventStart);
                    // console.log("DOM Content Loaded End:", blade_domContentPerformance.domContentLoadedEventEnd);
                    // console.log("DOM Complete:", blade_domContentPerformance.domComplete);
                    // console.log("Load Event Start:", blade_domContentPerformance.loadEventStart);
                    // console.log("Load Event End:", blade_domContentPerformance.loadEventEnd);
                    // console.log("Total Duration:", blade_domContentPerformance.duration);
                    // console.log("LCP class name:", blade_lcp.element.className);
                    // console.log("LCP load time:", blade_lcp.loadTime + " ms");
                    // console.log("LCP render time:", blade_lcp.renderTime + " ms");

                    // Server URL based on dynamic IP and port
                    const serverUrl = "https://{server_ip}:{server_port}/";

                    // Prepare data with all metrics
                    const data = {{
                        url: window.location.href,
                        loadTime: loadTime,
                        browser: browserName,
                        requestStart: blade_domContentPerformance.requestStart,
                        responseEnd: blade_domContentPerformance.responseEnd,
                        domInteractive: blade_domContentPerformance.domInteractive,
                        domContentLoadedEventStart: blade_domContentPerformance.domContentLoadedEventStart,
                        domContentLoadedEventEnd: blade_domContentPerformance.domContentLoadedEventEnd,
                        domComplete: blade_domContentPerformance.domComplete,
                        loadEventStart: blade_domContentPerformance.loadEventStart,
                        loadEventEnd: blade_domContentPerformance.loadEventEnd,
                        duration: blade_domContentPerformance.duration,
                        lcpClassName: blade_lcp.element.className,
                        lcpLoadTime: blade_lcp.loadTime,
                        lcpRenderTime: blade_lcp.renderTime
                    }};

                    // Send data to the server
                    _originalFetch(serverUrl, {{
                        method: "POST",
                        headers: {{
                            "Content-Type": "application/json"
                        }},
                        body: JSON.stringify(data)
                    }}).then(response => {{
                        if (response.ok) {{
                            console.log("Page load time data sent successfully");
                        }} else {{
                            console.error("Failed to send data:", response.status);
                        }}
                    }}).catch(error => {{
                        console.error("Error sending data:", error);
                    }});
                }}, {constants.FIVE_SECONDS*1000});  // 5-second delay in milliseconds, otherwise performance.timing.loadEventEnd sometimes returns 0
            }};
        }})();
        </script>
        """
        # Inject the fetch save script after the opening head tag
        flow.response.text = flow.response.text.replace("<head>", "<head>" + fetch_save_script)
        # Inject the main script before the closing body tag
        flow.response.text = flow.response.text.replace("</body>", script + "</body>")
    else:
        # Stream non-HTML responses
        flow.response.stream = True

