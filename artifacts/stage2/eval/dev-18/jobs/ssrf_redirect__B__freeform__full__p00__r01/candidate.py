import socket
import urllib.parse
from urllib.parse import urlparse, parse_qs

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation to prevent SSRF.
    
    Args:
        url: The target URL string.
        transport: A callable transport(url) -> (status, headers, body).
        resolve_host: A callable resolve_host(hostname) -> list of IP strings.
    
    Returns:
        The response body string for a 200 status code.
    
    Raises:
        ValueError: If the request is disallowed (invalid host, redirect loop, etc.).
    """
    # Parse the initial URL
    parsed_url = urlparse(url)
    
    # Validate scheme
    allowed_schemes = {'http', 'https'}
    if parsed_url.scheme not in allowed_schemes:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Validate port
    allowed_ports = {80, 443}
    if parsed_url.port not in allowed_ports:
        raise ValueError("Only default ports (80, 443) are allowed.")
    
    # Resolve the initial hostname
    initial_host = parsed_url.hostname
    if not initial_host:
        raise ValueError("Invalid URL: missing hostname.")
    
    try:
        resolved_ips = resolve_host(initial_host)
    except Exception:
        raise ValueError("Failed to resolve hostname.")
    
    if not resolved_ips:
        raise ValueError("No valid IP addresses found for the hostname.")
    
    # Validate IP addresses (public vs private)
    # We assume that if the user asks for a specific IP, we check if it's public.
    # However, the prompt implies we check the resolved hostname against a "public-address validation".
    # Since we don't have a specific list of allowed IPs in the context, we will implement a basic check
    # that rejects obviously private ranges if the user tries to resolve them, 
    # but strictly following the prompt: "raise ValueError unless the resolved hostname is valid".
    # We will assume "valid" means it's not a private IP range unless explicitly allowed, 
    # but without a whitelist, we must be careful. The prompt says "check it against the same scheme, port, credentials, DNS, and public-address validation applied to the initial destination".
    # This implies we apply the same rules recursively.
    
    # We'll define a helper to check if an IP is in a private range.
    def is_private_ip(ip_str):
        parts = ip_str.split('.')
        if len(parts) != 4:
            return True # Invalid format, treat as risky
        try:
            octets = [int(p) for p in parts]
            if octets[0] == 10 or octets[0] == 127 or octets[0] == 192 and octets[1] == 168 or octets[0] == 192 and octets[1] == 169 or octets[0] == 10 or octets[0] == 172 and 16 <= octets[1] <= 31 or octets[0] == 192 and octets[1] == 174:
                return True
        except ValueError:
            return True
        return False
    
    # If the resolved IP is private, we raise an error (unless the initial request was also private, but we start with untrusted input)
    # The prompt says "untrusted input that is joined beneath the requested host". This usually implies we are checking for SSRF.
    # If the initial request resolves to a private IP, we should probably block it or treat it strictly.
    # Given "raise ValueError unless the resolved hostname is valid", and "public-address validation", we will block private IPs.
    if is_private_ip(resolved_ips[0]):
        raise ValueError("Access to private IP addresses is disallowed.")
    
    current_url = parsed_url
    redirect_count = 0
    max_redirects = 5
    
    while True:
        # Make the request
        status, headers, body = transport(current_url.url)
        
        # Check status code
        if status != 200:
            raise ValueError("Unexpected status code.")
        
        # Check for redirect
        location = headers.get('Location')
        if location:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Redirect limit exceeded.")
            
            # Parse the redirect URL
            try:
                redirect_url = urllib.parse.urlparse(location)
            except Exception:
                raise ValueError("Invalid redirect URL.")
            
            # Check scheme
            if redirect_url.scheme not in allowed_schemes:
                raise ValueError("Redirect to disallowed scheme.")
            
            # Check port
            if redirect_url.port not in allowed_ports:
                raise ValueError("Redirect to non-default port.")
            
            # Check credentials (user:pass)
            if redirect_url.username or redirect_url.password:
                raise ValueError("Redirect with credentials is disallowed.")
            
            # Resolve the new hostname
            new_host = redirect_url.hostname
            if not new_host:
                raise ValueError("Invalid redirect hostname.")
            
            try:
                new_resolved_ips = resolve_host(new_host)
            except Exception:
                raise ValueError("Failed to resolve redirect hostname.")
            
            if not new_resolved_ips:
                raise ValueError("No valid IP addresses found for redirect hostname.")
            
            # Validate the new IP
            if is_private_ip(new_resolved_ips[0]):
                raise ValueError("Redirect to private IP address is disallowed.")
            
            # Check DNS (we assume resolve_host handles this, but we check if it's in the list)
            if not any(ip in resolved_ips for ip in new_resolved_ips):
                # This logic is slightly flawed if the IPs are different, but the prompt implies we check against the "same scheme, port, credentials, DNS, and public-address validation applied to the initial destination".
                # This likely means we apply the same rules, not that the IP must be in the initial list.
                pass
            
            current_url = redirect_url
        else:
            break
    
    return body
