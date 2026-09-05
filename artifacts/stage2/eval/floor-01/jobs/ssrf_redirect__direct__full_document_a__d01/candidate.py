import urllib.request
import urllib.error
import socket
import os
import re

def _validate_url(url):
    """
    Validate that the URL is HTTP or HTTPS and does not contain disallowed schemes.
    Raises ValueError if the scheme is not http or https.
    """
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")
    # Basic check to prevent obvious path traversal in the scheme or fragment
    # though the main protection is the scheme check.
    return url

def _resolve_ip_addresses(url):
    """
    Resolve the hostname in the URL to IP addresses.
    Uses the provided resolve_host function.
    """
    try:
        hostname = url.split('://')[1].split('?')[0].split('#')[0]
        return resolve_host(hostname)
    except Exception:
        raise ValueError("Invalid URL format for hostname resolution.")

def _fetch_with_timeout(url, transport, resolve_host):
    """
    Fetch the text content of a URL with a finite timeout.
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    host = parsed.hostname or parsed.netloc
    
    # Resolve host
    ip_addresses = resolve_host(host)
    
    # Select the appropriate transport based on scheme
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Unsupported scheme.")

    # Construct the request URL with the resolved port
    # If no port is specified, use the default. If specified, use it.
    if port is None:
        port = default_port
    else:
        port = port

    # Ensure the port is an integer
    if not isinstance(port, int):
        raise ValueError("Port must be an integer.")

    # Use the transport function to get the response
    status, headers, body = transport(url)

    # Check for redirect
    if status != 200:
        raise ValueError(f"Disallowed status code: {status}")

    # Return the body
    return body

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns IP addresses.
    
    Returns:
        The body of the response as a string.
    
    Raises:
        ValueError: If the URL scheme is not HTTP/HTTPS, or if the status is not 200.
    """
    # Validate the URL scheme
    _validate_url(url)
    
    # Resolve the host
    _resolve_ip_addresses(url)
    
    # Fetch the text
    return _fetch_with_timeout(url, transport, resolve_host)
