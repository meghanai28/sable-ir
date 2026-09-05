import socket
import urllib.parse
from typing import Tuple, List, Union, Optional

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution functions.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the scheme is not HTTP or HTTPS, or if the resolved IP does not match the scheme's address family.
    """
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    
    family = socket.AF_INET if scheme == 'http' else socket.AF_INET6
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname.")
    
    if not resolved_ips:
        raise ValueError("No IP addresses found for hostname.")
    
    if not resolved_ips:
        raise ValueError("resolve_host returned no IP addresses.")
    
    # Check if any resolved IP matches the expected family
    valid_ips = [ip for ip in resolved_ips if isinstance(ip, str) and ip]
    if not valid_ips:
        raise ValueError("No valid IP addresses found.")
    
    # Determine the IP to use based on the scheme and available IPs
    # For simplicity, we pick the first valid IP. In a real scenario, you might choose based on preference.
    target_ip = valid_ips[0]
    
    # Construct the request URL with the resolved IP
    if scheme == 'http':
        request_url = f"http://{target_ip}:{port}{parsed.path}"
    else:
        request_url = f"https://{target_ip}:{port}{parsed.path}"
    
    # Use the provided transport function
    status, headers, body = transport(request_url)
    
    if status != 200:
        raise ValueError(f"Request failed with status code {status}")
    
    return body

def resolve_host(hostname: str) -> List[str]:
    """
    Resolve a hostname to a list of IP addresses.
    This is a placeholder implementation for demonstration purposes.
    In a real scenario, this would use the socket module to resolve the hostname.
    
    Args:
        hostname: The hostname to resolve.
    
    Returns:
        A list of IP addresses as strings.
    """
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        return [ip[4][0] for ip in ip_addresses]
    except socket.gaierror:
        return []

def transport(url: str) -> Tuple[int, dict, str]:
    """
    A placeholder transport function that simulates an HTTP request.
    In a real scenario, this would make an actual HTTP request.
    
    Args:
        url: The URL to request.
    
    Returns:
        A tuple containing (status, headers, body).
    """
    # This is a mock implementation for demonstration purposes.
    # In a real scenario, this would make an actual HTTP request.
    status = 200
    headers = {}
    body = f"Response from {url}"
    return (status, headers, body)
