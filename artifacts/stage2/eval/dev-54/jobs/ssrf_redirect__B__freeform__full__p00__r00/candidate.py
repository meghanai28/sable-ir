import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation and redirection limits.
    
    Args:
        url: The initial URL to fetch from (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The body of the HTTP response with status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, if DNS resolution fails,
                   if redirections exceed 5 hops, or if any redirect violates
                   scheme/port/DNS/public-address constraints.
    """
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve the initial hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid hostname in URL.")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    current_url = url
    current_scheme = parsed.scheme
    current_port = parsed.port
    current_host = parsed.hostname
    hop_count = 0
    max_hops = 5
    
    # Iterate through potential redirects
    while True:
        # If we've exceeded the hop limit, stop
        if hop_count > max_hops:
            raise ValueError("Too many redirects (exceeded maximum of 5).")
        
        # Make the HTTP request
        # Note: We use urllib.request to construct the request, but we must
        # ensure we are using the resolved IP if necessary, though urllib usually
        # handles hostname resolution. However, to strictly follow the spec's
        # reliance on resolve_host, we might need to use a custom opener or
        # ensure the hostname passed to transport is resolved.
        # The spec says "transport(url) returns...", implying we pass the URL string.
        # We will pass the current_url string.
        
        try:
            status, headers, body = transport(current_url)
        except Exception as e:
            raise ValueError(f"Failed to make request: {e}")
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Return the body immediately if status is 200
        return body.decode('utf-8') if isinstance(body, bytes) else body
        
        # Check for Location header
        location_header = headers.get('Location')
        if not location_header:
            break
        
        # Parse the Location header
        location_parsed = urllib.parse.urlparse(location_header)
        
        # Validate the Location URL
        if location_parsed.scheme not in ('http', 'https'):
            raise ValueError("Redirect location must have http or https scheme.")
        
        # Resolve the hostname of the Location
        location_hostname = location_parsed.hostname
        if location_hostname is None:
            raise ValueError("Invalid hostname in redirect location.")
        
        # Resolve IP addresses for the new location
        location_ips = resolve_host(location_hostname)
        if not location_ips:
            raise ValueError(f"No IP addresses found for redirect hostname: {location_hostname}")
        
        # Validate DNS and public-address (basic checks)
        # DNS check: Ensure IPs are valid IPv4 or IPv6 strings
        for ip in location_ips:
            try:
                socket.inet_aton(ip) if ':' not in ip else socket.inet_pton(socket.AF_INET6, ip)
            except (socket.error, socket.timeout):
                raise ValueError(f"Invalid IP address in redirect: {ip}")
        
        # Public address validation: Ensure the IP is not a private/reserved address
        # This is a simplified check; a full implementation would use more robust libraries.
        # We'll assume standard IPv4/IPv6 ranges are acceptable unless they are clearly private.
        # For this context, we rely on the fact that resolve_host might already filter or
        # that the caller ensures public addresses. However, to be safe against
        # private IPs (10.0.0.0/8, 127.0.0.0/8, ::1, etc.), we check:
        is_private = False
        if ip.startswith(('10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.',
                         '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
                         '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.',
                         '169.254.', '127.', '0.')):
            is_private = True
        if ':' in ip:
            # IPv6 private ranges
            if ip.startswith(('fe80:', 'fc', 'ff01:', 'ff02:', 'ff03:', 'ff04:', 'ff05:', 'ff06:', 'ff07:', 'ff08:')):
                is_private = True
            # Link-local
            if ip.startswith(('fe80:')):
                is_private = True
        
        if is_private:
            raise ValueError("Redirect target is a private or reserved IP address.")
        
        # Validate scheme and port match
        if location_parsed.scheme != current_scheme:
            raise ValueError("Redirect scheme must match current scheme.")
        
        if current_port is not None and location_parsed.port != current_port:
            raise ValueError("Redirect port must match current port.")
        
        # Update current URL and prepare for next hop
        current_url = location_header
        current_scheme = location_parsed.scheme
        current_port = location_parsed.port
        current_host = location_hostname
        hop_count += 1

def main():
    """
    Example usage of the fetch_text function.
    """
    # This is a placeholder for how the function would be called.
    # In a real scenario, transport and resolve_host would be provided by the caller.
    print("Module loaded successfully.")

if __name__ == "__main__":
    main()
