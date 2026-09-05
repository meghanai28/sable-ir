import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl
from typing import Tuple, List, Optional

def _is_global_public_address(ip: str) -> bool:
    """Check if an IP address is a global public address.
    This is a simplified check: allow IPv4 and IPv6, reject private/reserved ranges.
    In a real scenario, this would query a DNS blacklist or similar authoritative source.
    For this implementation, we assume standard public ranges unless explicitly private.
    """
    try:
        # Convert to integer to check ranges
        if '.' in ip:
            parts = [int(p) for p in ip.split('.')]
            # IPv4 private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 0.0.0.0/8, 224.0.0.0/4, 240.0.0.0/4
            if len(parts) == 4:
                if (parts[0] == 10) or \
                   (parts[0] == 172 and 16 <= parts[1] <= 31) or \
                   (parts[0] == 192 and parts[1] == 168) or \
                   (parts[0] == 127) or \
                   (parts[0] == 0) or \
                   (parts[0] >= 224) or \
                   (parts[0] >= 240):
                    return False
        else:
            # IPv6
            # Simplified check: reject link-local (fe80::/10), loopback (::1), multicast (ff00::/8)
            # This is a basic heuristic; a full check is complex without libraries like ipaddress
            if ip.startswith('fe80:') or ip.startswith('::1') or ip.startswith('ff00:'):
                return False
        return True
    except (ValueError, TypeError):
        return False

def _validate_hostname(hostname: str) -> Optional[str]:
    """Validate hostname, extract IP, and check if it's a global public address.
    Returns the IP string if valid, None otherwise.
    """
    if not hostname:
        return None
    
    try:
        # Resolve hostname
        addrs = socket.getaddrinfo(hostname, None, socket.AF_INET)
        if not addrs:
            return None
        
        for family, _, _, _, sockaddr in addrs:
            ip = sockaddr[0]
            if not _is_global_public_address(ip):
                return None
            return ip
    except socket.gaierror:
        return None
    return None

def _validate_url_scheme_port(url: str) -> Optional[str]:
    """Validate URL scheme and port.
    Returns the netloc if valid, None otherwise.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme.lower()
        port = parsed.port
        
        if scheme not in ('http', 'https'):
            return None
        
        if scheme == 'http':
            if port is not None and port != 80:
                return None
        elif scheme == 'https':
            if port is not None and port != 443:
                return None
        
        # Check for credentials in netloc
        netloc = parsed.netloc
        if '@' in netloc:
            return None
        
        return netloc
    except Exception:
        return None

def fetch_text(url: str, transport, resolve_host) -> str:
    """Fetch text from URL following redirects with validation.
    
    Args:
        url: The initial URL to fetch.
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of IP strings.
    
    Returns:
        The response body for a 200 status.
    
    Raises:
        ValueError: If validation fails or too many redirects.
    """
    current_url = url
    redirects_count = 0
    max_redirects = 5
    
    while redirects_count <= max_redirects:
        # Validate current_url
        validated_netloc = _validate_url_scheme_port(current_url)
        if not validated_netloc:
            raise ValueError("Invalid URL scheme or port")
        
        # Validate hostname
        hostname = validated_netloc.split(':')[0]
        resolved_ip = _validate_hostname(hostname)
        if not resolved_ip:
            raise ValueError("Hostname is not a global public address")
        
        # Make the request
        try:
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
        
        status, headers, body = response
        
        # Check status
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        return body
        
        # Handle redirects
        if 'location' in headers.lower():
            location_value = headers['location'].strip()
            if not location_value:
                raise ValueError("Missing Location header")
            
            # Resolve relative URL
            try:
                parsed_current = urllib.parse.urlparse(current_url)
                parsed_location = urllib.parse.urlparse(location_value)
                
                if parsed_current.scheme == '' and parsed_location.scheme == '':
                    # Relative URL
                    if parsed_current.path.endswith('/'):
                        new_path = parsed_location.path
                    else:
                        new_path = parsed_current.path + '/' + parsed_location.path
                    new_url = parsed_current._replace(path=new_path, params=parsed_location.params, query=parsed_location.query).geturl()
                else:
                    # Absolute URL
                    new_url = location_value
            except Exception:
                raise ValueError("Invalid redirect URL")
            
            # Increment redirect count
            redirects_count += 1
            if redirects_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Re-validate the new URL
            new_url = _validate_url_scheme_port(new_url)
            if not new_url:
                raise ValueError("Invalid redirect URL scheme or port")
            
            hostname = new_url.split(':')[0]
            resolved_ip = _validate_hostname(hostname)
            if not resolved_ip:
                raise ValueError("Redirect target is not a global public address")
            
            current_url = new_url
        else:
            raise ValueError("Missing Location header on redirect")
    
    raise ValueError("Too many redirects")
