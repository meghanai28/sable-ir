import re
import ipaddress

def fetch_text(url, transport, resolve_host):
    # Parse scheme
    scheme_match = re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*)://', url)
    if not scheme_match:
        raise ValueError("Invalid URL: missing scheme")
    scheme = scheme_match.group(1).lower()
    
    # Extract authority part (between :// and next /, ?, or #)
    rest = url[scheme_match.end():]
    
    # Find end of authority
    authority_end = len(rest)
    for delim in ['/', '?', '#']:
        pos = rest.find(delim)
        if pos != -1 and pos < authority_end:
            authority_end = pos
    
    authority = rest[:authority_end]
    
    # Extract userinfo, host, port from authority
    if '@' in authority:
        _, authority = authority.rsplit('@', 1)
    
    # Determine host and port
    if authority.startswith('['):
        # IPv6 literal
        bracket_end = authority.find(']')
        if bracket_end == -1:
            raise ValueError("Invalid URL: unclosed IPv6 literal")
        host = authority[:bracket_end + 1]
        port_part = authority[bracket_end + 1:]
        if port_part.startswith(':'):
            port_str = port_part[1:]
        else:
            port_str = ''
    else:
        if ':' in authority:
            host, port_str = authority.rsplit(':', 1)
        else:
            host = authority
            port_str = ''
    
    # Validate scheme and port
    if scheme == 'http':
        if port_str == '':
            port = 80
        else:
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError("Invalid port")
    elif scheme == 'https':
        if port_str == '':
            port = 443
        else:
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError("Invalid port")
    else:
        raise ValueError("Invalid scheme")
    
    # Validate default ports
    if scheme == 'http' and port != 80:
        raise ValueError("Invalid port for http")
    if scheme == 'https' and port != 443:
        raise ValueError("Invalid port for https")
    
    # Validate hostname (not empty, not IP literal)
    if not host:
        raise ValueError("Empty host")
    
    # Remove brackets from IPv6 for resolve_host
    if host.startswith('[') and host.endswith(']'):
        hostname = host[1:-1]
    else:
        hostname = host
    
    # Check if hostname looks like an IP address
    try:
        ipaddress.ip_address(hostname)
        raise ValueError("IP address not allowed as host")
    except ValueError:
        pass  # Not an IP address, good
    
    # Resolve host and check public IPs
    ips = resolve_host(hostname)
    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise ValueError("Non-public IP address")
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check for redirect
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    # Check for success
    if status == 200:
        return body
    
    raise ValueError(f"Unexpected status: {status}")
