import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    MAX_REDIRECTS = 5
    redirect_count = 0
    
    def validate_url(parsed_url):
        if parsed_url.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        if not parsed_url.hostname:
            raise ValueError("URL must have a hostname")
        
        default_port = 443 if parsed_url.scheme == 'https' else 80
        
        if parsed_url.port is not None and parsed_url.port != default_port:
            raise ValueError("Only default ports are allowed")
        
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Credentials in URLs are not allowed")
        
        hostname = parsed_url.hostname
        
        if hostname.startswith('[') and hostname.endswith(']'):
            raise ValueError("IPv6 literals are not allowed")
        
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            raise ValueError("IPv4 literals are not allowed")
        
        resolved_ips = resolve_host(hostname)
        
        if not resolved_ips:
            raise ValueError("Could not resolve hostname")
        
        for ip in resolved_ips:
            if ip.startswith('127.') or ip == '127.0.0.1':
                raise ValueError("Loopback addresses are not allowed")
            if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
                if ip.startswith('172.'):
                    octets = ip.split('.')
                    if len(octets) >= 2:
                        second_octet = int(octets[1])
                        if 16 <= second_octet <= 31:
                            raise ValueError("Private addresses are not allowed")
                else:
                    raise ValueError("Private addresses are not allowed")
            if ip.startswith('169.254.'):
                raise ValueError("Link-local addresses are not allowed")
            if ip == '0.0.0.0':
                raise ValueError("Invalid address")
            if ip.startswith('::') or ip == '::1':
                raise ValueError("IPv6 loopback or unspecified are not allowed")
            if ip.startswith('fc') or ip.startswith('fd'):
                raise ValueError("IPv6 unique local addresses are not allowed")
            if ip.startswith('fe80:'):
                raise ValueError("IPv6 link-local addresses are not allowed")
        
        return parsed_url
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        validate_url(parsed)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                raise ValueError("Too many redirects")
            
            location = None
            for header_name, header_value in headers:
                if header_name.lower() == 'location':
                    location = header_value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = resolve_location(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
