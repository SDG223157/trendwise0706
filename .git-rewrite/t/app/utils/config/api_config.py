"""
Configuration file for API settings and credentials
"""

ROIC_API = {
    'key': "a365bff224a6419fac064dd52e1f80d9",
    'base_url': "https://api.roic.ai/v1/rql"
}

# Default parameters for API requests
API_DEFAULTS = {
    'retries': 3,
    'timeout': 30,
    'backoff_factor': 0.5
}
