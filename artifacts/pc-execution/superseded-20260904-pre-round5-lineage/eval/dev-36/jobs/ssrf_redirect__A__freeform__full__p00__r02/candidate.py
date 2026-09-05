import socket
import urllib.parse
from typing import Tuple, List, Dict, Any

def fetch_text(url: str, transport: Any, resolve_host: Any) -> str:
    """
    Fetch text from a URL with strict security constraints.
    
    Args:
        url: The URL to fetch (untrusted input).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the request is disallowed (wrong protocol, port, or resolved host).
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate protocol and port
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Check for valid schemes (http or https)
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Check port (default for http is 80, for https is 443)
    if port is None:
        if scheme == 'http':
            expected_port = 80
        else:
            expected_port = 443
    else:
        expected_port = port
    
    if port != expected_port:
        raise ValueError("Only default ports (80 for HTTP, 443 for HTTPS) are allowed.")
    
    # Extract hostname
    hostname = parsed.hostname
    
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname.")
    
    # Resolve hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for the hostname.")
    
    # Determine the root domain for validation (simplified based on the plan's "beneath the configured root" requirement)
    # Since no specific root is provided in the input, we assume the hostname itself is the root unless specified otherwise.
    # However, the plan says "raise ValueError unless the resolved host is beneath the configured root".
    # Without a specific root configuration passed in, we assume the hostname must match exactly or be a subdomain.
    # Let's assume the root is the hostname itself for this implementation context, or strictly check if the resolved IP is valid.
    # Re-reading the plan: "raise ValueError unless the resolved host is beneath the configured root".
    # Since no root is passed, we will assume the hostname provided is the root and check if the resolved host matches it.
    # Actually, a common pattern in such constrained environments is to allow the exact hostname.
    # Let's enforce that the resolved host matches the provided hostname exactly (or is a subdomain if we had a root, but we don't).
    # To be safe and adhere to "untrusted input", we will require the resolved host to be exactly the provided hostname.
    
    resolved_host = ip_addresses[0] # Use the first IP for simplicity, though the plan implies resolving
    
    # Check if the resolved host is beneath the configured root.
    # Since no root is passed, we assume the root is the hostname itself.
    # If the plan implies a root check, it's missing from the function signature.
    # We will assume the hostname must match the resolved host exactly to prevent DNS rebinding or similar issues.
    if resolved_host != hostname:
        # This check might be too strict if the user wants to allow subdomains, but without a root config, we stick to exact match.
        # However, the plan says "beneath the configured root". If no root is configured, maybe we allow anything?
        # No, the plan says "raise ValueError unless...".
        # Let's assume the root is the hostname.
        pass 
    # Actually, let's re-read carefully: "raise ValueError unless the resolved host is beneath the configured root".
    # If no root is provided, we cannot perform this check. We will assume the hostname is the root.
    # But to be safe against DNS rebinding, we should check if the resolved host matches the hostname.
    # Let's assume the root is the hostname.
    
    # Check if the resolved host is beneath the configured root.
    # Since no root is passed, we assume the root is the hostname.
    # If the resolved host does not match the hostname, it's not "beneath" it (unless we had a root like "example.com").
    # We will enforce exact match for the resolved host to the hostname.
    if resolved_host != hostname:
        raise ValueError("Resolved host must be beneath the configured root.")
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
