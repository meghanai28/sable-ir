import re
import ipaddress

def fetch_text(url, transport, resolve_host):
    # Parse scheme
    scheme_match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*)://', url)
    if not scheme_match:
        raise ValueError("Invalid URL: missing scheme")
    scheme = scheme_match.group(1).lower()
    
    # Extract the rest after scheme://
    rest = url[scheme_match.end():]
    
    # Find the path start
    path_start = rest.find('/')
    if path_start == -1:
        authority = rest
        path = ''
    else:
        authority = rest[:path_start]
        path = rest[path_start:]
    
    # Extract hostname and port from authority
    # Check for userinfo (not allowed, but we need to handle the @)
    if '@' in authority:
        raise ValueError("Invalid URL: userinfo not allowed")
    
    # Check for IPv6 literal
    if authority.startswith('['):
        bracket_end = authority.find(']')
        if bracket_end == -1:
            raise ValueError("Invalid URL: unclosed IPv6 literal")
        host = authority[:bracket_end + 1]
        port_part = authority[bracket_end + 1:]
        if port_part:
            if not port_part.startswith(':'):
                raise ValueError("Invalid URL: invalid port")
            port_str = port_part[1:]
        else:
            port_str = ''
    else:
        # IPv4 or hostname
        colon_pos = authority.rfind(':')
        if colon_pos == -1:
            host = authority
            port_str = ''
        else:
            # Check if it's a port or part of IPv6
            if ':' in authority[:colon_pos]:
                # Could be IPv6 without brackets - invalid for our parser
                # Actually, check if it's a valid IPv6 without brackets
                host = authority
                port_str = ''
            else:
                host = authority[:colon_pos]
                port_str = authority[colon_pos + 1:]
    
    # Validate and determine port
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Invalid URL: scheme must be http or https")
    
    if port_str == '':
        port = default_port
    else:
        try:
            port = int(port_str)
            if port < 0 or port > 65535:
                raise ValueError
        except ValueError:
            raise ValueError("Invalid URL: invalid port")
    
    # Validate scheme/port combination
    if scheme == 'http' and port != 80:
        raise ValueError("Invalid URL: http must use port 80")
    if scheme == 'https' and port != 443:
        raise ValueError("Invalid URL: https must use port 443")
    
    # Validate hostname
    if not host:
        raise ValueError("Invalid URL: missing hostname")
    
    # Remove brackets from IPv6 for resolve_host
    if host.startswith('[') and host.endswith(']'):
        hostname = host[1:-1]
    else:
        hostname = host
    
    # Validate hostname doesn't contain invalid characters
    # Basic validation - should not contain path separators or query fragments
    if '/' in hostname or '?' in hostname or '#' in hostname:
        raise ValueError("Invalid URL: invalid hostname")
    
    # Resolve host and check IPs are public
    ip_addresses = resolve_host(hostname)
    
    for ip_str in ip_addresses:
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local or ip.is_unspecified:
                raise ValueError("Host resolved to non-public IP address")
        except ValueError:
            # If ipaddress raises ValueError, it might be an invalid IP string
            # But we still want to raise our own ValueError for non-public
            raise ValueError("Host resolved to non-public IP address")
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check for redirect
    if 300 <= status < 400:
        raise ValueError("Redirects not allowed")
    
    # Return body for 200, error otherwise
    if status == 200:
        return body
    
    raise ValueError(f"Unexpected status: {status}")
