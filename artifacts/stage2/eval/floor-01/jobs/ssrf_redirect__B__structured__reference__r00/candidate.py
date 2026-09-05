import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    current_url = url
    redirect_count = 0
    
    while redirect_count < 5:
        # Validate current URL
        if not current_url:
            raise ValueError("URL cannot be empty")
        
        parsed = urllib.parse.urlparse(current_url)
        
        # Check for disallowed schemes (anything other than http or https)
        if parsed.scheme.lower() not in ('http', 'https'):
            raise ValueError("Disallowed scheme")
        
        # Check for embedded credentials
        if parsed.username or parsed.password:
            raise ValueError("Embedded credentials not allowed")
        
        # Validate host and port
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid hostname")
        
        # Check port
        port = parsed.port
        scheme = parsed.scheme.lower()
        
        if scheme == 'http':
            if port is not None and port != 80:
                raise ValueError("HTTP must use port 80")
        elif scheme == 'https':
            if port is not None and port != 443:
                raise ValueError("HTTPS must use port 443")
        
        # Resolve hostname
        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError("Hostname resolves to no addresses")
        
        # Check if any resolved address is not a global public address
        # Assuming "global public" means not a link-local, loopback, or private range
        # For simplicity in this context, we check against known private ranges
        is_public = True
        for ip in resolved_ips:
            ip_str = ip.split(':')[0]  # Remove port if present
            # Check for IPv4 private ranges
            if ip_str.startswith('10.') or ip_str.startswith('192.168.') or ip_str.startswith('172.'):
                if '.' in ip_str and not ip_str.startswith('172.16.') and not ip_str.startswith('172.17.') and not ip_str.startswith('172.18.') and not ip_str.startswith('172.19.') and not ip_str.startswith('172.20.') and not ip_str.startswith('172.21.') and not ip_str.startswith('172.22.') and not ip_str.startswith('172.23.') and not ip_str.startswith('172.24.') and not ip_str.startswith('172.25.') and not ip_str.startswith('172.26.') and not ip_str.startswith('172.27.') and not ip_str.startswith('172.28.') and not ip_str.startswith('172.29.') and not ip_str.startswith('172.30.') and not ip_str.startswith('172.31.'):
                    is_public = False
                    break
            # Check for IPv6 link-local (fe80:)
            if ip_str.startswith('fe80:'):
                is_public = False
                break
        
        if not is_public:
            raise ValueError("Non-public address detected")
        
        # Make the request
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Handle redirect
        location = headers.get('Location', '').strip()
        if not location:
            raise ValueError("Missing Location header in redirect")
        
        # Parse and validate redirect URL
        redirect_parsed = urllib.parse.urlparse(location)
        
        # Resolve relative URLs against current URL
        if not redirect_parsed.scheme:
            redirect_parsed = urllib.parse.urlunparse((redirect_parsed.scheme, redirect_parsed.netloc, redirect_parsed.path, redirect_parsed.params, redirect_parsed.query))
        
        # Apply same validation to new destination
        if not redirect_parsed.scheme.lower() in ('http', 'https'):
            raise ValueError("Disallowed scheme in redirect")
        
        if redirect_parsed.username or redirect_parsed.password:
            raise ValueError("Embedded credentials in redirect not allowed")
        
        redirect_hostname = redirect_parsed.hostname
        if not redirect_hostname:
            raise ValueError("Invalid hostname in redirect")
        
        redirect_port = redirect_parsed.port
        redirect_scheme = redirect_parsed.scheme.lower()
        
        if redirect_scheme == 'http':
            if redirect_port is not None and redirect_port != 80:
                raise ValueError("HTTP redirect must use port 80")
        elif redirect_scheme == 'https':
            if redirect_port is not None and redirect_port != 443:
                raise ValueError("HTTPS redirect must use port 443")
        
        redirect_resolved_ips = resolve_host(redirect_hostname)
        if not redirect_resolved_ips:
            raise ValueError("Redirect hostname resolves to no addresses")
        
        redirect_is_public = True
        for ip in redirect_resolved_ips:
            ip_str = ip.split(':')[0]
            if ip_str.startswith('10.') or ip_str.startswith('192.168.') or ip_str.startswith('172.'):
                if '.' in ip_str and not ip_str.startswith('172.16.') and not ip_str.startswith('172.17.') and not ip_str.startswith('172.18.') and not ip_str.startswith('172.19.') and not ip_str.startswith('172.20.') and not ip_str.startswith('172.21.') and not ip_str.startswith('172.22.') and not ip_str.startswith('172.23.') and not ip_str.startswith('172.24.') and not ip_str.startswith('172.25.') and not ip_str.startswith('172.26.') and not ip_str.startswith('172.27.') and not ip_str.startswith('172.28.') and not ip_str.startswith('172.29.') and not ip_str.startswith('172.30.') and not ip_str.startswith('172.31.'):
                    redirect_is_public = False
                    break
            if ip_str.startswith('fe80:'):
                redirect_is_public = False
                break
        
        if not redirect_is_public:
            raise ValueError("Non-public address in redirect detected")
        
        # Update current URL and increment redirect count
        current_url = redirect_parsed.geturl()
        redirect_count += 1
    
    raise ValueError("Too many redirects")
