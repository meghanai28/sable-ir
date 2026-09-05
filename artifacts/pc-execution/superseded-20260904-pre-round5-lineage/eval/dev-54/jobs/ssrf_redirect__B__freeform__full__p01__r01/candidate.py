import urllib.parse
from typing import Tuple, List, Optional

def fetch_text(url: str, transport, resolve_host: callable) -> str:
    """
    Fetch text from a URL, following redirects up to 5 hops.
    
    Args:
        url: The URL to fetch from (can be absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme or port is invalid.
    """
    def _validate_scheme_port(url_str: str) -> Tuple[str, str]:
        """Validate and extract scheme and port from URL."""
        parsed = urllib.parse.urlparse(url_str)
        scheme = parsed.scheme.lower()
        port = parsed.port
        
        # Check for valid schemes
        if scheme not in ('http', 'https'):
            raise ValueError(f"Unsupported scheme: {scheme}")
        
        # Validate port
        if port is not None:
            if port < 1 or port > 65535:
                raise ValueError(f"Invalid port: {port}")
            if port != 80 and scheme == 'http':
                raise ValueError(f"Non-default port {port} not allowed for HTTP")
            if port != 443 and scheme == 'https':
                raise ValueError(f"Non-default port {port} not allowed for HTTPS")
        
        return scheme, port

    def _resolve_hostname(host: str) -> List[str]:
        """Resolve hostname to IP addresses."""
        if not host:
            raise ValueError("Empty hostname")
        try:
            ips = resolve_host(host)
            if not ips:
                raise ValueError(f"No IP addresses found for {host}")
            return ips
        except Exception:
            raise ValueError(f"Failed to resolve {host}")

    def _get_effective_port(parsed: urllib.parse.ParseResult, scheme: str) -> int:
        """Get the effective port for the scheme."""
        if parsed.port:
            return parsed.port
        if scheme == 'http':
            return 80
        if scheme == 'https':
            return 443
        return 0

    def _validate_redirect_location(current_url: str, location: str) -> bool:
        """Validate that redirect location matches scheme, port, and has valid DNS."""
        current_parsed = urllib.parse.urlparse(current_url)
        redirect_parsed = urllib.parse.urlparse(location)
        
        # Must have same scheme
        if redirect_parsed.scheme != current_parsed.scheme:
            return False
        
        # Must have same effective port
        current_port = _get_effective_port(current_parsed, current_parsed.scheme)
        redirect_port = _get_effective_port(redirect_parsed, redirect_parsed.scheme)
        if current_port != redirect_port:
            return False
        
        # Validate DNS for the new host
        if not redirect_parsed.hostname:
            return False
        try:
            resolve_host(redirect_parsed.hostname)
            return True
        except ValueError:
            return False

    def _resolve_relative_url(base: str, relative: str) -> str:
        """Resolve a relative URL against a base URL."""
        base_parsed = urllib.parse.urlparse(base)
        # Remove fragment if present
        if base_parsed.fragment:
            base_parsed = urllib.parse.urlparse(base_parsed._replace(fragment=''))
        
        result = urllib.parse.urljoin(base, relative)
        return result

    # Parse initial URL
    initial_url = url
    parsed = urllib.parse.urlparse(initial_url)
    
    # Validate scheme and port
    scheme, port = _validate_scheme_port(initial_url)
    
    # Resolve hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")
    
    try:
        ips = resolve_host(hostname)
    except ValueError:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    # Start fetching
    current_url = initial_url
    hops = 0
    
    while hops < 5:
        # Transport call
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            # If not 200, we still need to handle redirects if present
            # But per spec, we only return body for 200. If not 200, we stop.
            # However, we should check for Location header to see if we should continue
            # The spec says "Follow Location headers at most five hops"
            # So if status is not 200 but there's a Location, we continue
            pass
        
        # Check for Location header
        location = None
        if 'location' in headers:
            location = headers['location']
        
        if location:
            # Resolve relative location
            if not location.startswith(('http://', 'https://')):
                current_url = _resolve_relative_url(current_url, location)
            else:
                current_url = location
            
            # Validate redirect
            if not _validate_redirect_location(current_url, location):
                raise ValueError("Invalid redirect: scheme or port mismatch or invalid DNS")
            
            hops += 1
            continue
        
        # If no location or after following redirects, check status
        if status != 200:
            # According to spec: "return the body for status 200"
            # If not 200, we don't return body. But should we raise?
            # The spec says "raise ValueError for a disallowed request"
            # A non-200 response might be disallowed if we're expecting 200
            # However, the plan doesn't explicitly say to raise on non-200
            # But it says "return the body for status 200" implying we only return on 200
            # Let's assume non-200 means we stop and don't return anything
            # But the function signature requires returning str
            # This is ambiguous. Let's assume we raise ValueError for non-200
            raise ValueError(f"Request failed with status {status}")
        
        # Return body
        return body

    # If we exit the loop without returning, something went wrong
    # But per spec, we should have returned by now if status is 200
    # If we get here, it means we followed 5 redirects and still didn't get 200
    # Or we had an error
    raise ValueError("Failed to fetch text")
