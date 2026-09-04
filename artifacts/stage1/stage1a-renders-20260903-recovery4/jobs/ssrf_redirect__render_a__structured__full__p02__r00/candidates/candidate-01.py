import ipaddress
import urllib.parse


def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)

    scheme = parsed.scheme.lower()

    if scheme == "http":
        default_port = 80
    elif scheme == "https":
        default_port = 443
    else:
        raise ValueError("Invalid scheme")

    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname")

    port = parsed.port
    if port is None:
        port = default_port

    if port != default_port:
        raise ValueError("Non-default port")

    try:
        addr = ipaddress.ip_address(hostname)
        ip_texts = [str(addr)]
    except ValueError:
        ip_texts = resolve_host(hostname)
        if not ip_texts:
            raise ValueError("Host resolution failed")

    for ip_text in ip_texts:
        try:
            addr = ipaddress.ip_address(ip_text)
        except ValueError:
            raise ValueError("Invalid IP address")

        if addr.is_loopback:
            raise ValueError("Non-public IP")
        if addr.is_private:
            raise ValueError("Non-public IP")
        if addr.is_link_local:
            raise ValueError("Non-public IP")
        if addr.is_multicast:
            raise ValueError("Non-public IP")
        if addr.is_reserved:
            raise ValueError("Non-public IP")
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
            mapped = addr.ipv4_mapped
            if mapped.is_loopback or mapped.is_private or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved:
                raise ValueError("Non-public IP")

    status, headers, body = transport(url)

    if status == 200:
        if isinstance(body, bytes):
            return body.decode("utf-8")
        return str(body)

    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")

    raise ValueError("Unexpected status")
