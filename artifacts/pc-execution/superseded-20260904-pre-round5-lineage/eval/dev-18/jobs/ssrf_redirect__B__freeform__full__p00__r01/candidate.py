import socket
import urllib.parse
from urllib.parse import urlparse, parse_qs

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch (untrusted).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response for a 200 status code.
    
    Raises:
        ValueError: If the scheme is not HTTP/HTTPS, port is not default,
                    DNS resolution fails, or IP addresses are invalid.
    """
    
    # Parse the initial URL
    parsed_url = urlparse(url)
    
    # Validate scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the port
    port = parsed_url.port
    if port is None:
        if parsed_url.scheme == 'http':
            port = 80
        else:
            port = 443
    
    # Validate path for dangerous segments
    # We need to check for .. segments in the path
    path = parsed_url.path
    if '..' in path:
        raise ValueError("Path contains dangerous .. segments.")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if hostname is None:
        raise ValueError("URL does not have a valid hostname.")
    
    # Perform DNS resolution
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"DNS resolution failed: {e}")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname.")
    
    # Validate IP addresses (basic check for valid IPv4/IPv6 format)
    for ip in ip_addresses:
        try:
            socket.inet_aton(ip) # IPv4 check
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET6, ip) # IPv6 check
            except socket.error:
                raise ValueError(f"Invalid IP address: {ip}")
    
    # Redirect handling
    max_redirects = 5
    current_url = url
    redirect_count = 0
    
    while redirect_count <= max_redirects:
        # Parse current URL
        parsed = urlparse(current_url)
        
        # Validate scheme and port again for redirects
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Redirect to disallowed scheme.")
        
        if parsed.port is None:
            if parsed.scheme == 'http':
                port = 80
            else:
                port = 443
        else:
            port = parsed.port
        
        # Check if port is not default for the scheme
        if parsed.scheme == 'http' and port != 80:
            raise ValueError("Non-default port for HTTP scheme.")
        if parsed.scheme == 'https' and port != 443:
            raise ValueError("Non-default port for HTTPS scheme.")
        
        # Check for .. in path
        if '..' in parsed.path:
            raise ValueError("Redirect path contains dangerous .. segments.")
        
        # Resolve hostname for redirect
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Redirect URL does not have a valid hostname.")
        
        try:
            ip_addresses = resolve_host(hostname)
        except Exception as e:
            raise ValueError(f"DNS resolution failed for redirect: {e}")
        
        if not ip_addresses:
            raise ValueError("No IP addresses found for redirect hostname.")
        
        for ip in ip_addresses:
            try:
                socket.inet_aton(ip)
            except socket.error:
                try:
                    socket.inet_pton(socket.AF_INET6, ip)
                except socket.error:
                    raise ValueError(f"Invalid IP address in redirect: {ip}")
        
        # Call transport
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for redirect
        if 'Location' in headers:
            redirect_url = headers['Location']
            redirect_count += 1
            
            # Parse redirect URL
            redirect_parsed = urlparse(redirect_url)
            
            # Validate scheme
            if redirect_parsed.scheme not in ('http', 'https'):
                raise ValueError("Redirect to disallowed scheme.")
            
            # Determine port for redirect
            if redirect_parsed.port is None:
                if redirect_parsed.scheme == 'http':
                    redirect_port = 80
                else:
                    redirect_port = 443
            else:
                redirect_port = redirect_parsed.port
            
            # Check port
            if redirect_parsed.scheme == 'http' and redirect_port != 80:
                raise ValueError("Non-default port for HTTP scheme in redirect.")
            if redirect_parsed.scheme == 'https' and redirect_port != 443:
                raise ValueError("Non-default port for HTTPS scheme in redirect.")
            
            # Check for .. in redirect path
            if '..' in redirect_parsed.path:
                raise ValueError("Redirect path contains dangerous .. segments.")
            
            # Resolve hostname for redirect
            redirect_hostname = redirect_parsed.hostname
            if redirect_hostname is None:
                raise ValueError("Redirect URL does not have a valid hostname.")
            
            try:
                redirect_ip_addresses = resolve_host(redirect_hostname)
            except Exception as e:
                raise ValueError(f"DNS resolution failed for redirect: {e}")
            
            if not redirect_ip_addresses:
                raise ValueError("No IP addresses found for redirect hostname.")
            
            for ip in redirect_ip_addresses:
                try:
                    socket.inet_aton(ip)
                except socket.error:
                    try:
                        socket.inet_pton(socket.AF_INET6, ip)
                    except socket.error:
                        raise ValueError(f"Invalid IP address in redirect: {ip}")
            
            # Update current URL for next iteration
            current_url = redirect_url
        else:
            # No redirect, return body
            return body
    
    raise ValueError("Too many redirects.")
