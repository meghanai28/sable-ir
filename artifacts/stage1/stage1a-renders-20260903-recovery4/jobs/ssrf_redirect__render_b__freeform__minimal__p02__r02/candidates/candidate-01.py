import urllib.parse

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    redirect_count = 0
    current_url = url

    while True:
        parsed = urllib.parse.urlparse(current_url)

        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Scheme must be HTTP or HTTPS")

        default_port = 443 if parsed.scheme == 'https' else 80
        port = parsed.port

        if port is not None and port != default_port:
            raise ValueError("Non-default port not allowed")

        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")

        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")

        ip_addresses = resolve_host(hostname)

        for ip in ip_addresses:
            parts = ip.split('.')
            if len(parts) == 4:
                try:
                    octets = [int(p) for p in parts]
                    if all(0 <= o <= 255 for o in octets):
                        if octets[0] == 10:
                            raise ValueError("Non-public IP address")
                        if octets[0] == 172 and 16 <= octets[1] <= 31:
                            raise ValueError("Non-public IP address")
                        if octets[0] == 192 and octets[1] == 168:
                            raise ValueError("Non-public IP address")
                        if octets[0] == 127:
                            raise ValueError("Non-public IP address")
                        if octets[0] == 169 and octets[1] == 254:
                            raise ValueError("Non-public IP address")
                        if octets[0] >= 224:
                            raise ValueError("Non-public IP address")
                        if octets == [0, 0, 0, 0]:
                            raise ValueError("Non-public IP address")
                        if octets == [255, 255, 255, 255]:
                            raise ValueError("Non-public IP address")
                except ValueError:
                    raise ValueError("Non-public IP address")
            else:
                raise ValueError("Non-public IP address")

        netloc = hostname
        reconstructed = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        status, headers, body = transport(reconstructed)

        if status == 200:
            return body

        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")

            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")

            current_url = urllib.parse.urljoin(current_url, location)
            continue

        raise ValueError(f"Non-200 final status: {status}")
