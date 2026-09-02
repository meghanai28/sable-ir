import re


def get_url_to_visit(domain: str, subdomain_prefix: str) -> str:
    if not re.match(r"^[a-zA-Z0-9.-]+$", subdomain_prefix):
        return f"https://{domain}"
    return f"https://{subdomain_prefix}.{domain}"
