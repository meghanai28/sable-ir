import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Malformed URL")

    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Userinfo not allowed")

    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")

    if scheme == 'http':
        default_port = 80
    else:
        default_port = 443

    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Non-default port not allowed")

    resolved_ips = resolve_host(hostname)

    for ip_str in resolved_ips:
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError("Invalid IP address")

        if addr.is_loopback:
            raise ValueError("Loopback address not allowed")
        if addr.is_link_local:
            raise ValueError("Link-local address not allowed")
        if addr.is_private:
            raise ValueError("Private address not allowed")
        if addr.is_multicast:
            raise ValueError("Multicast address not allowed")
        if addr.is_reserved:
            raise ValueError("Reserved address not allowed")
        if addr.is_unspecified:
            raise ValueError("Unspecified address not allowed")

        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
            mapped = addr.ipv4_mapped
            if mapped.is_loopback or mapped.is_link_local or mapped.is_private or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                raise ValueError("Non-public IPv4-mapped address not allowed")

    status, headers, body = transport(url)

    if 300 <= status <= 399:
        raise ValueError("Redirect not allowed")

    if status != 200:
        raise ValueError("Non-200 status")

    return body
