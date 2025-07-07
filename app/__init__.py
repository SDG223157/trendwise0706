from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
import logging
from app.config import Config
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_migrate import Migrate  # Import Migrate
# from app.models import NewsArticle, ArticleMetric, ArticleSymbol, User  # Import models after db is initialized
import markdown
from flask_login import current_user
from app.utils.activity_logger import log_user_activity

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

db = SQLAlchemy()  # Define SQLAlchemy instance
migrate = Migrate()  # Initialize Migrate instance
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'error'

def markdown_to_html(text):
    import re
    
    # Pre-process text to convert dashes to bullet points for better display
    if text:
        # Convert lines starting with "- " to "• " for visual enhancement
        text = re.sub(r'^- ', '• ', text, flags=re.MULTILINE)
    
    return markdown.markdown(text or '', extensions=[
        'fenced_code', 
        'tables', 
        'nl2br',  # Convert newlines to <br> tags for better formatting
        'sane_lists',  # Better list handling
        'md_in_html'  # Allow markdown inside HTML
    ])

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Add ProxyFix middleware for HTTPS handling
    app.wsgi_app = ProxyFix(
        app.wsgi_app, 
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1
    )

    # Initialize extensions
    
    db.init_app(app)  # Link the db with the app
    migrate.init_app(app, db)  # Link Flask-Migrate with the app and db
   
    login_manager.init_app(app)
    # from app.models import NewsArticle, ArticleMetric, ArticleSymbol, User  # Import models after db is initialized
   

    # Force HTTPS
    @app.before_request
    def before_request():
        if not request.is_secure and not app.debug:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    with app.app_context():
        try:
            # No need to call db.create_all() because Flask-Migrate will handle migrations
            # db.create_all()
            logger.info("Database tables created successfully")

            logger.info("Database initialized using Flask-Migrate")
            from app.models import NewsArticle, ArticleMetric, ArticleSymbol, User  # Import models after db is initialized
            db.create_all()

            # Check if admin user exists, if not create one from environment variables
            admin_email = app.config.get('ADMIN_EMAIL')
            admin_password = app.config.get('ADMIN_PASSWORD')
            
            if admin_email and admin_password:
                admin_user = User.query.filter_by(email=admin_email).first()
                if not admin_user:
                    admin = User(
                        email=admin_email,
                        username=app.config.get('ADMIN_USERNAME', 'admin'),
                        first_name=app.config.get('ADMIN_FIRST_NAME', 'Admin'),
                        last_name=app.config.get('ADMIN_LAST_NAME', 'User'),
                        is_admin=True,
                        role='admin',
                        is_active=True
                    )
                    admin.set_password(admin_password)
                    db.session.add(admin)
                    db.session.commit()
                    logger.info(f"Admin user created successfully: {admin_email}")
                else:
                    # Update existing admin user password if it changed
                    admin_user.set_password(admin_password)
                    db.session.commit()
                    logger.info(f"Admin user password updated: {admin_email}")
            else:
                logger.warning("ADMIN_EMAIL and ADMIN_PASSWORD not set in environment variables. No admin user created.")
        except Exception as e:
            logger.error(f"Error during database initialization: {str(e)}")

        # Register blueprints
        from app.routes import bp as main_bp
        logger.debug(f"Registering main blueprint: {main_bp.name}")
        app.register_blueprint(main_bp)

        try:
            from app.auth.routes import bp as auth_bp
            logger.debug(f"Registering auth blueprint: {auth_bp.name}")
            app.register_blueprint(auth_bp, url_prefix='/auth')
        except Exception as e:
            logger.error(f"Error registering auth blueprint: {str(e)}")
            raise

        from app.user.routes import bp as user_bp
        logger.debug(f"Registering user blueprint: {user_bp.name}")
        app.register_blueprint(user_bp, url_prefix='/user')

        from app.stock import stock_bp
        logger.debug(f"Registering stock blueprint: {stock_bp.name}")
        app.register_blueprint(stock_bp, url_prefix='/stock')

        # Register admin blueprint
        try:
            from app.admin.routes import bp as admin_bp
            logger.debug(f"Registering admin blueprint: {admin_bp.name}")
            app.register_blueprint(admin_bp, url_prefix='/admin')
            logger.info("Admin blueprint registered successfully")
        except Exception as e:
            logger.error(f"Error registering admin blueprint: {str(e)}")
            logger.error("Admin blueprint registration failed, admin features will be unavailable")
            # Don't raise, just continue without admin features

        # Register news blueprint
        try:
            from app.news.routes import bp as news_bp
            logger.debug(f"Registering news blueprint: {news_bp.name}")
            app.register_blueprint(news_bp, url_prefix='/news')
        except Exception as e:
            logger.error(f"Error registering news blueprint: {str(e)}")
            raise

        # Initialize automated news AI scheduler
        try:
            from app.utils.scheduler.news_scheduler import news_scheduler
            news_scheduler.init_app(app)
            news_scheduler.start()
            logger.info("🤖 Automated news AI processing scheduler started successfully!")
        except Exception as e:
            logger.error(f"Failed to start news AI scheduler: {str(e)}")
            # Don't break the app if scheduler fails
            pass

        # Initialize automated news fetch scheduler
        try:
            from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
            news_fetch_scheduler.init_app(app)
            logger.info("📡 Automated news fetch scheduler initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize news fetch scheduler: {str(e)}")
            # Don't break the app if scheduler fails
            pass

        @app.context_processor
        def utility_processor():
            return {
                'now': datetime.now()
            }

        # Add utility function to check if a route exists
        @app.template_global()
        def route_exists(endpoint):
            try:
                # Check if the endpoint exists in the URL map
                for rule in app.url_map.iter_rules():
                    if rule.endpoint == endpoint:
                        return True
                return False
            except Exception as e:
                logger.error(f"Error checking if route exists: {str(e)}")
                return False

        # Debug: Print all registered endpoints
        logger.debug("Registered URLs:")
        for rule in app.url_map.iter_rules():
            logger.debug(f"{rule.endpoint}: {rule.rule}")

        # Error handlers with proper navigation
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            return render_template('errors/500.html'), 500

        # Add Markdown filter to Jinja2 environment
        app.jinja_env.filters['markdown'] = markdown_to_html

        # Add activity logging middleware
        @app.before_request
        def log_request_activity():
            # Disable automatic activity logging for activities other than login/logout
            # Login and logout are explicitly logged in auth/routes.py
            pass
            # Original code commented out below:
            """
            if current_user.is_authenticated:
                # Exclude static files and certain paths
                if not request.path.startswith('/static/') and not request.path.startswith('/favicon.ico'):
                    # Determine activity type based on route
                    activity_type = None
                    description = None
                    
                    if request.endpoint:
                        if 'news.fetch_news' == request.endpoint and request.method == 'POST':
                            activity_type = 'fetch_news'
                            symbols = request.get_json().get('symbols', [])
                            description = f"Fetched news for symbols: {', '.join(symbols[:5])}"
                            if len(symbols) > 5:
                                description += f" and {len(symbols) - 5} more"
                                
                        elif 'news.update_ai_summaries' == request.endpoint:
                            activity_type = 'update_ai_summaries'
                            
                        elif 'news.search' == request.endpoint:
                            activity_type = 'search_news'
                            symbol = request.args.get('symbol') or request.form.get('symbol')
                            description = f"Searched news for symbol: {symbol}" if symbol else "Searched news"
                        
                        # For APIs, we might want to log in a more structured way
                        elif request.path.startswith('/api/'):
                            activity_type = 'api_request'
                            description = f"API Call: {request.endpoint}"
                        
                    # If we've determined this is a loggable activity
                    if activity_type:
                        try:
                            log_user_activity(
                                current_user.id,
                                activity_type,
                                description=description
                            )
                        except Exception as e:
                            logger.error(f"Failed to log user activity: {str(e)}")
            """

    return app

# Add global exception handler
@db.event.listens_for(db.session, 'after_rollback')
def handle_after_rollback(session):
    logger.warning("Database session rollback occurred")