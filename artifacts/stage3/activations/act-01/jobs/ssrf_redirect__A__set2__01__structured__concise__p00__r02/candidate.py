import urllib.request
import urllib.error
import socket
from typing import Tuple, List

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetches text from a URL using the provided transport function.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the hostname cannot be resolved or if the status is not 200.
    """
    # Resolve the hostname
    try:
        hostname = urllib.parse.urlparse(url).hostname
        if not hostname:
            raise ValueError("Invalid URL: Missing hostname")
        
        ip_addresses = resolve_host(hostname)
        if not ip_addresses or not isinstance(ip_addresses, (list, tuple)):
            raise ValueError("resolve_host must return textual IP addresses")
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    # Create a request and open the connection
    req = urllib.request.Request(url)
    try:
        response = urllib.request.urlopen(req)
        status = response.status
        headers = dict(response.headers)
        body = response.read().decode('utf-8')
        
        if status != 200:
            raise ValueError(f"Request failed with status code: {status}")
        
        return body
    except urllib.error.HTTPError as e:
        status = e.code
        raise ValueError(f"HTTP Error: {status}")
    except Exception as e:
        raise ValueError(f"Network error: {e}")
