import re
import ipaddress
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    def validate_url(u):
        parsed = urlparse(u)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
            raise ValueError("Invalid port for HTTP")
        if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
            raise ValueError("Invalid port for HTTPS")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials not allowed")
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            ip_addrs = [hostname]
        elif re.match(r'^[0-9a-fA-F:]+$', hostname) and ':' in hostname:
            ip_addrs = [hostname]
        else:
            ip_addrs = resolve_host(hostname)
            if not ip_addrs:
                raise ValueError("DNS resolution failed")
        for addr in ip_addrs:
            try:
                ip = ipaddress.ip_address(addr)
                if ip.is_private:
                    raise ValueError("Private IP not allowed")
                if ip.is_loopback:
                    raise ValueError("Loopback IP not allowed")
                if ip.is_link_local:
                    raise ValueError("Link-local IP not allowed")
                if ip.is_multicast:
                    raise ValueError("Multicast IP not allowed")
                if ip.is_reserved:
                    raise ValueError("Reserved IP not allowed")
                if ip.is_unspecified:
                    raise ValueError("Unspecified IP not allowed")
                if ip.version == 4:
                    if ip == ipaddress.ip_address('0.0.0.0'):
                        raise ValueError("Unspecified IP not allowed")
                if hasattr(ip, 'is_global') and not ip.is_global:
                    if not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
                        pass
            except ValueError as e:
                if "not allowed" in str(e):
                    raise
                raise ValueError("Invalid IP address")
        return u

    current_url = validate_url(url)
    redirect_count = 0
    max_redirects = 5

    while True:
        status, headers, body = transport(current_url)
        if status == 200:
            return body
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            next_url = urljoin(current_url, location)
            current_url = validate_url(next_url)
            continue
        raise ValueError(f"Unexpected status: {status}")
