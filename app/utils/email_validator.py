def is_email_domain_blocked(email):
    """Check if email domain is blocked from registration/login"""
    blocked_domains = ['testform.xyz']
    if '@' not in email:
        return False
    
    # Split email and ensure we have a valid domain part
    parts = email.split('@')
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False
    
    domain = parts[1].lower()
    return domain in blocked_domains 