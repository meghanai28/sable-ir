import re
import ipaddress
from urllib.parse import urlparse, urlunparse, urljoin

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    redirect_count = 0
    
    def validate_url(url_str):
        parsed = urlparse(url_str)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed scheme")
        
        default_port = 80 if scheme == 'http' else 443
        
        host = parsed.hostname
        if host is None:
            raise ValueError("Missing hostname")
        
        port = parsed.port
        if port is not None and port != default_port:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            validate_credentials(parsed.username, parsed.password)
        
        host_str = host.lower()
        if host_str.startswith('[') and host_str.endswith(']'):
            host_str = host_str[1:-1]
        
        try:
            ip_addr = ipaddress.ip_address(host_str)
            validate_ip(ip_addr)
        except ValueError:
            ips = resolve_host(host)
            if not ips:
                raise ValueError("Host resolution failed")
            for ip_text in ips:
                try:
                    ip_addr = ipaddress.ip_address(ip_text)
                except ValueError:
                    raise ValueError("Invalid IP from DNS")
                validate_ip(ip_addr)
        
        netloc = host
        if port is not None:
            netloc = f"{host}:{port}"
        
        normalized = urlunparse((
            scheme,
            netloc,
            parsed.path or '/',
            parsed.params,
            parsed.query,
            ''
        ))
        
        return normalized, scheme, host
    
    def validate_credentials(username, password):
        if username is not None and username != '':
            raise ValueError("Embedded credentials not allowed")
        if password is not None and password != '':
            raise ValueError("Embedded credentials not allowed")
    
    def validate_ip(ip_addr):
        if ip_addr.version == 4:
            if ip_addr.is_private:
                raise ValueError("Private IPv4 address")
            if ip_addr.is_loopback:
                raise ValueError("Loopback IPv4 address")
            if ip_addr.is_link_local:
                raise ValueError("Link-local IPv4 address")
            if ip_addr.is_multicast:
                raise ValueError("Multicast IPv4 address")
            if ip_addr.is_reserved:
                raise ValueError("Reserved IPv4 address")
            if ip_addr.is_unspecified:
                raise ValueError("Unspecified IPv4 address")
            if ip_addr == ipaddress.ip_address('0.0.0.0'):
                raise ValueError("Unspecified IPv4 address")
        elif ip_addr.version == 6:
            if ip_addr.is_private:
                raise ValueError("Private IPv6 address")
            if ip_addr.is_loopback:
                raise ValueError("Loopback IPv6 address")
            if ip_addr.is_link_local:
                raise ValueError("Link-local IPv6 address")
            if ip_addr.is_multicast:
                raise ValueError("Multicast IPv6 address")
            if ip_addr.is_reserved:
                raise ValueError("Reserved IPv6 address")
            if ip_addr.is_unspecified:
                raise ValueError("Unspecified IPv6 address")
            if ip_addr.ipv4_mapped is not None:
                validate_ip(ip_addr.ipv4_mapped)
    
    def make_request(request_url):
        nonlocal redirect_count
        
        validated_url, scheme, host = validate_url(request_url)
        
        status, headers, body = transport(validated_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            if redirect_count >= max_redirects:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                for key in headers:
                    if key.lower() == 'location':
                        location = headers[key]
                        break
            
            if location is None or location == '':
                raise ValueError("Missing or empty Location header")
            
            try:
                absolute_url = urljoin(validated_url, location)
            except Exception:
                raise ValueError("Malformed redirect location")
            
            redirect_count += 1
            return make_request(absolute_url)
        
        raise ValueError(f"Unexpected status: {status}")
    
    return make_request(url)
