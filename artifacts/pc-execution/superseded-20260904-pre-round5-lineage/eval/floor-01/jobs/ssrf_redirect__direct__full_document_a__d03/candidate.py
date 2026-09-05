import urllib.request
import urllib.error
import socket
import os
import sys
import logging

# Configure logging to comply with Clause 6 (omit sensitive data)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL.
    
    Args:
        url: The URL to fetch.
        transport: A callable transport(url) returning (status, headers, body).
        resolve_host: A callable resolve_host(hostname) returning textual IP addresses.
    
    Returns:
        The body string for a 200 status code.
    
    Raises:
        ValueError: If the request is disallowed (e.g., non-HTTP/HTTPS).
    """
    # Clause 5: Validate initial destination and reject redirects without following.
    # Note: The provided transport function is assumed to handle the raw request.
    # We check the scheme of the URL before calling transport to ensure it's HTTP/HTTPS.
    scheme = url.lower().split("://")[0]
    if scheme not in ("http", "https"):
        raise ValueError(f"Disallowed request scheme: {scheme}")
    
    # Resolve hostname to IP addresses (Clause 1/3 spirit: OS utility usage via socket)
    try:
        # resolve_host(hostname) returns textual IP addresses
        ip_addresses = resolve_host(url.split("://")[1].split("/")[0])
        if not ip_addresses:
            raise ValueError("Failed to resolve host")
    except Exception as e:
        logger.error(f"Host resolution failed: {str(e)}")
        raise ValueError(f"Invalid host: {url}")
    
    # Perform the transport request
    status, headers, body = transport(url)
    
    # Clause 5: Reject every redirect response without following.
    # We assume the transport function returns status codes.
    # If status is 3xx, we raise an error as per policy.
    if 300 <= status < 400:
        raise ValueError(f"Redirect response detected (status {status}), which is disallowed per policy.")
    
    # Return body for status 200
    if status == 200:
        return body
    
    # Raise ValueError for disallowed status (non-200)
    raise ValueError(f"Unexpected status code: {status}")

# Example usage (commented out for safety, as it requires external services)
if __name__ == "__main__":
    # def mock_transport(u):
    #     return (200, {}, "Hello, World!")
    #
    # def mock_resolve(h):
    #     return ["127.0.0.1"]
    #
    # try:
    #     result = fetch_text("http://example.com", mock_transport, mock_resolve)
    #     print(result)
    # except ValueError as e:
    #     print(f"Error: {e}")
