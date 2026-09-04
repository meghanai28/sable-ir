import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    current_url = url
    hops = 0
    max_hops = 5
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed URL scheme")
        
        if scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Disallowed non-default port")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        if '@' in parsed.netloc:
            raise ValueError("Disallowed credentials in URL")
        
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No IP addresses resolved")
        
        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError("Invalid IP address")
            
            if ip.is_loopback:
                raise ValueError("Disallowed loopback address")
            if ip.is_private:
                raise ValueError("Disallowed private address")
            if ip.is_reserved:
                raise ValueError("Disallowed reserved address")
            if ip.is_multicast:
                raise ValueError("Disallowed multicast address")
            if ip.is_link_local:
                raise ValueError("Disallowed link-local address")
            if ip.version == 6 and ip.ipv4_mapped is not None:
                ip = ip.ipv4_mapped
                if ip.is_loopback:
                    raise ValueError("Disallowed loopback address")
                if ip.is_private:
                    raise ValueError("Disallowed private address")
                if ip.is_reserved:
                    raise ValueError("Disallowed reserved address")
                if ip.is_multicast:
                    raise ValueError("Disallowed multicast address")
                if ip.is_link_local:
                    raise ValueError("Disallowed link-local address")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status <= 399:
            hops += 1
            if hops > max_hops:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header in redirect")
            
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError("Unsupported HTTP status: {}".format(status))
