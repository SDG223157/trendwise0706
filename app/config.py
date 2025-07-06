import os

class Config:
    # Database configuration - prioritize Coolify database
    # 1. Check for DATABASE_URL environment variable first (Coolify standard)
    SQLALCHEMY_DATABASE_URI = (
        os.getenv('DATABASE_URL') or
        # 2. Check for PostgreSQL credentials (common in Coolify)
        (
            f"postgresql://{os.getenv('POSTGRES_USER')}:"
            f"{os.getenv('POSTGRES_PASSWORD')}@"
            f"{os.getenv('POSTGRES_HOST')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB')}"
            if all([os.getenv('POSTGRES_USER'), os.getenv('POSTGRES_PASSWORD'), 
                    os.getenv('POSTGRES_HOST'), os.getenv('POSTGRES_DB')])
            else
            # 3. Check for MySQL credentials 
            (
                f"mysql+pymysql://{os.getenv('MYSQL_USER')}:"
                f"{os.getenv('MYSQL_PASSWORD')}@"
                f"{os.getenv('MYSQL_HOST')}:"
                f"{os.getenv('MYSQL_PORT', '3306')}/"
                f"{os.getenv('MYSQL_DATABASE')}"
                if all([os.getenv('MYSQL_USER'), os.getenv('MYSQL_PASSWORD'), 
                        os.getenv('MYSQL_HOST'), os.getenv('MYSQL_DATABASE')])
                else 
                # 4. Fallback to SQLite for local development only
                "sqlite:///trendwise.db"
            )
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_TIMEOUT = 30
    
    # Secret key configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DEBUG = False
    TESTING = False
    # Google OAuth configuration
     # Google OAuth config
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
    SERVER_NAME = os.getenv('SERVER_NAME')
    PREFERRED_URL_SCHEME = "https"
    # OAuth redirect URI
    GOOGLE_REDIRECT_URI = f"{PREFERRED_URL_SCHEME}://{SERVER_NAME}/auth/google/callback"
    
    # Security configuration
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    PROXY_FIX = True
    
    # Admin user configuration (traditional login system)
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@cfa187260.com')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')  # Set this in your environment variables
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_FIRST_NAME = os.getenv('ADMIN_FIRST_NAME', 'Admin')
    ADMIN_LAST_NAME = os.getenv('ADMIN_LAST_NAME', 'User')
    
    # Session-based admin password (alternative system - can be disabled)
    ADMIN_SESSION_PASSWORD = os.getenv('ADMIN_SESSION_PASSWORD')
    ADMIN_SESSION_PASSWORD_HASH = os.getenv('ADMIN_SESSION_PASSWORD_HASH')