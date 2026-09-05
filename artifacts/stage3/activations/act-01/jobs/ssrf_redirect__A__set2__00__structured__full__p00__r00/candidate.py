import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    # Validate scheme
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Resolve hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError(f"Failed to resolve hostname: {hostname}")
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    # Construct the full URL for transport
    # transport expects a URL string, we use the original or normalized one
    # The plan says "follow only the first validated request", implying we use the input url
    # but we must ensure we are connecting to the resolved host.
    # Since transport(url) is called, we assume it handles the URL resolution or expects the final URL.
    # However, the guard says "resolve the hostname... and raise ValueError when resolution fails".
    # The transport function likely takes the URL and connects.
    # We must ensure we don't follow redirects.
    
    # Make the request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
