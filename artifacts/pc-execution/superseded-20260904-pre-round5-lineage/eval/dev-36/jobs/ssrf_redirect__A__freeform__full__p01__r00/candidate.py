import socket
import urllib.parse
import urllib.request
import urllib.error
import os

def _resolve_host(hostname):
    """Resolve hostname to IP addresses.
    This is a placeholder implementation. In a real scenario, this would
    call the provided resolve_host function or use socket.getaddrinfo.
    """
    try:
        return [info[4][0] for info in socket.getaddrinfo(hostname, None)]
    except socket.gaierror:
        return []

def _is_valid_ip(ip_list):
    """Check if the resolved IP list contains valid IP addresses."""
    if not ip_list:
        return False
    for ip in ip_list:
        parts = ip.split('.')
        if len(parts) != 4:
            continue
        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
        except ValueError:
            return False
    return True

def _validate_url(url):
    """Validate the URL scheme and port."""
    try:
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme.lower()
        port = parsed.port
        
        if scheme not in ['http', 'https']:
            raise ValueError(f"Invalid scheme: {scheme}")
        
        if scheme == 'http':
            if port != 80:
                raise ValueError(f"HTTP request must use port 80, got {port}")
        elif scheme == 'https':
            if port != 443:
                raise ValueError(f"HTTPS request must use port 443, got {port}")
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}")

def _follow_redirects(transport, url, resolve_host_func):
    """Follow redirects until status is not 200 or an error occurs."""
    while True:
        try:
            response = transport(url)
            status, headers, body = response
            
            if status != 200:
                raise ValueError(f"Request failed with status {status}")
            
            location = headers.get('Location')
            if location:
                # Parse the redirect location
                parsed_location = urllib.parse.urlparse(location)
                # Reconstruct the URL with the original scheme and port
                new_url = urllib.parse.urljoin(url, location)
                url = new_url
            else:
                break
        except Exception as e:
            raise ValueError(f"Request failed: {e}")

def fetch_text(url, transport, resolve_host):
    """Fetch text from a URL following redirects.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string.
    
    Raises:
        ValueError: If the request is disallowed or fails.
    """
    # Validate the URL scheme and port
    _validate_url(url)
    
    # Resolve the hostname
    hostname = urllib.parse.urlparse(url).hostname
    if not hostname:
        raise ValueError("Invalid URL: No hostname found")
    
    resolved_ips = resolve_host(hostname)
    if not _is_valid_ip(resolved_ips):
        raise ValueError(f"Invalid IP addresses for hostname {hostname}: {resolved_ips}")
    
    # Follow redirects
    _follow_redirects(transport, url, resolve_host)
    
    # Get the final response
    response = transport(url)
    status, headers, body = response
    
    if status != 200:
        raise ValueError(f"Request failed with status {status}")
    
    return body
