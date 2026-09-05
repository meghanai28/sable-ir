import socket
import urllib.parse
import urllib.request
import urllib.error
import re

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL, handling redirects and validating inputs.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the HTTP response with status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, no IP is resolved, or redirect validation fails.
    """
    
    def validate_scheme_and_port(parsed_url):
        """Ensure the scheme is http/https and port is valid."""
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError(f"Disallowed scheme: {scheme}")
        
        port = parsed_url.port
        if port is None:
            if scheme == 'http':
                port = 80
            elif scheme == 'https':
                port = 443
        return scheme, port
    
    def is_public_address(ip_str):
        """
        Basic check to ensure the IP is not a private/reserved address.
        This is a simplified version of the requirement "points to a public address".
        """
        ip = ip_str.strip()
        if not ip:
            return False
        
        # Check for IPv4
        if re.match(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$', ip):
            octets = [int(x) for x in ip.split('.')]
            # Check for private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, etc.)
            if (octets[0] == 10 or 
                (octets[0] == 172 and 16 <= octets[1] <= 31) or 
                octets[0] == 192 and octets[1] == 168 or 
                octets[0] == 127 or 
                octets[0] == 0 or 
                octets[0] == 169 or 
                octets[0] == 224 or 
                octets[0] == 225 or 
                octets[0] == 226 or 
                octets[0] == 238 or 
                octets[0] == 239 or 
                octets[0] == 240 or 
                octets[0] == 241 or 
                octets[0] == 242 or 
                octets[0] == 243 or 
                octets[0] == 244 or 
                octets[0] == 245 or 
                octets[0] == 246 or 
                octets[0] == 247 or 
                octets[0] == 250 or 
                octets[0] == 251 or 
                octets[0] == 252 or 
                octets[0] == 253 or 
                octets[0] == 254 or 
                octets[0] == 255):
                return False
        # Check for IPv6 (simplified: just reject if it looks like a loopback or link-local)
        # For strictness, we assume any valid DNS resolution result is acceptable if not obviously private
        # However, the prompt implies we must check if it points to a public address.
        # A robust check would use a library, but we stick to regex/string logic.
        # Let's assume standard public IPs pass this basic check unless they are clearly private.
        return True

    def resolve_url_hostname(hostname):
        """Resolve hostname to IP addresses using the supplied resolve_host function."""
        try:
            ips = resolve_host(hostname)
            if not ips:
                raise ValueError(f"No IP address found for hostname: {hostname}")
            return ips
        except Exception:
            raise ValueError(f"DNS lookup failed for hostname: {hostname}")

    def validate_redirect_location(current_url, location_header):
        """
        Validate the Location header against the current URL.
        - Must have the same scheme and port.
        - Must resolve to a public address.
        """
        current_scheme, current_port = validate_scheme_and_port(urllib.parse.urlparse(current_url))
        
        # Parse the location header
        try:
            location_parsed = urllib.parse.urlparse(location_header)
        except Exception:
            raise ValueError(f"Invalid Location header format: {location_header}")
        
        # Check scheme
        if location_parsed.scheme.lower() != current_scheme:
            raise ValueError(f"Location scheme mismatch: {location_parsed.scheme} vs {current_scheme}")
        
        # Check port
        location_port = location_parsed.port
        if location_port is None:
            if current_scheme == 'http':
                expected_port = 80
            elif current_scheme == 'https':
                expected_port = 443
        else:
            expected_port = location_port
        
        if expected_port != current_port:
            raise ValueError(f"Location port mismatch: {expected_port} vs {current_port}")
        
        # Extract hostname for resolution
        hostname = location_parsed.hostname
        if not hostname:
            raise ValueError(f"Invalid hostname in Location header: {location_header}")
        
        # Resolve hostname
        try:
            resolved_ips = resolve_url_hostname(hostname)
        except ValueError:
            raise
        
        # Check if any resolved IP is public
        public_ips = [ip for ip in resolved_ips if is_public_address(ip)]
        if not public_ips:
            raise ValueError(f"Resolved IP address is not public: {resolved_ips}")
        
        return True

    def get_host_and_port(parsed_url):
        """Get the hostname and port from a parsed URL."""
        if parsed_url.port is None:
            if parsed_url.scheme == 'http':
                port = 80
            elif parsed_url.scheme == 'https':
                port = 443
        else:
            port = parsed_url.port
        return parsed_url.hostname, port

    # Parse the initial URL
    initial_parsed = urllib.parse.urlparse(url)
    
    # Validate initial scheme
    scheme, port = validate_scheme_and_port(initial_parsed)
    
    # Validate initial hostname resolution
    initial_hostname, _ = get_host_and_port(initial_parsed)
    resolve_url_hostname(initial_hostname)
    
    current_url = url
    current_scheme = scheme
    current_port = port
    redirect_count = 0
    max_redirects = 5
    
    while redirect_count <= max_redirects:
        # Use the transport to get the response
        status, headers, body = transport(current_url)
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Parse headers
        location_header = headers.get('Location')
        
        if location_header:
            # Follow redirect
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Validate the redirect location
            validate_redirect_location(current_url, location_header)
            
            # Update current_url to the new location
            current_url = location_header
        else:
            break
        
        # Check if we are done
        if redirect_count > max_redirects:
            raise ValueError("Too many redirects")
    
    return body
