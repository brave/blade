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
browser_name = os.getenv("BROWSER_NAME", constants.PROXY_DEFAULT_BROWSER_NAME)
server_ip = os.getenv("SERVER_IP", constants.PROXY_DEFAULT_SERVER_IP)
server_port = os.getenv("SERVER_PORT", str(constants.PROXY_DEFAULT_SERVER_PORT))


def response(flow: http.HTTPFlow) -> None:

    # Check if the response is HTML, not part of an iframe, and not a redirect
    if (flow.response.status_code not in [301, 302, 303, 307, 308] and 
        "text/html" in flow.response.headers.get("content-type", "") and 
        flow.request.headers.get("sec-fetch-dest", "") != "iframe"):
        # Remove Content-Security-Policy header
        if "Content-Security-Policy" in flow.response.headers:
            del flow.response.headers["Content-Security-Policy"]
            
        # Get the content using flow.response.text to avoid manual decoding
        content = flow.response.text
        
        # Remove CSP meta tag if present
        content = re.sub(
            r'<meta[^>]*http-equiv=["\']Content-Security-Policy["\'][^>]*>',
            '',
            content,
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

            // Use a unique identifier for this page visit - timestamp + random for uniqueness
            const pageVisitId = new Date().getTime() + '-' + Math.random().toString(36).substring(2, 15);
            
            // Get a URL-specific key for storage
            const getStorageKey = function() {{
                // Use pathname and search params as the key to differentiate URLs
                return 'blade_metrics_' + window.location.pathname + window.location.search;
            }};
            
            // Check if metrics have already been reported for this specific URL
            const reportCheck = function() {{
                const storageKey = getStorageKey();
                const reported = sessionStorage.getItem(storageKey);
                if (reported) {{
                    console.log("Metrics already reported for this specific URL:", window.location.href);
                    return true;
                }}
                return false;
            }};

            // Mark this specific URL as reported in sessionStorage
            const markAsReported = function() {{
                const storageKey = getStorageKey();
                sessionStorage.setItem(storageKey, pageVisitId);
                console.log("Marked URL as reported:", window.location.href);
            }};

            // Use addEventListener to preserve any existing onload handlers
            window.addEventListener('load', function() {{
                setTimeout(() => {{
                    // Exit early if this specific URL was already reported
                    if (reportCheck()) {{
                        return;
                    }}
                    
                    const timing = _originalPerformance.timing;
                    const loadTime = timing.loadEventEnd - timing.navigationStart;
                    
                    // Mark as reported immediately to prevent race conditions
                    markAsReported();

                    blade_domContentPerformance = _originalPerformance.getEntriesByType("navigation")[0];

                    // Server URL based on dynamic IP and port
                    const serverUrl = "https://{server_ip}:{server_port}/";

                    // Prepare data with all metrics
                    const data = {{
                        url: window.location.href,
                        loadTime: loadTime,
                        browser: browserName,
                        pageVisitId: pageVisitId, // Include the unique ID
                        requestStart: blade_domContentPerformance.requestStart,
                        responseEnd: blade_domContentPerformance.responseEnd,
                        domInteractive: blade_domContentPerformance.domInteractive,
                        domContentLoadedEventStart: blade_domContentPerformance.domContentLoadedEventStart,
                        domContentLoadedEventEnd: blade_domContentPerformance.domContentLoadedEventEnd,
                        domComplete: blade_domContentPerformance.domComplete,
                        loadEventStart: blade_domContentPerformance.loadEventStart,
                        loadEventEnd: blade_domContentPerformance.loadEventEnd,
                        duration: blade_domContentPerformance.duration,
                        lcpClassName: blade_lcp && blade_lcp.element ? encodeURIComponent(blade_lcp.element.className) : "",
                        lcpLoadTime: blade_lcp ? blade_lcp.loadTime : 0,
                        lcpRenderTime: blade_lcp ? blade_lcp.renderTime : 0
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
                }}, {constants.PAGELOAD_PROXY_WAIT_TIME_AFTER_STARTING*1000});  // delay in milliseconds, otherwise performance.timing.loadEventEnd sometimes returns 0
            }});
        }})();
        </script>
        """
        # Inject the fetch save script after the opening head tag
        content = re.sub(r'<head(\s[^>]*)?>', r'<head\1>' + fetch_save_script + script, content, flags=re.IGNORECASE)
        # Set the modified content back to the response
        #content = re.sub(r'</body(\s[^>]*)?>', fetch_save_script + script + r'</body\1>', content, flags=re.IGNORECASE)
        flow.response.text = content
    else:
        # Stream non-HTML responses
        flow.response.stream = True
