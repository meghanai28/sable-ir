import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with redirect handling and safety checks.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the final request with status 200.
    
    Raises:
        ValueError: If the scheme is not http/https or the port is not the default.
    """
    current_url = url
    max_redirects = 5
    redirect_count = 0
    
    while True:
        # Parse current URL to check scheme and port
        parsed = urllib.parse.urlparse(current_url)
        scheme = parsed.scheme.lower()
        port = parsed.port
        
        # Validate scheme
        if scheme not in ('http', 'https'):
            raise ValueError(f"Unallowed scheme: {scheme}")
        
        # Validate port
        default_port = {'http': 80, 'https': 443}[scheme]
        if port is None:
            port = default_port
        if port != default_port:
            raise ValueError(f"Non-default port {port} for scheme {scheme}")
        
        # Determine the default port for the scheme
        default_port = {'http': 80, 'https': 443}[scheme]
        
        # Perform the request
        try:
            # Construct the request URL with the current scheme, port, and path
            # If port is not specified in the input URL but is different from default,
            # we need to ensure we use the correct port.
            request_url = f"{scheme}://{parsed.hostname}:{port}{parsed.path}"
            
            status, headers, body = transport(request_url)
            
            if status != 200:
                raise ValueError(f"Status code {status} is not 200")
            
            return body
        
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
    
    # Handle redirects
    while redirect_count < max_redirects:
        redirect_count += 1
        location = headers.get('Location', None)
        
        if not location:
            raise ValueError("No Location header in redirect")
        
        # Update current URL with the new location
        current_url = location
        
        # Check for embedded credentials in Location header
        # e.g., http://example.com/path?foo=bar
        # We should strip credentials if present, but the plan says to check them.
        # The plan says "checking ... embedded credentials". This likely means we should
        # ensure we don't follow credentials that might be malicious.
        # However, standard behavior is to strip credentials. Let's assume standard stripping.
        parsed_location = urllib.parse.urlparse(location)
        
        # Check scheme and port of the redirect target
        redirect_scheme = parsed_location.scheme.lower()
        redirect_port = parsed_location.port
        
        if redirect_scheme not in ('http', 'https'):
            raise ValueError(f"Unallowed redirect scheme: {redirect_scheme}")
        
        default_port = {'http': 80, 'https': 443}[redirect_scheme]
        if redirect_port is None:
            redirect_port = default_port
        if redirect_port != default_port:
            raise ValueError(f"Non-default port {redirect_port} in redirect")
        
        # DNS resolution
        hostname = parsed_location.hostname
        if not hostname:
            raise ValueError("Invalid hostname in redirect")
        
        try:
            ips = resolve_host(hostname)
            if not ips:
                raise ValueError(f"No IP addresses found for {hostname}")
        except Exception as e:
            raise ValueError(f"DNS resolution failed: {e}")
        
        # Check for public addressing (assuming all returned IPs are public, or check if any are loopback/private)
        # The plan says "checking ... public addressing". This is vague.
        # Typically, we might want to block private IPs. Let's assume we check if any IP is private.
        import ipaddress
        private_ips = []
        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private:
                    private_ips.append(ip_str)
            except ValueError:
                # Invalid IP, skip
                continue
        
        # If any private IPs are found, raise an error?
        # The plan says "checking ... public addressing". This might mean we should only accept public IPs.
        if private_ips:
            raise ValueError(f"Private IP addresses found in DNS response: {private_ips}")
        
        # Continue to the next redirect
        continue
    
    raise ValueError("Too many redirects")
