import re
import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    
    def validate_url(url_to_validate):
        parsed = urlparse(url_to_validate)
        
        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        # Validate port (must be default port)
        if parsed.scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        
        # Check for explicit non-default port
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        
        # Validate no credentials in URL
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed in URL")
        
        # Validate hostname exists
        if not parsed.hostname:
            raise ValueError("Missing hostname")
        
        # Resolve hostname
        try:
            ip_addresses = resolve_host(parsed.hostname)
        except Exception:
            raise ValueError("DNS resolution failed")
        
        if not ip_addresses:
            raise ValueError("No IP addresses returned")
        
        # Validate each resolved IP address
        for ip_text in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_text)
            except ValueError:
                raise ValueError("Invalid IP address format")
            
            # Check for loopback addresses
            if ip.is_loopback:
                raise ValueError("Loopback address not allowed")
            
            # Check for private addresses
            if ip.is_private:
                raise ValueError("Private address not allowed")
            
            # Check for link-local addresses
            if ip.is_link_local:
                raise ValueError("Link-local address not allowed")
            
            # Check for multicast addresses
            if ip.is_multicast:
                raise ValueError("Multicast address not allowed")
            
            # Check for reserved addresses
            if ip.is_reserved:
                raise ValueError("Reserved address not allowed")
            
            # Check for unspecified address
            if ip.is_unspecified:
                raise ValueError("Unspecified address not allowed")
            
            # For IPv4, check for 0.0.0.0/8 (current network)
            if isinstance(ip, ipaddress.IPv4Address):
                if ip.packed[0] == 0:
                    raise ValueError("Current network address not allowed")
            
            # Check for site-local (deprecated but still check)
            if hasattr(ip, 'is_site_local') and ip.is_site_local:
                raise ValueError("Site-local address not allowed")
        
        return url_to_validate
    
    def resolve_location(current_url, location):
        # Handle empty location
        if not location:
            raise ValueError("Empty Location header")
        
        # Resolve relative URL against current URL
        next_url = urljoin(current_url, location)
        return next_url
    
    # Main fetch logic with redirect handling
    current_url = url
    redirect_count = 0
    
    while True:
        # Validate the current URL
        validated_url = validate_url(current_url)
        
        # Submit to transport
        try:
            status, headers, body = transport(validated_url)
        except Exception:
            raise ValueError("Transport failed")
        
        # Handle redirect status codes
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            # Extract Location header
            location = None
            for header_name, header_value in headers:
                if header_name.lower() == 'location':
                    location = header_value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            # Resolve location against current URL
            current_url = resolve_location(current_url, location)
            continue
        
        # Handle successful response
        if status == 200:
            return body
        
        # Any other terminal state
        raise ValueError(f"Unexpected status: {status}")
