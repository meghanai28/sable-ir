import socket
import urllib.parse
import urllib.request
import urllib.error

def resolve_host(hostname):
    """Resolve hostname to textual IP addresses."""
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        return [ip[4][0] for ip in ip_addresses]
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

def is_public_address(ip):
    """Check if an IP address is public (not localhost or private)."""
    # Check for localhost
    if ip in ('127.0.0.1', '::1', '0.0.0.0'):
        return True
    
    # Check for private ranges
    private_ranges = [
        ('10.0.0.0', '10.255.255.255'),
        ('172.16.0.0', '172.31.255.255'),
        ('192.168.0.0', '192.168.255.255'),
        ('0.0.0.0', '0.255.255.255'),
    ]
    
    for start, end in private_ranges:
        try:
            start_parts = [int(x) for x in start.split('.')]
            end_parts = [int(x) for x in end.split('.')]
            ip_parts = [int(x) for x in ip.split('.')]
            
            if all(a <= b <= c for a, b, c in zip(ip_parts, start_parts, end_parts)):
                return True
        except ValueError:
            continue
    
    return False

def is_embedded_scheme(url):
    """Check if URL contains an embedded scheme (e.g., javascript:, data:)."""
    scheme = urllib.parse.urlparse(url).scheme.lower()
    dangerous_schemes = ['javascript', 'data', 'vbscript', 'file']
    return scheme in dangerous_schemes

def is_default_port(scheme, port):
    """Check if port is the default for the scheme."""
    if scheme == 'http' and port != 80:
        return False
    if scheme == 'https' and port != 443:
        return False
    return True

def fetch_text(url, transport, resolve_host_func):
    """Fetch text from a URL with strict safety checks."""
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Check scheme
    if parsed_url.scheme.lower() not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Check port
    port = parsed_url.port
    if port is None:
        port = 80 if parsed_url.scheme.lower() == 'http' else 443
    
    if not is_default_port(parsed_url.scheme, port):
        raise ValueError("Only default ports are allowed")
    
    # Check for embedded schemes in the URL
    if is_embedded_scheme(url):
        raise ValueError("Embedded schemes are not allowed")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if hostname is None:
        raise ValueError("No hostname in URL")
    
    ip_addresses = resolve_host_func(hostname)
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for hostname")
    
    # Check for public addressing
    for ip in ip_addresses:
        if is_public_address(ip):
            raise ValueError("Public addressing is not allowed")
    
    # Fetch with redirects
    max_redirects = 5
    current_url = url
    redirect_count = 0
    
    while redirect_count <= max_redirects:
        # Make the request
        try:
            req = urllib.request.Request(current_url)
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Request failed: {str(e)}")
        
        status, headers, body = response
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for Location header
        location_header = headers.get('location', None)
        if location_header:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Parse the new URL
            new_parsed = urllib.parse.urlparse(location_header)
            
            # Check for embedded schemes
            if is_embedded_scheme(location_header):
                raise ValueError("Embedded schemes in redirect not allowed")
            
            # Check scheme
            if new_parsed.scheme.lower() not in ('http', 'https'):
                raise ValueError("Redirect scheme not allowed")
            
            # Check port
            new_port = new_parsed.port
            if new_port is None:
                new_port = 80 if new_parsed.scheme.lower() == 'http' else 443
            
            if not is_default_port(new_parsed.scheme, new_port):
                raise ValueError("Redirect port not allowed")
            
            # Resolve new hostname
            new_hostname = new_parsed.hostname
            if new_hostname is None:
                raise ValueError("No hostname in redirect URL")
            
            new_ip_addresses = resolve_host_func(new_hostname)
            if not new_ip_addresses:
                raise ValueError("No IP addresses resolved for redirect hostname")
            
            # Check for public addressing
            for ip in new_ip_addresses:
                if is_public_address(ip):
                    raise ValueError("Public addressing in redirect not allowed")
            
            # Update current URL
            current_url = location_header
        else:
            break
    
    return body
