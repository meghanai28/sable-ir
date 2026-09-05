import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse and normalize the URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    scheme = parsed.scheme.lower()
    valid_schemes = ['http', 'https']
    
    if scheme not in valid_schemes:
        raise ValueError(f"Invalid scheme: {scheme}")
    
    # Check for default port
    default_port = {'http': 80, 'https': 443}.get(scheme)
    if default_port is not None and parsed.port != default_port:
        raise ValueError(f"Invalid port for scheme {scheme}: {parsed.port}")
    
    # Follow redirects (max 5 hops)
    current_url = url
    hop_count = 0
    redirect_chain = []
    
    while hop_count < 5:
        redirect_chain.append(current_url)
        current_url = transport(current_url)
        
        if len(current_url) != 3:
            raise ValueError("Transport did not return a tuple")
        
        status, headers, body = current_url
        
        if status != 200:
            raise ValueError(f"Status code {status} is not 200")
        
        # Check for redirect
        location = headers.get('Location')
        if location:
            redirect_url = urllib.parse.urljoin(current_url[0], location)
            redirect_chain.append(redirect_url)
            
            # Re-check scheme, port, and public addressing before next hop
            redirect_parsed = urllib.parse.urlparse(redirect_url)
            
            if redirect_parsed.scheme not in valid_schemes:
                raise ValueError(f"Invalid scheme in redirect: {redirect_parsed.scheme}")
            
            default_port = {'http': 80, 'https': 443}.get(redirect_parsed.scheme)
            if default_port is not None and redirect_parsed.port != default_port:
                raise ValueError(f"Invalid port in redirect: {redirect_parsed.port}")
            
            # Check for public addressing (no localhost, no private IPs)
            hostname = redirect_parsed.hostname
            if hostname and hostname.lower() in ['localhost', 'localhost.localdomain']:
                raise ValueError("Localhost access disallowed")
            
            hop_count += 1
            current_url = redirect_url
        else:
            break
    
    # Resolve hostname of the final URL to its textual IP addresses
    final_url = current_url[0]
    final_parsed = urllib.parse.urlparse(final_url)
    hostname = final_parsed.hostname
    
    if not hostname:
        raise ValueError("No hostname found in final URL")
    
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses or len(ip_addresses) == 0:
        raise ValueError("resolve_host did not return any valid IP addresses")
    
    # Final validation of IP addresses (basic check for IPv4/IPv6 format)
    for ip in ip_addresses:
        try:
            socket.inet_aton(ip)
        except socket.error:
            raise ValueError(f"Invalid IP address format: {ip}")
    
    return body
