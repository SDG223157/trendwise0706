from flask import current_app, url_for, redirect, request, flash
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests
import os
from functools import wraps

def create_google_oauth_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [url_for('auth.google_callback', _external=True)]
            }
        },
        scopes=['openid', 'email', 'profile']
    )
    return flow