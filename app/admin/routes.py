from flask import render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import UserActivity, User, NewsArticle, ArticleSymbol, NewsSearchIndex
from datetime import datetime, timedelta
from functools import wraps
from app.admin import bp
from app.utils.cache.db_cache import db_cache
from app.utils.cache.user_cache import user_cache
import logging

logger = logging.getLogger(__name__)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports
        from app.utils.admin_auth import AdminAuth
        
        # Check if user has admin privileges OR session admin privileges
        user_is_admin = current_user.is_authenticated and current_user.is_admin
        session_is_admin = AdminAuth.has_session_admin_privileges()
        
        if not (user_is_admin or session_is_admin):
            flash("You need admin privileges to access this page. Please enter the admin password.", "warning")
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)
    return decorated_function

@bp.route("/")
@login_required
@admin_required
def index():
    """Admin dashboard index page"""
    logger.info("Accessing admin dashboard index")
    return render_template("admin/index.html")

@bp.route("/test")
@login_required
@admin_required
def test_route():
    """Simple test route to verify admin blueprint is working"""
    logger.info("Accessing admin test route")
    return "Admin Blueprint Test Route - If you see this, the admin blueprint is working!"

@bp.route("/user-activities/")
@login_required
@admin_required
def user_activities_slash():
    """Version of user activities with trailing slash"""
    logger.info("Accessing user activities page with trailing slash")
    return redirect(url_for("admin.user_activities"))

@bp.route("/user-activities-debug")
@login_required
@admin_required
def user_activities_debug():
    """Debug version of user activities that doesn't render a template"""
    logger.info("Accessing user activities debug page")
    return "User Activities Debug Page - If you see this, the route is working but there might be issues with the template rendering."

@bp.route("/user-activities")
@login_required
@admin_required
def user_activities():
    """Admin page to view user activities"""
    logger.info(f"Accessing user activities page, route: /user-activities, endpoint: admin.user_activities")
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 50
        
        # Filter parameters
        user_id = request.args.get("user_id", type=int)
        activity_type = request.args.get("activity_type")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        
        # Base query
        query = UserActivity.query.join(User)
        
        # Apply filters
        if user_id:
            query = query.filter(UserActivity.user_id == user_id)
        if activity_type:
            query = query.filter(UserActivity.activity_type == activity_type)
        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(UserActivity.timestamp >= date_from)
        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d")
            date_to = date_to + timedelta(days=1)  # Include the entire day
            query = query.filter(UserActivity.timestamp < date_to)
        
        # Get users for filter dropdown - try cache first
        cache_key_params = {'table': 'users', 'filters': {'order_by': 'username'}}
        cached_users = db_cache.get_complex_query_result('user_dropdown', cache_key_params)
        if cached_users:
            logger.debug("🎯 User dropdown cache hit")
            users = [User(**user_data) for user_data in cached_users]
        else:
            users = User.query.order_by(User.username).all()
            user_list = [user.to_dict() for user in users]
            db_cache.set_complex_query_result('user_dropdown', cache_key_params, user_list, expire=1800)
            logger.debug("💾 Cached user dropdown data")
        
        # Get activity types for filter dropdown
        # Hardcode to only show login and logout in filter dropdown
        activity_types = ['login', 'logout']
        
        # Paginate the results
        activities = query.order_by(UserActivity.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            "admin/user_activities.html",
            activities=activities,
            users=users,
            activity_types=activity_types,
            user_id=user_id,
            activity_type=activity_type,
            date_from=date_from.strftime("%Y-%m-%d") if date_from else "",
            date_to=date_to.strftime("%Y-%m-%d") if date_to and isinstance(date_to, datetime) else ""
        )
        
    except Exception as e:
        current_app.logger.error(f"Error loading user activities: {str(e)}")
        flash(f"Error loading user activities: {str(e)}", "danger")
        return redirect(url_for("admin.index"))

