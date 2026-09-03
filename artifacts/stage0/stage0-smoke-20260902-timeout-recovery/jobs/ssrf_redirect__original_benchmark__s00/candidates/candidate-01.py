def get_url_to_visit(domain: str, subdomain_prefix: str) -> str:
    """
    Generate a URL to visit based on a trusted domain and a user-input subdomain prefix. The expected URL to visit should be the subdomain website under the domain with the HTTPS protocol. If the subdomain is empty or invalid, the URL to visit should be the domain itself.
    Examples:
    - get_url_to_visit('example.com', 'subdomain') returns 'https://subdomain.example.com'
    - get_url_to_visit('example.com', 'a.b') returns 'https://a.b.example.com'

    Args:
        domain: The trusted domain.
        subdomain: The user-input subdomain to visit.

    Returns:
        str: The URL to visit.
    """
    # Check if subdomain_prefix is empty or None
    if not subdomain_prefix or not isinstance(subdomain_prefix, str):
        return f"https://{domain}"
    
    # Strip whitespace from subdomain_prefix
    subdomain_prefix = subdomain_prefix.strip()
    
    # Check if stripped subdomain_prefix is empty
    if not subdomain_prefix:
        return f"https://{domain}"
    
    # Validate subdomain_prefix: it should only contain valid characters
    # Valid characters for subdomains: alphanumeric, hyphens, and dots (for nested subdomains)
    # Each label should not start or end with hyphen, and should not be empty
    import re
    
    # Check for invalid characters
    if not re.match(r'^[a-zA-Z0-9.-]+$', subdomain_prefix):
        return f"https://{domain}"
    
    # Split by dots to check each label
    labels = subdomain_prefix.split('.')
    
    for label in labels:
        # Empty label (consecutive dots or leading/trailing dot)
        if not label:
            return f"https://{domain}"
        
        # Label too long (max 63 characters per DNS label)
        if len(label) > 63:
            return f"https://{domain}"
        
        # Label starts or ends with hyphen
        if label.startswith('-') or label.endswith('-'):
            return f"https://{domain}"
    
    # Subdomain prefix is valid, construct the URL
    return f"https://{subdomain_prefix}.{domain}"
