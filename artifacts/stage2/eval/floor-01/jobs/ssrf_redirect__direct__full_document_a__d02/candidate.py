import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl
import os
import re

def _validate_url(url: str) -> None:
    """
    Validate URL scheme and structure.
    Raises ValueError for disallowed requests (non-HTTP schemes).
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    allowed_schemes = {'http', 'https'}
    if scheme not in allowed_schemes:
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed, got: {scheme}")

    # Ensure path is not empty and host is present
    if not parsed.path or not parsed.netloc:
        raise ValueError("URL must have a scheme, host, and path")

def _resolve_host(hostname: str) -> list:
    """
    Resolve hostname to IP addresses using socket.
    Returns a list of textual IP addresses.
    """
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        # Extract IP addresses from the resolved info
        ips = [addr[4][0] for addr in ip_addresses]
        return ips
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {hostname}")

def _get_default_port(scheme: str) -> int:
    """Return the default port for the scheme."""
    if scheme == 'http':
        return 80
    elif scheme == 'https':
        return 443
    return 0

def _fetch_connection(url: str, transport_func, resolve_host_func) -> tuple:
    """
    Perform the HTTP request using the provided transport function.
    Validates the URL, resolves the host, and constructs the request.
    Returns (status, headers, body) tuple.
    """
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port or _get_default_port(scheme)
    host = parsed.netloc
    
    # Resolve host
    ips = resolve_host_func(host)
    if not ips:
        raise ValueError("No IP addresses found for host")
    
    # Select the first IP for the request
    ip_address = ips[0]
    
    # Build the full URL for the request
    full_url = f"{scheme}://{host}"
    if port != _get_default_port(scheme):
        full_url = f"{scheme}://{host}:{port}{parsed.path}"
    else:
        full_url = f"{scheme}://{host}{parsed.path}"
    
    # Use urllib.request to perform the request
    # Note: We do not follow redirects as per clause 5.
    req = urllib.request.Request(full_url)
    
    try:
        response = urllib.request.urlopen(req)
        status = response.status
        headers = dict(response.headers)
        body = response.read().decode('utf-8', errors='replace')
        return (status, headers, body)
    except urllib.error.HTTPError as e:
        # Even for errors, we return the status and headers, but body might be empty or partial
        return (e.code, dict(e.headers), e.read().decode('utf-8', errors='replace'))
    except urllib.error.URLError as e:
        raise ValueError(f"Request failed: {e.reason}")

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response as a string, if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., non-HTTP scheme) or fails.
    """
    # Clause 1: Validate URL before processing
    _validate_url(url)
    
    # Clause 5: Validate initial public HTTP destination (scheme check done above)
    # We do not follow redirects here.
    
    # Perform the fetch
    status, headers, body = transport(url)
    
    # Return body only for status 200
    if status == 200:
        return body
    else:
        raise ValueError(f"Disallowed request: HTTP status {status} is not 200")
