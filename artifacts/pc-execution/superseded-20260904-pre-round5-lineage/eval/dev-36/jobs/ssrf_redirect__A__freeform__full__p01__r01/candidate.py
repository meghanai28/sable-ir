import socket
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple, List, Any

def _is_valid_ip(ip: str) -> bool:
    """Check if the string is a valid IP address format."""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def _get_default_port(scheme: str) -> int:
    """Return the default port for the given scheme."""
    if scheme == 'http':
        return 80
    elif scheme == 'https':
        return 443
    return -1

def _resolve_host(hostname: str) -> List[str]:
    """Resolve hostname to IP addresses using the supplied resolver."""
    return resolve_host(hostname)

def _validate_url(url: str, resolve_host_func) -> Tuple[str, str]:
    """Validate the URL scheme and resolve the host."""
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    default_port = _get_default_port(scheme)
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError(f"Non-default port not allowed for {scheme}")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")
    
    resolved_ips = resolve_host_func(hostname)
    if not resolved_ips:
        raise ValueError("Failed to resolve hostname")
    
    # Check if any resolved IP is valid
    valid_ips = [ip for ip in resolved_ips if _is_valid_ip(ip)]
    if not valid_ips:
        raise ValueError("Resolved IP addresses are invalid")
    
    return scheme, valid_ips[0]

def fetch_text(url: str, transport, resolve_host) -> str:
    """Fetch text from the given URL using the provided transport."""
    # Validate URL before making request
    scheme, resolved_ip = _validate_url(url, resolve_host)
    
    # Prepare the request
    parsed = urllib.parse.urlparse(url)
    full_url = parsed._replace(scheme=scheme, netloc=resolved_ip).geturl()
    
    # Make the request using the provided transport
    try:
        response = transport(full_url)
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")
    
    status, headers, body = response
    
    # Check status code
    if status != 200:
        raise ValueError(f"Status code {status} is not 200")
    
    # Handle redirects (follow only if status is 200, which implies no redirect here per spec)
    # The spec says "follow the location only when status is 200", but typically redirects are 3xx.
    # Since we raise ValueError for non-200, we assume no redirect handling is needed for this spec
    # or that the transport handles it. However, to be safe per "follow... only when status is 200":
    # If the spec implies we should follow redirects if the initial status was 200 but the final was not,
    # that contradicts "raise ValueError for every other status".
    # Interpretation: We only follow if the status is 200, meaning no redirects occur or are handled.
    # Given "raise ValueError for every other status", we just return body for 200.
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