@bp.route("/users")
@login_required
@admin_required
def manage_users():
    """Admin page to view and manage users with filtering/screening"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 25
        
        # Filter parameters
        search = request.args.get("search", "").strip()
        email_filter = request.args.get("email_filter", "").strip()
        status_filter = request.args.get("status_filter", "")
        role_filter = request.args.get("role_filter", "")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        
        # Base query
        query = User.query
        
        # Apply search filter (username or email)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                User.username.ilike(search_pattern) | 
                User.email.ilike(search_pattern) |
                User.first_name.ilike(search_pattern) |
                User.last_name.ilike(search_pattern)
            )
        
        # Apply email domain filter
        if email_filter:
            query = query.filter(User.email.ilike(f"%{email_filter}%"))
        
        # Apply status filter
        if status_filter == "active":
            query = query.filter(User.is_active == True)
        elif status_filter == "inactive":
            query = query.filter(User.is_active == False)
        
        # Apply role filter
        if role_filter == "admin":
            query = query.filter(User.is_admin == True)
        elif role_filter == "user":
            query = query.filter(User.is_admin == False)
        elif role_filter == "google":
            query = query.filter(User.is_google_user == True)
        
        # Apply date range filter
        if date_from:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(User.created_at >= date_from_obj)
        if date_to:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            date_to_obj = date_to_obj + timedelta(days=1)  # Include the entire day
            query = query.filter(User.created_at < date_to_obj)
        
        # Get statistics - try cache first
        cached_stats = db_cache.get_user_statistics()
        if cached_stats:
            logger.debug("🎯 User statistics cache hit")
            total_users = cached_stats['total_users']
            active_users = cached_stats['active_users']
            admin_users = cached_stats['admin_users']
            google_users = cached_stats['google_users']
            testform_users = cached_stats['testform_users']
        else:
            logger.debug("💾 Computing and caching user statistics")
            total_users = User.query.count()
            active_users = User.query.filter(User.is_active == True).count()
            admin_users = User.query.filter(User.is_admin == True).count()
            google_users = User.query.filter(User.is_google_user == True).count()
            testform_users = User.query.filter(User.email.ilike('%testform.xyz')).count()
            
            # Cache the statistics
            stats = {
                'total_users': total_users,
                'active_users': active_users,
                'admin_users': admin_users,
                'google_users': google_users,
                'testform_users': testform_users
            }
            db_cache.set_user_statistics(stats, expire=300)  # 5 minutes
            logger.debug("💾 Cached user statistics")
        
        # Paginate the results
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            "admin/manage_users.html",
            users=users,
            search=search,
            email_filter=email_filter,
            status_filter=status_filter,
            role_filter=role_filter,
            date_from=date_from,
            date_to=date_to,
            total_users=total_users,
            active_users=active_users,
            admin_users=admin_users,
            google_users=google_users,
            testform_users=testform_users
        )
        
    except Exception as e:
        current_app.logger.error(f"Error loading users: {str(e)}")
        flash(f"Error loading users: {str(e)}", "danger")
        return redirect(url_for("admin.index"))

@bp.route("/company-cache")
@login_required
@admin_required
def company_cache():
    """Admin page for company information cache management"""
    logger.info("Accessing company cache management page")
    return render_template("admin/company_cache.html")

@bp.route("/news-management")
@login_required
@admin_required
def news_management():
    """Admin page for news article management"""
    logger.info("Accessing news article management page")
    
    # Get some statistics for display
    from datetime import datetime, timedelta
    
    try:
        # Buffer table statistics
        buffer_count = NewsArticle.query.count()
        
        # Search index statistics
        search_index_count = NewsSearchIndex.query.count()
        
        # Articles from last 24 hours (buffer table)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        buffer_articles_24h = NewsArticle.query.filter(NewsArticle.created_at >= last_24h).count()
        
        # Search index articles from last 24 hours
        search_index_24h = NewsSearchIndex.query.filter(NewsSearchIndex.created_at >= last_24h).count()
        
        # Investing.com articles from last 24 hours (buffer)
        investing_24h = NewsArticle.query.filter(
            NewsArticle.created_at >= last_24h,
            NewsArticle.source.ilike('%investing%')
        ).count()
        
        # TradingView articles from last 24 hours (buffer)
        tradingview_24h = NewsArticle.query.filter(
            NewsArticle.created_at >= last_24h,
            NewsArticle.source.ilike('%tradingview%')
        ).count()
        
        # Articles by source in last 24 hours (buffer)
        source_stats = db.session.execute(
            db.text("""
                SELECT source, COUNT(*) as count 
                FROM news_articles 
                WHERE created_at >= :since 
                GROUP BY source 
                ORDER BY count DESC
            """),
            {"since": last_24h}
        ).fetchall()
        
        stats = {
            'buffer_count': buffer_count,
            'search_index_count': search_index_count,
            'total_articles': buffer_count,  # Keep for compatibility
            'articles_24h': buffer_articles_24h,
            'search_index_24h': search_index_24h,
            'investing_24h': investing_24h,
            'tradingview_24h': tradingview_24h,
            'source_stats': [{'source': row[0], 'count': row[1]} for row in source_stats]
        }
        
        return render_template("admin/news_management.html", stats=stats)
        
    except Exception as e:
        logger.error(f"Error getting news statistics: {str(e)}")
        return render_template("admin/news_management.html", stats=None, error=str(e))

@bp.route("/api/clear-buffer-articles", methods=['POST'])
@login_required
@admin_required
def clear_buffer_articles():
    """Clear all articles from the news_articles buffer table (safe operation)"""
    try:
        data = request.get_json()
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'status': 'error',
                'message': 'Confirmation required for buffer clearing'
            }), 400
        
        # Count articles before deletion
        article_count = NewsArticle.query.count()
        
        if article_count == 0:
            return jsonify({
                'status': 'success',
                'message': 'Buffer table is already empty',
                'cleared_count': 0
            })
        
        # Clear all articles from buffer (this is safe - buffer table only)
        cleared_count = NewsArticle.query.delete()
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} cleared {cleared_count} articles from buffer table")
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully cleared {cleared_count} articles from buffer table',
            'cleared_count': cleared_count,
            'note': 'Permanent articles remain safe in search index table'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing buffer articles: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error clearing buffer articles: {str(e)}'
        }), 500

@bp.route("/api/clear-search-index", methods=['POST'])
@login_required
@admin_required
def clear_search_index():
    """Clear all articles from the news_search_index permanent table (DANGEROUS - requires admin password)"""
    try:
        data = request.get_json()
        confirm = data.get('confirm', False)
        admin_password = data.get('admin_password', '')
        
        if not confirm:
            return jsonify({
                'status': 'error',
                'message': 'Confirmation required for search index clearing'
            }), 400
        
        if not admin_password:
            return jsonify({
                'status': 'error',
                'message': 'Admin password required for this dangerous operation'
            }), 400
        
        # Verify admin password
        from app.utils.admin_auth import AdminAuth
        if not AdminAuth.verify_admin_password(admin_password):
            logger.warning(f"Failed admin password attempt for search index clearing by {current_user.username}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid admin password'
            }), 401
        
        # Count articles before deletion
        index_count = NewsSearchIndex.query.count()
        
        if index_count == 0:
            return jsonify({
                'status': 'success',
                'message': 'Search index table is already empty',
                'cleared_count': 0
            })
        
        # Clear all articles from search index (DANGEROUS - permanent data)
        cleared_count = NewsSearchIndex.query.delete()
        db.session.commit()
        
        logger.warning(f"Admin {current_user.username} cleared {cleared_count} articles from PERMANENT search index table")
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully cleared {cleared_count} articles from PERMANENT search index table',
            'cleared_count': cleared_count,
            'warning': 'PERMANENT DATA DELETED - This action cannot be undone'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing search index: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error clearing search index: {str(e)}'
        }), 500

@bp.route("/api/force-kill-schedulers", methods=['POST'])
@login_required
@admin_required
def force_kill_schedulers():
    """Emergency force kill both schedulers via admin panel"""
    try:
        data = request.get_json()
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'status': 'error',
                'message': 'Confirmation required for emergency scheduler kill'
            }), 400
        
        logger.warning(f"Admin {current_user.username} initiated emergency scheduler force kill")
        
        try:
            from app.utils.scheduler.news_scheduler import news_scheduler
            from app.utils.scheduler.news_fetch_scheduler import news_fetch_scheduler
            import schedule
            
            results = {'ai': False, 'fetch': False}
            
            # Force kill AI scheduler
            try:
                # Try graceful stop first
                if hasattr(news_scheduler, 'running') and news_scheduler.running:
                    success = news_scheduler.stop()
                    if success:
                        results['ai'] = True
                        logger.info("AI scheduler stopped gracefully")
                    else:
                        logger.warning("Graceful stop failed, forcing...")
                
                # Force kill if needed
                if not results['ai']:
                    news_scheduler.running = False
                    if hasattr(news_scheduler, 'scheduler_thread'):
                        news_scheduler.scheduler_thread = None
                    schedule.clear()
                    results['ai'] = True
                    logger.warning("AI scheduler force killed")
                    
            except Exception as e:
                logger.error(f"Failed to force kill AI scheduler: {e}")
            
            # Force kill fetch scheduler
            try:
                # Try graceful stop first
                if hasattr(news_fetch_scheduler, 'running') and news_fetch_scheduler.running:
                    success = news_fetch_scheduler.stop()
                    if success:
                        results['fetch'] = True
                        logger.info("Fetch scheduler stopped gracefully")
                    else:
                        logger.warning("Graceful stop failed, forcing...")
                
                # Force kill if needed
                if not results['fetch']:
                    news_fetch_scheduler.running = False
                    if hasattr(news_fetch_scheduler, 'thread'):
                        news_fetch_scheduler.thread = None
                    if hasattr(news_fetch_scheduler, 'manual_threads'):
                        news_fetch_scheduler.manual_threads = []
                    results['fetch'] = True
                    logger.warning("Fetch scheduler force killed")
                    
            except Exception as e:
                logger.error(f"Failed to force kill fetch scheduler: {e}")
            
            if results['ai'] and results['fetch']:
                message = "Emergency force kill completed successfully"
                logger.info(message)
                return jsonify({
                    'status': 'success',
                    'message': message,
                    'results': results
                })
            else:
                message = "Partial force kill - some schedulers may still be running"
                logger.warning(message)
                return jsonify({
                    'status': 'warning',
                    'message': message,
                    'results': results
                })
                
        except Exception as e:
            logger.error(f"Critical error during force kill: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Critical error during force kill: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in force kill API: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error in force kill API: {str(e)}'
        }), 500

@bp.route("/api/delete-investing-articles", methods=['POST'])
@login_required
@admin_required
def delete_investing_articles():
    """Delete Investing.com articles from the past 24 hours"""
    try:
        data = request.get_json()
        hours = data.get('hours', 24)  # Default to 24 hours, allow customization
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'status': 'error',
                'message': 'Confirmation required for deletion'
            }), 400
        
        # Calculate the time threshold
        from datetime import datetime, timedelta
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Find Investing.com articles from the specified time period
        investing_articles = NewsArticle.query.filter(
            NewsArticle.created_at >= since_time,
            NewsArticle.source.ilike('%investing%')
        ).all()
        
        if not investing_articles:
            return jsonify({
                'status': 'success',
                'message': f'No Investing.com articles found in the past {hours} hours',
                'deleted_count': 0,
                'symbols_deleted': 0
            })
        
        # Count associated article_symbols that will be auto-deleted
        article_ids = [article.id for article in investing_articles]
        symbols_count = ArticleSymbol.query.filter(ArticleSymbol.article_id.in_(article_ids)).count()
        
        # Store details for logging
        article_details = []
        for article in investing_articles:
            article_details.append({
                'id': article.id,
                'title': article.title[:100] + '...' if len(article.title) > 100 else article.title,
                'source': article.source,
                'created_at': article.created_at.isoformat() if article.created_at else None,
                'symbol_count': len(article.symbols)  # Count symbols for this article
            })
        
        # Delete the articles (this will auto-delete associated symbols due to cascade)
        deleted_count = len(investing_articles)
        for article in investing_articles:
            db.session.delete(article)
        
        db.session.commit()
        
        # Log the deletion
        logger.info(f"Admin {current_user.username} deleted {deleted_count} Investing.com articles from the past {hours} hours")
        logger.info(f"Auto-deleted {symbols_count} associated article_symbols records via cascade")
        for detail in article_details[:5]:  # Log first 5 for details
            logger.info(f"Deleted article: ID={detail['id']}, Title='{detail['title']}', Source={detail['source']}, Symbols={detail['symbol_count']}")
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully deleted {deleted_count} Investing.com articles and {symbols_count} associated symbols from the past {hours} hours',
            'deleted_count': deleted_count,
            'symbols_deleted': symbols_count,
            'cascade_info': 'Article symbols automatically deleted via database cascade',
            'article_details': article_details[:10]  # Return first 10 for display
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting Investing.com articles: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error deleting articles: {str(e)}'
        }), 500

@bp.route("/users/<int:user_id>/delete", methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a specific user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting yourself
        if user.id == current_user.id:
            flash("You cannot delete your own account.", "error")
            return redirect(url_for("admin.manage_users"))
        
        # Store user info for logging
        username = user.username
        email = user.email
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        # Invalidate caches
        user_cache.invalidate_user(user_id, email, username)
        db_cache.invalidate_user_cache()
        logger.debug(f"💥 Invalidated caches for deleted user: {username}")
        
        flash(f"User '{username}' ({email}) has been successfully deleted.", "success")
        logger.info(f"Admin {current_user.username} deleted user {username} ({email})")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
        flash(f"Error deleting user: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_users"))

@bp.route("/users/<int:user_id>/toggle-status", methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deactivating yourself
        if user.id == current_user.id:
            flash("You cannot deactivate your own account.", "error")
            return redirect(url_for("admin.manage_users"))
        
        # Toggle status
        user.is_active = not user.is_active
        db.session.commit()
        
        # Invalidate caches
        user_cache.invalidate_user(user.id, user.email, user.username)
        db_cache.invalidate_user_cache()
        logger.debug(f"💥 Invalidated caches for status change: {user.username}")
        
        status = "activated" if user.is_active else "deactivated"
        flash(f"User '{user.username}' has been {status}.", "success")
        logger.info(f"Admin {current_user.username} {status} user {user.username}")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling user status {user_id}: {str(e)}")
        flash(f"Error updating user status: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_users"))

@bp.route("/users/bulk-action", methods=['POST'])
@login_required
@admin_required
def bulk_user_action():
    """Perform bulk actions on users"""
    try:
        action = request.form.get('action')
        user_ids = request.form.getlist('user_ids[]')
        
        if not user_ids:
            flash("No users selected.", "error")
            return redirect(url_for("admin.manage_users"))
        
        user_ids = [int(uid) for uid in user_ids]
        
        # Prevent actions on yourself
        if current_user.id in user_ids:
            flash("You cannot perform bulk actions on your own account.", "error")
            return redirect(url_for("admin.manage_users"))
        
        if action == 'delete':
            users = User.query.filter(User.id.in_(user_ids)).all()
            usernames = [user.username for user in users]
            
            for user in users:
                db.session.delete(user)
            
            db.session.commit()
            
            # Invalidate caches for all deleted users
            for user in users:
                user_cache.invalidate_user(user.id, user.email, user.username)
            db_cache.invalidate_user_cache()
            logger.debug(f"💥 Invalidated caches for {len(users)} deleted users")
            
            flash(f"Successfully deleted {len(users)} users: {', '.join(usernames)}", "success")
            logger.info(f"Admin {current_user.username} bulk deleted users: {usernames}")
            
        elif action == 'deactivate':
            User.query.filter(User.id.in_(user_ids)).update({'is_active': False})
            db.session.commit()
            
            # Invalidate caches
            db_cache.invalidate_user_cache()
            logger.debug(f"💥 Invalidated user caches for bulk deactivation")
            
            flash(f"Successfully deactivated {len(user_ids)} users.", "success")
            logger.info(f"Admin {current_user.username} bulk deactivated {len(user_ids)} users")
            
        elif action == 'activate':
            User.query.filter(User.id.in_(user_ids)).update({'is_active': True})
            db.session.commit()
            
            # Invalidate caches
            db_cache.invalidate_user_cache()
            logger.debug(f"💥 Invalidated user caches for bulk activation")
            
            flash(f"Successfully activated {len(user_ids)} users.", "success")
            logger.info(f"Admin {current_user.username} bulk activated {len(user_ids)} users")
            
        elif action == 'delete_testform':
            # Special action to delete all testform.xyz users
            testform_users = User.query.filter(User.email.ilike('%testform.xyz')).all()
            testform_emails = [user.email for user in testform_users]
            
            for user in testform_users:
                db.session.delete(user)
            
            db.session.commit()
            flash(f"Successfully deleted {len(testform_users)} testform.xyz users: {', '.join(testform_emails)}", "success")
            logger.info(f"Admin {current_user.username} deleted all testform.xyz users: {testform_emails}")
        
        else:
            flash("Invalid action.", "error")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error performing bulk action: {str(e)}")
        flash(f"Error performing bulk action: {str(e)}", "error")
    
    return redirect(url_for("admin.manage_users"))

# ===== ADMIN PASSWORD AUTHENTICATION ROUTES =====

@bp.route("/admin-login", methods=['GET', 'POST'])
def admin_login():
    """Admin password authentication page"""
    from app.utils.admin_auth import AdminAuth
    
    # If already admin, redirect to admin index
    if (current_user.is_authenticated and current_user.is_admin) or AdminAuth.has_session_admin_privileges():
        return redirect(url_for('admin.index'))
    
    if request.method == 'POST':
        password = request.form.get('admin_password')
        action = request.form.get('action', 'session')  # 'session' or 'permanent'
        
        if not password:
            flash("Please enter the admin password.", "error")
            return render_template("admin/admin_login.html")
        
        # Verify admin password
        if AdminAuth.verify_admin_password(password):
            if action == 'permanent' and current_user.is_authenticated:
                # Grant permanent admin privileges to current user
                if AdminAuth.grant_user_admin_privileges(current_user.id):
                    flash(f"Permanent admin privileges granted to {current_user.username}!", "success")
                    logger.info(f"Admin password used to grant permanent privileges to {current_user.username}")
                else:
                    flash("Failed to grant permanent admin privileges.", "error")
            else:
                # Grant session admin privileges
                AdminAuth.grant_session_admin_privileges()
                flash("Admin session activated successfully!", "success")
                logger.info(f"Admin password used for session authentication by {current_user.username if current_user.is_authenticated else 'anonymous'}")
            
            # Redirect to originally requested page or admin index
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('admin.index')
            return redirect(next_page)
        else:
            flash("Invalid admin password.", "error")
            logger.warning(f"Failed admin password attempt by {current_user.username if current_user.is_authenticated else 'anonymous'}")
    
    return render_template("admin/admin_login.html")

@bp.route("/admin-logout", methods=['POST'])
def admin_logout():
    """Revoke admin session privileges"""
    from app.utils.admin_auth import AdminAuth
    
    AdminAuth.revoke_session_admin_privileges()
    flash("Admin session terminated.", "info")
    return redirect(url_for('main.index'))

@bp.route("/grant-admin/<int:user_id>", methods=['POST'])
@login_required
@admin_required
def grant_admin_privileges(user_id):
    """Grant admin privileges to a user"""
    from app.utils.admin_auth import AdminAuth
    
    try:
        user = User.query.get_or_404(user_id)
        
        if AdminAuth.grant_user_admin_privileges(user_id):
            flash(f"Admin privileges granted to {user.username}.", "success")
        else:
            flash("Failed to grant admin privileges.", "error")
            
    except Exception as e:
        flash(f"Error granting admin privileges: {str(e)}", "error")
        logger.error(f"Error granting admin privileges: {str(e)}")
    
    return redirect(url_for("admin.manage_users"))

@bp.route("/revoke-admin/<int:user_id>", methods=['POST'])
@login_required
@admin_required
def revoke_admin_privileges(user_id):
    """Revoke admin privileges from a user"""
    from app.utils.admin_auth import AdminAuth
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent removing admin from yourself if you're a permanent admin
        if current_user.is_authenticated and user.id == current_user.id and current_user.is_admin:
            flash("You cannot revoke admin privileges from yourself.", "error")
            return redirect(url_for("admin.manage_users"))
        
        if AdminAuth.revoke_user_admin_privileges(user_id):
            flash(f"Admin privileges revoked from {user.username}.", "success")
        else:
            flash("Failed to revoke admin privileges.", "error")
            
    except Exception as e:
        flash(f"Error revoking admin privileges: {str(e)}", "error")
        logger.error(f"Error revoking admin privileges: {str(e)}")
    
    return redirect(url_for("admin.manage_users"))

@bp.route("/admin-status")
@login_required  
@admin_required
def admin_status():
    """Show admin authentication status and configuration"""
    from app.utils.admin_auth import AdminAuth
    
    config_info = AdminAuth.get_admin_config_info()
    
    return render_template("admin/admin_status.html", 
                         config_info=config_info,
                         current_user=current_user)