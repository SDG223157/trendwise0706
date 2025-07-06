"""
Configuration file for API settings and credentials
"""
import os

ROIC_API = {
    'key': os.getenv("ROIC_API_KEY", ""),
    'base_url': "https://api.roic.ai/v1/rql"
}

# Default parameters for API requests
API_DEFAULTS = {
    'retries': 3,
    'timeout': 30,
    'backoff_factor': 0.5
}
