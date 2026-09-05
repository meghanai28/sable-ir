import os
import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl

def resolve_host(hostname: str) -> str:
    """Resolve hostname to textual IP addresses."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        raise ValueError(f"Failed to resolve hostname: {hostname}")

def fetch_text(url: str, transport, resolve_host) -> str:
    """Fetch text from URL using provided transport."""
    # Guard: Resolve hostname
    hostname = urllib.parse.urlparse(url).hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname found")
    
    resolved_ip = resolve_host(hostname)
    
    # Guard: Check port (HTTP default 80, HTTPS default 443)
    parsed = urllib.parse.urlparse(url)
    port = parsed.port
    scheme = parsed.scheme.lower()
    
    valid_port = None
    if scheme == 'http':
        valid_port = 80
    elif scheme == 'https':
        valid_port = 443
    
    if port is None:
        port = valid_port
    
    if port != valid_port:
        raise ValueError(f"Only HTTP (port 80) or HTTPS (port 443) on default ports are allowed. Got port {port} for {scheme}")
    
    # Build request
    req = urllib.request.Request(url)
    
    try:
        response = transport(url)
    except Exception as e:
        raise ValueError(f"Transport error: {e}")
    
    status, headers, body = response
    
    # Guard: Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Guard: Ensure body is string-like and return it
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return body
